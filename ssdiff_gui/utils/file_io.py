"""Project save/load functionality for SSD."""

import json
import pickle
from pathlib import Path
from datetime import datetime
from typing import Optional, Any

import numpy as np

from ..models.project import (
    Project,
    Run,
    RunResults,
    DatasetConfig,
    SpacyConfig,
    EmbeddingConfig,
    HyperparametersConfig,
    ConceptConfig,
)


class _NumpyEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy types."""

    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)


class ProjectIO:
    """Handles project save/load operations."""

    @staticmethod
    def save_project(project: Project) -> None:
        """Save project to project.json and associated files."""
        project.modified_date = datetime.now()

        # Save main project file
        project_dict = project.to_dict()
        project_file = project.project_path / "project.json"

        with open(project_file, "w", encoding="utf-8") as f:
            json.dump(project_dict, f, indent=2, ensure_ascii=False, cls=_NumpyEncoder)

        # Save each run's config
        for run in project.runs:
            ProjectIO.save_run_config(run)

    @staticmethod
    def save_run_config(run: Run) -> None:
        """Save run configuration to its folder."""
        run.run_path.mkdir(parents=True, exist_ok=True)

        config_file = run.run_path / "config.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(run.to_dict(), f, indent=2, ensure_ascii=False, cls=_NumpyEncoder)

    @staticmethod
    def save_run_results(run: Run) -> None:
        """Save run results to pickle file."""
        if run.results:
            results_file = run.run_path / "results.pkl"
            with open(results_file, "wb") as f:
                pickle.dump(run.results.to_dict(), f)

    @staticmethod
    def load_project(project_path: Path) -> Project:
        """Load project from project.json."""
        project_file = project_path / "project.json"

        with open(project_file, "r", encoding="utf-8") as f:
            project_dict = json.load(f)

        project = Project.from_dict(project_dict, project_path)

        # Load runs
        run_ids = project_dict.get("runs", [])
        for run_id in run_ids:
            try:
                run = ProjectIO.load_run(project_path, run_id)
                project.runs.append(run)
            except Exception as e:
                print(f"Warning: Failed to load run {run_id}: {e}")

        return project

    @staticmethod
    def load_run(project_path: Path, run_id: str) -> Run:
        """Load a specific run."""
        run_path = project_path / "runs" / run_id
        config_file = run_path / "config.json"

        with open(config_file, "r", encoding="utf-8") as f:
            run_dict = json.load(f)

        run = Run.from_dict(run_dict, run_path)

        # Load results if available
        results_file = run_path / "results.pkl"
        if results_file.exists() and run.status == "complete":
            try:
                with open(results_file, "rb") as f:
                    results_dict = pickle.load(f)
                run.results = RunResults.from_dict(results_dict)
            except Exception as e:
                print(f"Warning: Failed to load results for run {run_id}: {e}")

        return run

    @staticmethod
    def save_preprocessed_docs(
        project: Project,
        pre_docs: list,
        docs: list,
        id_row_indices: list = None,
    ) -> None:
        """Save preprocessed documents to cache."""
        data_dir = project.project_path / "data"
        data_dir.mkdir(exist_ok=True)

        cache_file = data_dir / "preprocessed_docs.pkl"
        payload = {"pre_docs": pre_docs, "docs": docs}
        if id_row_indices is not None:
            payload["id_row_indices"] = id_row_indices
        with open(cache_file, "wb") as f:
            pickle.dump(payload, f)

    @staticmethod
    def load_preprocessed_docs(project: Project) -> Optional[tuple]:
        """Load preprocessed documents from cache.

        Returns (pre_docs, docs, id_row_indices) where id_row_indices may
        be None for projects that were preprocessed without grouping.
        """
        cache_file = project.project_path / "data" / "preprocessed_docs.pkl"
        if not cache_file.exists():
            return None

        with open(cache_file, "rb") as f:
            data = pickle.load(f)
        return (
            data.get("pre_docs"),
            data.get("docs"),
            data.get("id_row_indices"),
        )

    @staticmethod
    def save_embeddings_cache(project: Project, kv: Any) -> None:
        """Save embeddings info to cache (not the full embeddings, just metadata)."""
        import numpy as np

        data_dir = project.project_path / "data"
        data_dir.mkdir(exist_ok=True)

        # Save only metadata, not the full embeddings
        cache_file = data_dir / "embeddings_info.json"
        info = {
            "vocab_size": len(kv.key_to_index),
            "embedding_dim": kv.vector_size,
            "model_path": str(project.embedding_config.model_path),
        }

        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(info, f, indent=2, cls=_NumpyEncoder)

    @staticmethod
    def create_project_structure(project_path: Path) -> None:
        """Create the project directory structure."""
        project_path.mkdir(parents=True, exist_ok=True)
        (project_path / "data").mkdir(exist_ok=True)
        (project_path / "runs").mkdir(exist_ok=True)
        (project_path / "artifacts").mkdir(exist_ok=True)
