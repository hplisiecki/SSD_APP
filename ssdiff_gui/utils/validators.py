"""Input validation functions for SSD."""

from typing import List, Tuple, Set, Any, Optional
import pandas as pd


class Validator:
    """Validation utilities for SSD."""

    @staticmethod
    def validate_dataset(
        df: pd.DataFrame,
        text_col: str,
        outcome_col: str,
        id_col: Optional[str] = None,
    ) -> Tuple[List[str], List[str]]:
        """
        Validate a dataset for SSD analysis (legacy, continuous mode).

        Returns:
            Tuple of (errors, warnings) lists
        """
        errors, warnings, _id_stats = Validator.validate_dataset_text(df, text_col, id_col)
        if errors:
            return errors, warnings

        # Check outcome column
        if outcome_col not in df.columns:
            errors.append(f"Outcome column '{outcome_col}' not found in dataset")
            return errors, warnings

        # Check outcome column is numeric
        outcome = pd.to_numeric(df[outcome_col], errors="coerce")
        n_invalid = outcome.isna().sum()
        n_original_na = df[outcome_col].isna().sum()
        n_non_numeric = n_invalid - n_original_na

        if n_non_numeric > 0:
            pct = n_non_numeric / len(df) * 100
            if pct > 50:
                errors.append(f"{pct:.1f}% of outcome values are non-numeric")
            else:
                warnings.append(f"{n_non_numeric} outcome values are non-numeric")

        # Check outcome variance
        valid_outcome = outcome.dropna()
        if len(valid_outcome) > 0:
            outcome_std = valid_outcome.std()
            if outcome_std < 0.01:
                errors.append("Outcome has near-zero variance")
            elif outcome_std < 0.1:
                warnings.append("Outcome has low variance")

        # Check sample size with valid outcome
        n_valid = len(valid_outcome)
        if n_valid < 30:
            errors.append(f"Only {n_valid} valid samples (need at least 30)")
        elif n_valid < 100:
            warnings.append(f"Small sample size ({n_valid} documents)")

        return errors, warnings

    @staticmethod
    def validate_dataset_text(
        df: pd.DataFrame,
        text_col: str,
        id_col: Optional[str] = None,
    ) -> Tuple[List[str], List[str], Optional[dict]]:
        """
        Validate dataset text column and optional ID column (no outcome required).

        Returns:
            Tuple of (errors, warnings, id_stats) where id_stats is a dict
            with n_unique_ids, has_duplicates, avg_texts_per_id when an ID
            column is provided, or None otherwise.
        """
        errors = []
        warnings = []
        id_stats = None

        if text_col not in df.columns:
            errors.append(f"Text column '{text_col}' not found in dataset")
            return errors, warnings, id_stats

        # Check text column
        n_empty = df[text_col].isna().sum() + (df[text_col].astype(str).str.strip() == "").sum()
        if n_empty > 0:
            pct = n_empty / len(df) * 100
            if pct > 50:
                errors.append(f"{pct:.1f}% of texts are empty or missing")
            elif pct > 10:
                warnings.append(f"{pct:.1f}% of texts are empty or missing")

        # Check sample size
        n_rows = len(df)
        if n_rows < 30:
            errors.append(f"Only {n_rows} rows (need at least 30)")
        elif n_rows < 100:
            warnings.append(f"Small sample size ({n_rows} documents)")

        # Compute ID stats if provided
        if id_col and id_col in df.columns:
            n_unique = df[id_col].nunique(dropna=True)
            has_duplicates = n_unique < (~df[id_col].isna()).sum()
            avg_texts = len(df) / n_unique if n_unique > 0 else 0.0
            id_stats = {
                "n_unique_ids": n_unique,
                "has_duplicates": has_duplicates,
                "avg_texts_per_id": avg_texts,
            }

        return errors, warnings, id_stats

    @staticmethod
    def validate_lexicon(
        lexicon: Set[str],
        vocab: Set[str],
        docs: List[List[str]],
    ) -> Tuple[List[str], List[str]]:
        """
        Validate a lexicon for SSD analysis.

        Returns:
            Tuple of (errors, warnings) lists
        """
        errors = []
        warnings = []

        if not lexicon:
            errors.append("Lexicon is empty")
            return errors, warnings

        # Check tokens in vocabulary
        oov_tokens = lexicon - vocab
        if oov_tokens == lexicon:
            errors.append("None of the lexicon tokens are in the embedding vocabulary")
        elif len(oov_tokens) > 0:
            pct = len(oov_tokens) / len(lexicon) * 100
            if pct > 50:
                warnings.append(f"{pct:.1f}% of lexicon tokens not in vocabulary: {list(oov_tokens)[:5]}...")
            else:
                warnings.append(f"{len(oov_tokens)} tokens not in vocabulary: {list(oov_tokens)[:5]}")

        # Check coverage
        valid_tokens = lexicon & vocab
        if valid_tokens:
            n_docs_with_hit = sum(1 for doc in docs if any(t in valid_tokens for t in doc))
            coverage = n_docs_with_hit / len(docs) * 100 if docs else 0

            if coverage < 10:
                errors.append(f"Very low coverage: only {coverage:.1f}% of documents contain lexicon terms")
            elif coverage < 30:
                warnings.append(f"Low coverage: {coverage:.1f}% of documents contain lexicon terms")

        # Check lexicon size
        if len(valid_tokens) < 3:
            warnings.append(f"Very small lexicon ({len(valid_tokens)} tokens)")
        elif len(valid_tokens) < 5:
            warnings.append(f"Small lexicon ({len(valid_tokens)} tokens)")

        return errors, warnings

    @staticmethod
    def validate_embeddings_path(path: str) -> Tuple[List[str], List[str]]:
        """
        Validate an embeddings file path.

        Returns:
            Tuple of (errors, warnings) lists
        """
        from pathlib import Path

        errors = []
        warnings = []

        if not path:
            errors.append("No embedding file specified")
            return errors, warnings

        p = Path(path)
        if not p.exists():
            errors.append(f"File not found: {path}")
            return errors, warnings

        # Check file extension
        valid_extensions = {".kv", ".bin", ".txt", ".gz", ".vec"}
        if p.suffix.lower() not in valid_extensions:
            warnings.append(f"Unusual file extension: {p.suffix}. Expected one of {valid_extensions}")

        # Check file size
        size_mb = p.stat().st_size / (1024 * 1024)
        if size_mb > 5000:
            warnings.append(f"Large embedding file ({size_mb:.0f} MB) - loading may take time")

        return errors, warnings

    @staticmethod
    def validate_csv_path(path: str) -> Tuple[List[str], List[str]]:
        """
        Validate a CSV file path.

        Returns:
            Tuple of (errors, warnings) lists
        """
        from pathlib import Path

        errors = []
        warnings = []

        if not path:
            errors.append("No CSV file specified")
            return errors, warnings

        p = Path(path)
        if not p.exists():
            errors.append(f"File not found: {path}")
            return errors, warnings

        if p.suffix.lower() not in {".csv", ".tsv", ".txt"}:
            warnings.append(f"Unusual file extension: {p.suffix}")

        return errors, warnings
