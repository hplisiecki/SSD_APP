"""Project data model for SSD.

Contains all dataclasses representing project configuration,
run results, and cached data.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Set, Any, Tuple
from datetime import datetime


@dataclass
class DatasetConfig:
    """Configuration for the loaded dataset."""
    csv_path: Optional[Path] = None
    text_column: Optional[str] = None
    outcome_column: Optional[str] = None
    id_column: Optional[str] = None
    group_column: Optional[str] = None
    n_rows: int = 0
    n_valid: int = 0
    cached: bool = False

    # Analysis configuration (set in Setup tab)
    analysis_type: str = "continuous"  # "continuous" or "crossgroup"
    concept_mode: str = "lexicon"  # "lexicon" or "fulldoc"
    n_perm: int = 5000  # permutation count for crossgroup

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "csv_path": str(self.csv_path) if self.csv_path else None,
            "text_column": self.text_column,
            "outcome_column": self.outcome_column,
            "id_column": self.id_column,
            "group_column": self.group_column,
            "n_rows": self.n_rows,
            "n_valid": self.n_valid,
            "cached": self.cached,
            "analysis_type": self.analysis_type,
            "concept_mode": self.concept_mode,
            "n_perm": self.n_perm,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DatasetConfig":
        """Create from dict."""
        return cls(
            csv_path=Path(d["csv_path"]) if d.get("csv_path") else None,
            text_column=d.get("text_column"),
            outcome_column=d.get("outcome_column"),
            id_column=d.get("id_column"),
            group_column=d.get("group_column"),
            n_rows=d.get("n_rows", 0),
            n_valid=d.get("n_valid", 0),
            cached=d.get("cached", False),
            analysis_type=d.get("analysis_type", "continuous"),
            concept_mode=d.get("concept_mode", "lexicon"),
            n_perm=d.get("n_perm", 5000),
        )


@dataclass
class SpacyConfig:
    """Configuration for spaCy text processing."""
    language: str = "en"
    model: str = "en_core_web_sm"
    custom_model_path: Optional[Path] = None
    lemmatize: bool = True
    remove_stopwords: bool = True
    processed: bool = False
    n_docs_processed: int = 0
    total_tokens: int = 0
    mean_words_before_stopwords: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "language": self.language,
            "model": self.model,
            "custom_model_path": str(self.custom_model_path) if self.custom_model_path else None,
            "lemmatize": self.lemmatize,
            "remove_stopwords": self.remove_stopwords,
            "processed": self.processed,
            "n_docs_processed": self.n_docs_processed,
            "total_tokens": self.total_tokens,
            "mean_words_before_stopwords": self.mean_words_before_stopwords,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SpacyConfig":
        """Create from dict."""
        return cls(
            language=d.get("language", "en"),
            model=d.get("model", "en_core_web_sm"),
            custom_model_path=Path(d["custom_model_path"]) if d.get("custom_model_path") else None,
            lemmatize=d.get("lemmatize", True),
            remove_stopwords=d.get("remove_stopwords", True),
            processed=d.get("processed", False),
            n_docs_processed=d.get("n_docs_processed", 0),
            total_tokens=d.get("total_tokens", 0),
            mean_words_before_stopwords=d.get("mean_words_before_stopwords", 0.0),
        )


@dataclass
class EmbeddingConfig:
    """Configuration for word embeddings."""
    model_type: str = "custom"  # "known" or "custom"
    model_name: Optional[str] = None  # e.g., "GloVe 300d"
    model_path: Optional[Path] = None
    l2_normalize: bool = True
    abtt_enabled: bool = True
    abtt_m: int = 1
    loaded: bool = False
    vocab_size: int = 0
    embedding_dim: int = 0
    coverage_pct: float = 0.0
    n_oov: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "model_type": self.model_type,
            "model_name": self.model_name,
            "model_path": str(self.model_path) if self.model_path else None,
            "l2_normalize": self.l2_normalize,
            "abtt_enabled": self.abtt_enabled,
            "abtt_m": self.abtt_m,
            "loaded": self.loaded,
            "vocab_size": self.vocab_size,
            "embedding_dim": self.embedding_dim,
            "coverage_pct": self.coverage_pct,
            "n_oov": self.n_oov,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EmbeddingConfig":
        """Create from dict."""
        return cls(
            model_type=d.get("model_type", "custom"),
            model_name=d.get("model_name"),
            model_path=Path(d["model_path"]) if d.get("model_path") else None,
            l2_normalize=d.get("l2_normalize", True),
            abtt_enabled=d.get("abtt_enabled", True),
            abtt_m=d.get("abtt_m", 1),
            loaded=d.get("loaded", False),
            vocab_size=d.get("vocab_size", 0),
            embedding_dim=d.get("embedding_dim", 0),
            coverage_pct=d.get("coverage_pct", 0.0),
            n_oov=d.get("n_oov", 0),
        )


@dataclass
class HyperparametersConfig:
    """Configuration for SSD model hyperparameters."""
    # PCA
    n_pca_mode: str = "auto"  # "auto" or "manual"
    n_pca_manual: Optional[int] = 20
    sweep_k_min: int = 1
    sweep_k_max: int = 80
    sweep_k_step: int = 1
    sweep_stability_criterion: str = "elbow"

    # Context
    context_window_size: int = 3
    sif_a: float = 1e-3

    # Beta
    use_unit_beta: bool = True

    # Clustering
    clustering_topn: int = 100
    clustering_k_auto: bool = True
    clustering_k_min: int = 2
    clustering_k_max: int = 10

    # Doc normalization
    l2_normalize_docs: bool = True

    # PCA sweep advanced
    auck_radius: int = 3
    beta_smooth_win: int = 7
    beta_smooth_kind: str = "median"
    weight_by_size: bool = True

    # Clustering advanced
    clustering_top_words: int = 10

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "n_pca_mode": self.n_pca_mode,
            "n_pca_manual": self.n_pca_manual,
            "sweep_k_min": self.sweep_k_min,
            "sweep_k_max": self.sweep_k_max,
            "sweep_k_step": self.sweep_k_step,
            "sweep_stability_criterion": self.sweep_stability_criterion,
            "context_window_size": self.context_window_size,
            "sif_a": self.sif_a,
            "use_unit_beta": self.use_unit_beta,
            "clustering_topn": self.clustering_topn,
            "clustering_k_auto": self.clustering_k_auto,
            "clustering_k_min": self.clustering_k_min,
            "clustering_k_max": self.clustering_k_max,
            "l2_normalize_docs": self.l2_normalize_docs,
            "auck_radius": self.auck_radius,
            "beta_smooth_win": self.beta_smooth_win,
            "beta_smooth_kind": self.beta_smooth_kind,
            "weight_by_size": self.weight_by_size,
            "clustering_top_words": self.clustering_top_words,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "HyperparametersConfig":
        """Create from dict."""
        return cls(
            n_pca_mode=d.get("n_pca_mode", "auto"),
            n_pca_manual=d.get("n_pca_manual", 20),
            sweep_k_min=d.get("sweep_k_min", 1),
            sweep_k_max=d.get("sweep_k_max", 80),
            sweep_k_step=d.get("sweep_k_step", 1),
            sweep_stability_criterion=d.get("sweep_stability_criterion", "elbow"),
            context_window_size=d.get("context_window_size", 3),
            sif_a=d.get("sif_a", 1e-3),
            use_unit_beta=d.get("use_unit_beta", True),
            clustering_topn=d.get("clustering_topn", 100),
            clustering_k_auto=d.get("clustering_k_auto", True),
            clustering_k_min=d.get("clustering_k_min", 2),
            clustering_k_max=d.get("clustering_k_max", 10),
            l2_normalize_docs=d.get("l2_normalize_docs", True),
            auck_radius=d.get("auck_radius", 3),
            beta_smooth_win=d.get("beta_smooth_win", 7),
            beta_smooth_kind=d.get("beta_smooth_kind", "median"),
            weight_by_size=d.get("weight_by_size", True),
            clustering_top_words=d.get("clustering_top_words", 10),
        )


@dataclass
class ConceptConfig:
    """Configuration for concept definition (Stage 2)."""
    mode: str = "lexicon"  # "lexicon" or "fulldoc"
    lexicon_tokens: Optional[Set[str]] = None
    min_hits_per_doc: Optional[int] = None
    drop_no_hits: bool = True
    stoplist: Optional[Set[str]] = None  # for fulldoc mode

    # Analysis type: "continuous" or "crossgroup"
    analysis_type: str = "continuous"
    outcome_column: Optional[str] = None
    group_column: Optional[str] = None
    n_perm: int = 5000  # permutation count for crossgroup

    # Computed stats
    coverage_pct: float = 0.0
    n_docs_with_hits: int = 0
    median_hits: float = 0.0
    mean_hits: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "mode": self.mode,
            "lexicon_tokens": list(self.lexicon_tokens) if self.lexicon_tokens else None,
            "min_hits_per_doc": self.min_hits_per_doc,
            "drop_no_hits": self.drop_no_hits,
            "stoplist": list(self.stoplist) if self.stoplist else None,
            "analysis_type": self.analysis_type,
            "outcome_column": self.outcome_column,
            "group_column": self.group_column,
            "n_perm": self.n_perm,
            "coverage_pct": self.coverage_pct,
            "n_docs_with_hits": self.n_docs_with_hits,
            "median_hits": self.median_hits,
            "mean_hits": self.mean_hits,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ConceptConfig":
        """Create from dict."""
        return cls(
            mode=d.get("mode", "lexicon"),
            lexicon_tokens=set(d["lexicon_tokens"]) if d.get("lexicon_tokens") else None,
            min_hits_per_doc=d.get("min_hits_per_doc"),
            drop_no_hits=d.get("drop_no_hits", True),
            stoplist=set(d["stoplist"]) if d.get("stoplist") else None,
            analysis_type=d.get("analysis_type", "continuous"),
            outcome_column=d.get("outcome_column"),
            group_column=d.get("group_column"),
            n_perm=d.get("n_perm", 5000),
            coverage_pct=d.get("coverage_pct", 0.0),
            n_docs_with_hits=d.get("n_docs_with_hits", 0),
            median_hits=d.get("median_hits", 0.0),
            mean_hits=d.get("mean_hits", 0.0),
        )


@dataclass
class RunResults:
    """Results from a completed SSD run."""
    # Analysis type
    analysis_type: str = "continuous"  # "continuous" or "crossgroup"

    # Model fit statistics (continuous)
    r2: float = 0.0
    r2_adj: float = 0.0
    f_stat: float = 0.0
    f_pvalue: float = 0.0

    # Effect sizes (continuous)
    beta_norm_stdCN: float = 0.0
    delta_per_0p10_raw: float = 0.0
    iqr_effect_raw: float = 0.0
    y_corr_pred: float = 0.0

    # Sample info
    n_raw: int = 0
    n_kept: int = 0
    n_dropped: int = 0

    # Interpretation data (continuous, or per-contrast for crossgroup)
    pos_neighbors: List[Tuple[str, float]] = field(default_factory=list)
    neg_neighbors: List[Tuple[str, float]] = field(default_factory=list)

    # Clustering (if performed)
    clusters_summary: Optional[List[Dict]] = None
    clusters_members: Optional[List[Dict]] = None

    # Snippets (if extracted)
    cluster_snippets_pos: Optional[List[Dict]] = None
    cluster_snippets_neg: Optional[List[Dict]] = None
    beta_snippets_pos: Optional[List[Dict]] = None
    beta_snippets_neg: Optional[List[Dict]] = None

    # Per-doc scores
    doc_scores: Optional[List[Dict]] = None

    # PCA selection (if auto)
    selected_k: Optional[int] = None
    pca_var_explained: float = 0.0

    # Lexicon coverage (if lexicon mode)
    lexicon_coverage_summary: Optional[Dict] = None
    lexicon_coverage_per_token: Optional[List[Dict]] = None

    # Crossgroup-specific (None for continuous runs)
    omnibus_p: Optional[float] = None
    omnibus_T: Optional[float] = None
    n_perm: Optional[int] = None
    group_labels: Optional[List[str]] = None
    group_counts: Optional[Dict[str, int]] = None
    pairwise_table: Optional[List[Dict]] = None  # results_table() as records

    # Per-contrast results: Dict keyed by "groupA vs groupB"
    contrast_results: Optional[Dict[str, Dict]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "analysis_type": self.analysis_type,
            "r2": self.r2,
            "r2_adj": self.r2_adj,
            "f_stat": self.f_stat,
            "f_pvalue": self.f_pvalue,
            "beta_norm_stdCN": self.beta_norm_stdCN,
            "delta_per_0p10_raw": self.delta_per_0p10_raw,
            "iqr_effect_raw": self.iqr_effect_raw,
            "y_corr_pred": self.y_corr_pred,
            "n_raw": self.n_raw,
            "n_kept": self.n_kept,
            "n_dropped": self.n_dropped,
            "pos_neighbors": self.pos_neighbors,
            "neg_neighbors": self.neg_neighbors,
            "clusters_summary": self.clusters_summary,
            "clusters_members": self.clusters_members,
            "cluster_snippets_pos": self.cluster_snippets_pos,
            "cluster_snippets_neg": self.cluster_snippets_neg,
            "beta_snippets_pos": self.beta_snippets_pos,
            "beta_snippets_neg": self.beta_snippets_neg,
            "doc_scores": self.doc_scores,
            "selected_k": self.selected_k,
            "pca_var_explained": self.pca_var_explained,
            "lexicon_coverage_summary": self.lexicon_coverage_summary,
            "lexicon_coverage_per_token": self.lexicon_coverage_per_token,
            "omnibus_p": self.omnibus_p,
            "omnibus_T": self.omnibus_T,
            "n_perm": self.n_perm,
            "group_labels": self.group_labels,
            "group_counts": self.group_counts,
            "pairwise_table": self.pairwise_table,
            "contrast_results": self.contrast_results,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RunResults":
        """Create from dict."""
        return cls(
            analysis_type=d.get("analysis_type", "continuous"),
            r2=d.get("r2", 0.0),
            r2_adj=d.get("r2_adj", 0.0),
            f_stat=d.get("f_stat", 0.0),
            f_pvalue=d.get("f_pvalue", 0.0),
            beta_norm_stdCN=d.get("beta_norm_stdCN", 0.0),
            delta_per_0p10_raw=d.get("delta_per_0p10_raw", 0.0),
            iqr_effect_raw=d.get("iqr_effect_raw", 0.0),
            y_corr_pred=d.get("y_corr_pred", 0.0),
            n_raw=d.get("n_raw", 0),
            n_kept=d.get("n_kept", 0),
            n_dropped=d.get("n_dropped", 0),
            pos_neighbors=d.get("pos_neighbors", []),
            neg_neighbors=d.get("neg_neighbors", []),
            clusters_summary=d.get("clusters_summary"),
            clusters_members=d.get("clusters_members"),
            cluster_snippets_pos=d.get("cluster_snippets_pos"),
            cluster_snippets_neg=d.get("cluster_snippets_neg"),
            beta_snippets_pos=d.get("beta_snippets_pos"),
            beta_snippets_neg=d.get("beta_snippets_neg"),
            doc_scores=d.get("doc_scores"),
            selected_k=d.get("selected_k"),
            pca_var_explained=d.get("pca_var_explained", 0.0),
            lexicon_coverage_summary=d.get("lexicon_coverage_summary"),
            lexicon_coverage_per_token=d.get("lexicon_coverage_per_token"),
            omnibus_p=d.get("omnibus_p"),
            omnibus_T=d.get("omnibus_T"),
            n_perm=d.get("n_perm"),
            group_labels=d.get("group_labels"),
            group_counts=d.get("group_counts"),
            pairwise_table=d.get("pairwise_table"),
            contrast_results=d.get("contrast_results"),
        )


@dataclass
class Run:
    """A single SSD run with frozen config and results."""
    run_id: str  # Format: YYYYMMDD_HHMMSS
    timestamp: datetime
    run_path: Path

    # Concept configuration (Stage 2)
    concept_config: ConceptConfig

    # Frozen snapshot of project settings
    frozen_dataset_config: DatasetConfig
    frozen_spacy_config: SpacyConfig
    frozen_embedding_config: EmbeddingConfig
    frozen_hyperparameters: HyperparametersConfig

    # User-assigned name (required for archiving)
    name: Optional[str] = None

    # Results
    results: Optional[RunResults] = None
    status: str = "pending"  # pending, running, complete, error
    error_message: Optional[str] = None

    # Cached objects (not serialized)
    ssd_model: Optional[Any] = None  # The actual SSD object
    ssd_group_model: Optional[Any] = None  # Cached SSDGroup (not serialized)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "run_id": self.run_id,
            "name": self.name,
            "timestamp": self.timestamp.isoformat(),
            "run_path": str(self.run_path),
            "concept_config": self.concept_config.to_dict(),
            "frozen_dataset_config": self.frozen_dataset_config.to_dict(),
            "frozen_spacy_config": self.frozen_spacy_config.to_dict(),
            "frozen_embedding_config": self.frozen_embedding_config.to_dict(),
            "frozen_hyperparameters": self.frozen_hyperparameters.to_dict(),
            "status": self.status,
            "error_message": self.error_message,
            # results saved separately as pickle
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any], run_path: Path) -> "Run":
        """Create from dict."""
        return cls(
            run_id=d["run_id"],
            name=d.get("name"),
            timestamp=datetime.fromisoformat(d["timestamp"]),
            run_path=run_path,
            concept_config=ConceptConfig.from_dict(d["concept_config"]),
            frozen_dataset_config=DatasetConfig.from_dict(d["frozen_dataset_config"]),
            frozen_spacy_config=SpacyConfig.from_dict(d["frozen_spacy_config"]),
            frozen_embedding_config=EmbeddingConfig.from_dict(d["frozen_embedding_config"]),
            frozen_hyperparameters=HyperparametersConfig.from_dict(d["frozen_hyperparameters"]),
            status=d.get("status", "pending"),
            error_message=d.get("error_message"),
        )


@dataclass
class Project:
    """Complete project state."""
    project_path: Path
    name: str
    created_date: datetime
    modified_date: datetime

    # Stage 1 configs
    dataset_config: DatasetConfig = field(default_factory=DatasetConfig)
    spacy_config: SpacyConfig = field(default_factory=SpacyConfig)
    embedding_config: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    hyperparameters: HyperparametersConfig = field(default_factory=HyperparametersConfig)

    # Runs
    runs: List[Run] = field(default_factory=list)

    # State flags
    stage1_complete: bool = False
    ready_for_runs: bool = False

    # Cached data (not serialized, loaded on demand)
    _cached_df: Optional[Any] = field(default=None, repr=False)
    _cached_pre_docs: Optional[List] = field(default=None, repr=False)
    _cached_docs: Optional[List] = field(default=None, repr=False)
    _cached_y: Optional[Any] = field(default=None, repr=False)
    _cached_groups: Optional[Any] = field(default=None, repr=False)
    _cached_kv: Optional[Any] = field(default=None, repr=False)
    _cached_nlp: Optional[Any] = field(default=None, repr=False)
    _cached_stopwords: Optional[List] = field(default=None, repr=False)
    _cached_id_row_indices: Optional[List] = field(default=None, repr=False)

    def check_stage1_complete(self) -> bool:
        """Check if Stage 1 is complete and ready to proceed."""
        return (
            self.dataset_config.cached
            and self.spacy_config.processed
            and self.embedding_config.loaded
        )

    def update_ready_state(self):
        """Update the ready_for_runs flag based on current state."""
        self.stage1_complete = self.check_stage1_complete()
        self.ready_for_runs = self.stage1_complete

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "name": self.name,
            "created_date": self.created_date.isoformat(),
            "modified_date": self.modified_date.isoformat(),
            "dataset_config": self.dataset_config.to_dict(),
            "spacy_config": self.spacy_config.to_dict(),
            "embedding_config": self.embedding_config.to_dict(),
            "hyperparameters": self.hyperparameters.to_dict(),
            "runs": [run.run_id for run in self.runs],
            "stage1_complete": self.stage1_complete,
            "ready_for_runs": self.ready_for_runs,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any], project_path: Path) -> "Project":
        """Create from dict."""
        return cls(
            project_path=project_path,
            name=d["name"],
            created_date=datetime.fromisoformat(d["created_date"]),
            modified_date=datetime.fromisoformat(d["modified_date"]),
            dataset_config=DatasetConfig.from_dict(d["dataset_config"]),
            spacy_config=SpacyConfig.from_dict(d["spacy_config"]),
            embedding_config=EmbeddingConfig.from_dict(d["embedding_config"]),
            hyperparameters=HyperparametersConfig.from_dict(d["hyperparameters"]),
            stage1_complete=d.get("stage1_complete", False),
            ready_for_runs=d.get("ready_for_runs", False),
        )
