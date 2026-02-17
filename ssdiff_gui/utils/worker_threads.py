"""Background worker threads for SSD."""

from PySide6.QtCore import QThread, Signal
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import os
import sys


def get_spacy_models_dir() -> Path:
    """Return the directory for locally-downloaded spaCy models.

    Uses platform-appropriate data directories:
    - Windows: ``%LOCALAPPDATA%/SSD/spacy_models``
    - macOS:   ``~/Library/Application Support/SSD/spacy_models``
    - Linux:   ``~/.local/share/SSD/spacy_models``
    """
    if sys.platform == "win32":
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            base = Path(local_appdata) / "SSD"
        else:
            base = Path.home() / "AppData" / "Local" / "SSD"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "SSD"
    else:
        base = Path.home() / ".local" / "share" / "SSD"
    models_dir = base / "spacy_models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


def find_local_model(model_name: str) -> Optional[Path]:
    """Check if a spaCy model has been downloaded locally.

    Returns the path to the model data directory if found, otherwise None.
    The wheel extracts into ``{model_name}-{version}/{model_name}/{model_name}-{version}``.
    We look for any version sub-folder matching this pattern.
    """
    import glob as _glob

    models_dir = get_spacy_models_dir()
    # Pattern: models_dir/{model_name}-*/{model_name}/{model_name}-*/
    pattern = str(models_dir / f"{model_name}-*" / model_name / f"{model_name}-*")
    matches = sorted(_glob.glob(pattern))
    if matches:
        return Path(matches[-1])  # latest version
    return None


class PreprocessWorker(QThread):
    """Worker thread for spaCy preprocessing."""

    progress = Signal(int, str)  # percent, message
    finished = Signal(list, list, dict)  # pre_docs, docs, stats
    error = Signal(str)

    def __init__(
        self,
        texts_raw: Union[List[str], List[List[str]]],
        language: str,
        model: str,
        model_path: Optional[Path] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.texts_raw = texts_raw
        self.language = language
        self.model = model
        self.model_path = model_path
        self._is_cancelled = False

    def cancel(self):
        """Request cancellation of the preprocessing."""
        self._is_cancelled = True

    def run(self):
        """Execute preprocessing in background thread."""
        try:
            from ssdiff import (
                load_spacy,
                load_stopwords,
                preprocess_texts,
                build_docs_from_preprocessed,
            )
            import spacy

            self.progress.emit(5, "Loading spaCy model...")
            if self.model_path:
                # Load from local path (downloaded wheel)
                nlp = spacy.load(str(self.model_path), disable=["ner"])
                if "parser" not in nlp.pipe_names and "sentencizer" not in nlp.pipe_names:
                    nlp.add_pipe("sentencizer")
            else:
                nlp = load_spacy(self.model)

            if self._is_cancelled:
                return

            self.progress.emit(15, "Loading stopwords...")
            stopwords = load_stopwords(self.language)

            if self._is_cancelled:
                return

            n_items = len(self.texts_raw)
            label = "profiles" if self.texts_raw and isinstance(self.texts_raw[0], list) else "documents"
            self.progress.emit(25, f"Preprocessing {n_items} {label}...")

            # Process in batches for progress updates
            pre_docs = preprocess_texts(self.texts_raw, nlp, stopwords)

            if self._is_cancelled:
                return

            self.progress.emit(85, "Building document vectors...")
            docs = build_docs_from_preprocessed(pre_docs)

            if self._is_cancelled:
                return

            self.progress.emit(95, "Computing statistics...")
            stats = self._compute_stats(pre_docs, docs)

            self.progress.emit(100, "Complete!")
            self.finished.emit(pre_docs, docs, stats)

        except Exception as e:
            import traceback
            self.error.emit(f"Preprocessing failed: {str(e)}\n{traceback.format_exc()}")

    def _compute_stats(self, pre_docs: list, docs: list) -> dict:
        """Compute preprocessing statistics.

        Handles both flat (PreprocessedDoc) and grouped (PreprocessedProfile)
        outputs from ssdiff.preprocess_texts().
        """
        from ssdiff.preprocess import PreprocessedProfile

        is_grouped = pre_docs and isinstance(pre_docs[0], PreprocessedProfile)

        if is_grouped:
            # docs is List[List[List[str]]] — profiles × posts × lemmas
            total_tokens = sum(
                sum(len(post) for post in profile) for profile in docs
            )
            n_profiles = len(docs)
            n_total_posts = sum(len(profile) for profile in docs)
            avg_tokens = total_tokens / n_profiles if n_profiles else 0
            empty_profiles = sum(
                1 for profile in docs if all(len(post) == 0 for post in profile)
            )

            # Mean words per profile before stopword removal
            words_per_profile = [
                sum(
                    len(s.split())
                    for post_sents in pdoc.post_sents_surface
                    for s in post_sents
                )
                for pdoc in pre_docs
            ]
            mean_words_before_stopwords = (
                sum(words_per_profile) / len(words_per_profile) if words_per_profile else 0.0
            )

            return {
                "n_docs": n_profiles,
                "n_total_rows": n_total_posts,
                "is_grouped": True,
                "total_tokens": total_tokens,
                "avg_tokens_per_doc": avg_tokens,
                "empty_docs": empty_profiles,
                "mean_words_before_stopwords": mean_words_before_stopwords,
            }
        else:
            # Flat: docs is List[List[str]]
            total_tokens = sum(len(doc) for doc in docs)
            avg_tokens = total_tokens / len(docs) if docs else 0
            empty_docs = sum(1 for doc in docs if len(doc) == 0)

            words_per_doc = [
                sum(len(s.split()) for s in pdoc.sents_surface)
                for pdoc in pre_docs
            ]
            mean_words_before_stopwords = (
                sum(words_per_doc) / len(words_per_doc) if words_per_doc else 0.0
            )

            return {
                "n_docs": len(docs),
                "is_grouped": False,
                "total_tokens": total_tokens,
                "avg_tokens_per_doc": avg_tokens,
                "empty_docs": empty_docs,
                "mean_words_before_stopwords": mean_words_before_stopwords,
            }


class EmbeddingWorker(QThread):
    """Worker thread for loading and normalizing embeddings."""

    progress = Signal(int, str)  # percent, message
    finished = Signal(object, dict)  # kv, stats
    error = Signal(str)

    def __init__(
        self,
        embedding_path: Path,
        l2_normalize: bool = True,
        abtt_enabled: bool = True,
        abtt_m: int = 1,
        docs: Optional[List[List[str]]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.embedding_path = embedding_path
        self.l2_normalize = l2_normalize
        self.abtt_enabled = abtt_enabled
        self.abtt_m = abtt_m
        self.docs = docs
        self._is_cancelled = False

    def cancel(self):
        """Request cancellation of embedding loading."""
        self._is_cancelled = True

    def run(self):
        """Execute embedding loading in background thread."""
        try:
            from ssdiff import load_embeddings, normalize_kv

            self.progress.emit(10, "Loading embeddings file...")
            kv = load_embeddings(str(self.embedding_path))

            if self._is_cancelled:
                return

            self.progress.emit(50, "Normalizing embeddings...")
            abtt_m = self.abtt_m if self.abtt_enabled else 0
            kv = normalize_kv(kv, l2=self.l2_normalize, abtt_m=abtt_m)

            if self._is_cancelled:
                return

            self.progress.emit(80, "Computing coverage statistics...")
            stats = self._compute_coverage(kv)

            self.progress.emit(100, "Complete!")
            self.finished.emit(kv, stats)

        except Exception as e:
            import traceback
            self.error.emit(f"Failed to load embeddings: {str(e)}\n{traceback.format_exc()}")

    def _compute_coverage(self, kv) -> dict:
        """Compute vocabulary coverage statistics.

        Handles both flat (List[List[str]]) and grouped
        (List[List[List[str]]]) doc formats.
        """
        vocab_size = len(kv.key_to_index)
        embedding_dim = kv.vector_size

        stats = {
            "vocab_size": vocab_size,
            "embedding_dim": embedding_dim,
        }

        # Compute coverage against docs if available
        if self.docs:
            vocab_set = set(kv.key_to_index.keys())
            all_tokens = set()

            # Detect grouped vs flat by checking first element
            is_grouped = self.docs and self.docs[0] and isinstance(self.docs[0][0], list)
            if is_grouped:
                for profile in self.docs:
                    for post in profile:
                        all_tokens.update(post)
            else:
                for doc in self.docs:
                    all_tokens.update(doc)

            in_vocab = all_tokens & vocab_set
            oov = all_tokens - vocab_set

            stats["doc_vocab_size"] = len(all_tokens)
            stats["in_vocab"] = len(in_vocab)
            stats["oov"] = len(oov)
            stats["coverage_pct"] = len(in_vocab) / len(all_tokens) * 100 if all_tokens else 0

        return stats


class SpacyDownloadWorker(QThread):
    """Worker thread for downloading a spaCy model wheel from GitHub.

    Downloads the compatible .whl file, extracts it to the local
    AppData models directory, and emits the extracted model path
    on success.
    """

    progress = Signal(int, str)
    finished = Signal(str)  # model_path
    error = Signal(str)

    def __init__(self, model: str, parent=None):
        super().__init__(parent)
        self.model = model

    def run(self):
        import json
        import zipfile
        import tempfile
        import shutil
        from urllib.request import urlopen, Request
        from urllib.error import URLError

        try:
            import spacy

            # 1. Resolve spaCy minor version (e.g. "3.7")
            spacy_version = spacy.__version__
            parts = spacy_version.split(".")
            minor_version = f"{parts[0]}.{parts[1]}"

            self.progress.emit(5, "Fetching model compatibility info...")

            compat_url = (
                "https://raw.githubusercontent.com/explosion/spacy-models"
                "/master/compatibility.json"
            )
            req = Request(compat_url, headers={"User-Agent": "SSD-App/1.0"})
            with urlopen(req, timeout=30) as resp:
                compat = json.loads(resp.read().decode("utf-8"))

            # 2. Look up model version
            spacy_compat = compat.get("spacy", {})

            # Try exact minor, then try prefix match
            model_versions = None
            for key in spacy_compat:
                if key == minor_version or key.startswith(minor_version + "."):
                    if self.model in spacy_compat[key]:
                        model_versions = spacy_compat[key][self.model]
                        break

            if not model_versions:
                self.error.emit(
                    f"No compatible version of '{self.model}' found for "
                    f"spaCy {spacy_version}.\n\n"
                    f"Check https://spacy.io/models for available models."
                )
                return

            model_version = model_versions[0]  # latest compatible
            wheel_name = f"{self.model}-{model_version}-py3-none-any.whl"

            # 3. Download the wheel
            self.progress.emit(15, f"Downloading {wheel_name}...")

            download_url = (
                f"https://github.com/explosion/spacy-models/releases/download/"
                f"{self.model}-{model_version}/{wheel_name}"
            )

            req = Request(download_url, headers={"User-Agent": "SSD-App/1.0"})
            with urlopen(req, timeout=60) as resp:
                total = resp.headers.get("Content-Length")
                total = int(total) if total else None

                tmp_file = tempfile.NamedTemporaryFile(
                    delete=False, suffix=".whl"
                )
                try:
                    downloaded = 0
                    chunk_size = 64 * 1024
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        tmp_file.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            pct = 15 + int(60 * downloaded / total)
                            mb = downloaded / (1024 * 1024)
                            total_mb = total / (1024 * 1024)
                            self.progress.emit(
                                min(pct, 75),
                                f"Downloading... {mb:.1f}/{total_mb:.1f} MB",
                            )
                    tmp_file.close()

                    # 4. Extract the wheel
                    self.progress.emit(80, "Extracting model...")
                    models_dir = get_spacy_models_dir()
                    extract_dir = models_dir / f"{self.model}-{model_version}"

                    # Remove previous version if exists
                    if extract_dir.exists():
                        shutil.rmtree(extract_dir)

                    with zipfile.ZipFile(tmp_file.name, "r") as zf:
                        zf.extractall(extract_dir)

                finally:
                    # Clean up temp file
                    try:
                        os.unlink(tmp_file.name)
                    except OSError:
                        pass

            # 5. Verify the model data exists
            model_data_path = (
                extract_dir / self.model / f"{self.model}-{model_version}"
            )
            if not model_data_path.exists():
                self.error.emit(
                    f"Extraction succeeded but model data not found at "
                    f"expected path:\n{model_data_path}"
                )
                return

            self.progress.emit(100, "Download complete!")
            self.finished.emit(str(model_data_path))

        except URLError as e:
            self.error.emit(
                f"Network error downloading '{self.model}': {e}\n\n"
                f"Check your internet connection and try again."
            )
        except Exception as e:
            import traceback
            self.error.emit(
                f"Download failed: {str(e)}\n{traceback.format_exc()}"
            )


class KvConvertWorker(QThread):
    """Worker thread for saving embeddings in .kv format."""

    progress = Signal(int, str)
    finished = Signal(str)   # kv_path
    error = Signal(str)

    def __init__(self, kv, kv_path: str, parent=None):
        super().__init__(parent)
        self.kv = kv
        self.kv_path = kv_path

    def run(self):
        try:
            self.progress.emit(10, "Saving .kv format...")
            self.kv.save(self.kv_path)
            self.progress.emit(100, "Done!")
            self.finished.emit(self.kv_path)
        except Exception as e:
            import traceback
            self.error.emit(f"Failed to save .kv file: {str(e)}\n{traceback.format_exc()}")


class CoverageWorker(QThread):
    """Worker thread for computing lexicon coverage."""

    progress = Signal(int, str)
    finished = Signal(dict, object)  # summary, per_token_df
    error = Signal(str)

    def __init__(
        self,
        docs: List[List[str]],
        y: Any,
        lexicon: set,
        parent=None,
    ):
        super().__init__(parent)
        self.docs = docs
        self.y = y
        self.lexicon = lexicon

    def run(self):
        """Compute coverage statistics."""
        try:
            from ssdiff import coverage_by_lexicon

            self.progress.emit(50, "Computing coverage...")

            summary, per_token_df = coverage_by_lexicon(
                (self.docs, self.y),
                lexicon=self.lexicon,
                n_bins=4,
                verbose=False,
            )

            self.progress.emit(100, "Complete!")
            self.finished.emit(summary, per_token_df)

        except Exception as e:
            import traceback
            self.error.emit(f"Coverage computation failed: {str(e)}")
