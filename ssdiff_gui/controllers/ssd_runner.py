"""SSD analysis runner thread."""

import copy
from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal

from ..models.project import (
    Project,
    Run,
    RunResults,
    ConceptConfig,
)
from ..utils.file_io import ProjectIO


class SSDRunner(QThread):
    """Worker thread for running SSD analysis."""

    progress = Signal(int, str)  # percent, message
    finished = Signal(object)  # Run object
    error = Signal(str)

    def __init__(
        self,
        project: Project,
        concept_config: ConceptConfig,
        parent=None,
    ):
        super().__init__(parent)
        self.project = project
        self.concept_config = concept_config
        self._is_cancelled = False

    def cancel(self):
        """Request cancellation of the analysis."""
        self._is_cancelled = True

    def run(self):
        """Execute the SSD analysis pipeline."""
        try:
            # Create run object
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_path = self.project.project_path / "runs" / run_id

            run = Run(
                run_id=run_id,
                timestamp=datetime.now(),
                run_path=run_path,
                concept_config=copy.deepcopy(self.concept_config),
                frozen_dataset_config=copy.deepcopy(self.project.dataset_config),
                frozen_spacy_config=copy.deepcopy(self.project.spacy_config),
                frozen_embedding_config=copy.deepcopy(self.project.embedding_config),
                frozen_hyperparameters=copy.deepcopy(self.project.hyperparameters),
                status="running",
            )

            run_path.mkdir(parents=True, exist_ok=True)
            ProjectIO.save_run_config(run)

            if self._is_cancelled:
                return

            if self.concept_config.analysis_type == "crossgroup":
                self._run_crossgroup(run)
            else:
                self._run_continuous(run)

        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
            self.error.emit(error_msg)

    # ------------------------------------------------------------------ #
    #  Continuous pipeline (existing)
    # ------------------------------------------------------------------ #

    def _run_continuous(self, run: Run):
        """Execute the continuous SSD analysis pipeline."""
        from ssdiff import SSD, pca_sweep

        self.progress.emit(5, "Loading cached data...")
        kv = self.project._cached_kv
        docs = self.project._cached_docs
        y = self.project._cached_y
        pre_docs = self.project._cached_pre_docs

        if kv is None or docs is None or y is None:
            raise ValueError("Cached data not available. Please complete Stage 1 setup.")

        if self._is_cancelled:
            return

        # Prepare lexicon
        lexicon = None
        use_full_doc = True
        cov_summary = None
        cov_per_token = None
        if self.concept_config.mode == "lexicon":
            lexicon = self.concept_config.lexicon_tokens
            use_full_doc = False
            if not lexicon:
                raise ValueError("Lexicon mode selected but no tokens provided.")

            self.progress.emit(8, "Computing lexicon coverage...")
            try:
                from ssdiff import coverage_by_lexicon
                cov_summary, cov_per_token_df = coverage_by_lexicon(
                    (docs, y), lexicon=lexicon
                )
                cov_per_token = cov_per_token_df.to_dict("records")
            except Exception as e:
                print(f"Lexicon coverage computation failed: {e}")

        if self._is_cancelled:
            return

        # PCA sweep if needed
        selected_k = self.project.hyperparameters.n_pca_manual
        if self.project.hyperparameters.n_pca_mode == "auto":
            self.progress.emit(15, "Running PCA sweep to find optimal dimensions...")

            k_min = self.project.hyperparameters.sweep_k_min
            k_max = self.project.hyperparameters.sweep_k_max
            k_step = self.project.hyperparameters.sweep_k_step
            k_values = list(range(k_min, k_max + 1, k_step))

            selector = pca_sweep(
                kv=kv,
                docs=docs,
                y=y,
                lexicon=lexicon,
                use_full_doc=use_full_doc,
                pca_k_values=k_values,
                window=self.project.hyperparameters.context_window_size,
                sif_a=self.project.hyperparameters.sif_a,
                cluster_topn=self.project.hyperparameters.clustering_topn,
                k_min=self.project.hyperparameters.clustering_k_min,
                k_max=self.project.hyperparameters.clustering_k_max,
                top_words=self.project.hyperparameters.clustering_top_words,
                weight_by_size=self.project.hyperparameters.weight_by_size,
                auck_radius=self.project.hyperparameters.auck_radius,
                beta_smooth_win=self.project.hyperparameters.beta_smooth_win,
                beta_smooth_kind=self.project.hyperparameters.beta_smooth_kind,
                out_dir=str(run.run_path),
                prefix="pca_sweep",
                save_figures=True,
            )
            selected_k = selector.best_k

            if self._is_cancelled:
                return

        self.progress.emit(40, f"Fitting SSD model (K={selected_k})...")

        ssd = SSD(
            kv=kv,
            docs=docs,
            y=y,
            lexicon=lexicon,
            l2_normalize_docs=self.project.hyperparameters.l2_normalize_docs,
            N_PCA=selected_k,
            use_unit_beta=self.project.hyperparameters.use_unit_beta,
            window=self.project.hyperparameters.context_window_size,
            sif_a=self.project.hyperparameters.sif_a,
            use_full_doc=use_full_doc,
        )

        if self._is_cancelled:
            return

        self.progress.emit(55, "Extracting model statistics...")

        results = RunResults(
            analysis_type="continuous",
            r2=ssd.r2,
            r2_adj=ssd.r2_adj,
            f_stat=ssd.f_stat,
            f_pvalue=ssd.f_pvalue,
            beta_norm_stdCN=ssd.beta_norm_stdCN,
            delta_per_0p10_raw=ssd.delta_per_0p10_raw,
            iqr_effect_raw=ssd.iqr_effect_raw,
            y_corr_pred=ssd.y_corr_pred,
            n_raw=ssd.n_raw,
            n_kept=ssd.n_kept,
            n_dropped=ssd.n_dropped,
            selected_k=selected_k,
            pca_var_explained=float(ssd.pca_var_explained),
            lexicon_coverage_summary=cov_summary,
            lexicon_coverage_per_token=cov_per_token,
        )

        # Get neighbors
        self.progress.emit(60, "Finding nearest neighbors...")
        top_words_df = ssd.top_words(n=50, verbose=False)

        results.pos_neighbors = top_words_df[top_words_df["side"] == "pos"].to_dict("records")
        results.neg_neighbors = top_words_df[top_words_df["side"] == "neg"].to_dict("records")

        if self._is_cancelled:
            return

        # Clustering
        self.progress.emit(70, "Clustering neighbors into themes...")
        try:
            k_min = self.project.hyperparameters.clustering_k_min
            k_max = self.project.hyperparameters.clustering_k_max

            df_clusters, df_members = ssd.cluster_neighbors(
                topn=self.project.hyperparameters.clustering_topn,
                k=None if self.project.hyperparameters.clustering_k_auto else k_min,
                k_min=k_min,
                k_max=k_max,
                random_state=13,
                top_words=self.project.hyperparameters.clustering_top_words,
                verbose=False,
            )
            results.clusters_summary = df_clusters.to_dict("records")
            results.clusters_members = df_members.to_dict("records")
        except Exception as e:
            print(f"Clustering failed: {e}")

        if self._is_cancelled:
            return

        # Snippets
        self.progress.emit(80, "Extracting text snippets...")
        if pre_docs:
            try:
                cluster_snips = ssd.cluster_snippets(
                    pre_docs=pre_docs,
                    side="both",
                    top_per_cluster=100,
                )
                results.cluster_snippets_pos = cluster_snips["pos"].to_dict("records")
                results.cluster_snippets_neg = cluster_snips["neg"].to_dict("records")
            except Exception as e:
                print(f"Cluster snippets failed: {e}")

            try:
                beta_snips = ssd.beta_snippets(
                    pre_docs=pre_docs,
                    window_sentences=1,
                    top_per_side=200,
                )
                results.beta_snippets_pos = beta_snips["beta_pos"].to_dict("records")
                results.beta_snippets_neg = beta_snips["beta_neg"].to_dict("records")
            except Exception as e:
                print(f"Beta snippets failed: {e}")

        if self._is_cancelled:
            return

        # Per-document scores
        self.progress.emit(90, "Computing document scores...")
        try:
            scores_df = ssd.ssd_scores(include_all=True)
            results.doc_scores = scores_df.to_dict("records")
        except Exception as e:
            print(f"Document scores failed: {e}")

        # Finalize run
        run.results = results
        run.status = "complete"
        run.ssd_model = ssd

        self.progress.emit(95, "Saving results...")
        ProjectIO.save_run_config(run)
        ProjectIO.save_run_results(run)

        self.progress.emit(100, "Complete!")
        self.finished.emit(run)

    # ------------------------------------------------------------------ #
    #  Crossgroup pipeline (new)
    # ------------------------------------------------------------------ #

    def _run_crossgroup(self, run: Run):
        """Execute the crossgroup SSD analysis pipeline."""
        from ssdiff import SSDGroup

        self.progress.emit(5, "Loading cached data...")
        kv = self.project._cached_kv
        docs = self.project._cached_docs
        groups = self.project._cached_groups
        pre_docs = self.project._cached_pre_docs

        if kv is None or docs is None or groups is None:
            raise ValueError(
                "Cached data not available. Please select a group column."
            )

        if self._is_cancelled:
            return

        # Prepare lexicon
        lexicon = None
        use_full_doc = True
        cov_summary = None
        cov_per_token = None
        if self.concept_config.mode == "lexicon":
            lexicon = self.concept_config.lexicon_tokens
            use_full_doc = False
            if not lexicon:
                raise ValueError("Lexicon mode selected but no tokens provided.")

            self.progress.emit(10, "Computing lexicon coverage...")
            try:
                from ssdiff import coverage_by_lexicon
                cov_summary, cov_per_token_df = coverage_by_lexicon(
                    (docs, groups), lexicon=lexicon, var_type="categorical"
                )
                cov_per_token = cov_per_token_df.to_dict("records")
            except Exception as e:
                print(f"Lexicon coverage computation failed: {e}")

        if self._is_cancelled:
            return

        # Fit SSDGroup
        n_perm = self.concept_config.n_perm
        self.progress.emit(15, f"Fitting SSDGroup (n_perm={n_perm})...")

        sg = SSDGroup(
            kv=kv,
            docs=docs,
            groups=groups,
            lexicon=lexicon,
            n_perm=n_perm,
            window=self.project.hyperparameters.context_window_size,
            sif_a=self.project.hyperparameters.sif_a,
            l2_normalize_docs=self.project.hyperparameters.l2_normalize_docs,
            use_full_doc=use_full_doc,
        )

        if self._is_cancelled:
            return

        self.progress.emit(50, "Extracting omnibus results...")

        # Build group counts (from kept docs only)
        import numpy as np
        group_labels = sorted(sg.group_labels)
        group_counts = {g: int((sg.groups_kept == g).sum()) for g in group_labels}

        # Get results table
        results_table_df = sg.results_table()
        pairwise_table = results_table_df.to_dict("records")

        # Initialize results
        results = RunResults(
            analysis_type="crossgroup",
            n_raw=sg.n_raw,
            n_kept=sg.n_kept,
            n_dropped=sg.n_dropped,
            omnibus_p=float(sg.omnibus_p),
            omnibus_T=float(sg.omnibus_T),
            n_perm=n_perm,
            group_labels=group_labels,
            group_counts=group_counts,
            pairwise_table=pairwise_table,
            lexicon_coverage_summary=cov_summary,
            lexicon_coverage_per_token=cov_per_token,
        )

        if self._is_cancelled:
            return

        # Extract per-contrast results
        self.progress.emit(55, "Extracting pairwise contrasts...")
        contrast_results = {}
        pairs = list(sg.pairwise)
        n_pairs = len(pairs)

        hp = self.project.hyperparameters

        for idx, (g1, g2) in enumerate(pairs):
            if self._is_cancelled:
                return

            pair_key = f"{g1} vs {g2}"
            pct = 55 + int(35 * (idx / max(n_pairs, 1)))
            self.progress.emit(pct, f"Processing contrast: {pair_key}...")

            contrast = sg.get_contrast(g1, g2)
            cr = {}

            # Per-pair stats from results table
            pair_row = results_table_df[
                (results_table_df["group_A"] == g1) &
                (results_table_df["group_B"] == g2)
            ]
            if len(pair_row) > 0:
                row = pair_row.iloc[0]
                cr["p_raw"] = float(row.get("p_raw", 0))
                cr["p_corrected"] = float(row.get("p_corrected", 0))
                cr["cohens_d"] = float(row.get("cohens_d", 0))
                cr["cosine_distance"] = float(row.get("cosine_distance", 0))
                cr["contrast_norm"] = float(row.get("contrast_norm", 0))
                cr["n_g1"] = int(row.get("n_A", 0))
                cr["n_g2"] = int(row.get("n_B", 0))

            # Top words (neighbors)
            try:
                top_words_df = contrast.top_words(n=50, verbose=False)
                cr["pos_neighbors"] = top_words_df[
                    top_words_df["side"] == "pos"
                ].to_dict("records")
                cr["neg_neighbors"] = top_words_df[
                    top_words_df["side"] == "neg"
                ].to_dict("records")
            except Exception as e:
                print(f"Top words failed for {pair_key}: {e}")
                cr["pos_neighbors"] = []
                cr["neg_neighbors"] = []

            # Clustering
            try:
                df_clusters, df_members = contrast.cluster_neighbors(
                    topn=hp.clustering_topn,
                    k=None if hp.clustering_k_auto else hp.clustering_k_min,
                    k_min=hp.clustering_k_min,
                    k_max=hp.clustering_k_max,
                    random_state=13,
                    top_words=hp.clustering_top_words,
                    verbose=False,
                )
                cr["clusters_summary"] = df_clusters.to_dict("records")
                cr["clusters_members"] = df_members.to_dict("records")
            except Exception as e:
                print(f"Clustering failed for {pair_key}: {e}")
                cr["clusters_summary"] = []
                cr["clusters_members"] = []

            # Snippets
            if pre_docs:
                try:
                    cluster_snips = contrast.cluster_snippets(
                        pre_docs=pre_docs,
                        side="both",
                        top_per_cluster=100,
                    )
                    cr["cluster_snippets_pos"] = cluster_snips["pos"].to_dict("records")
                    cr["cluster_snippets_neg"] = cluster_snips["neg"].to_dict("records")
                except Exception as e:
                    print(f"Cluster snippets failed for {pair_key}: {e}")
                    cr["cluster_snippets_pos"] = []
                    cr["cluster_snippets_neg"] = []

                try:
                    beta_snips = contrast.beta_snippets(
                        pre_docs=pre_docs,
                        top_per_side=200,
                    )
                    cr["beta_snippets_pos"] = beta_snips["beta_pos"].to_dict("records")
                    cr["beta_snippets_neg"] = beta_snips["beta_neg"].to_dict("records")
                except Exception as e:
                    print(f"Beta snippets failed for {pair_key}: {e}")
                    cr["beta_snippets_pos"] = []
                    cr["beta_snippets_neg"] = []

            # Contrast scores
            try:
                scores_df = sg.contrast_scores(g1, g2)
                cr["contrast_scores"] = scores_df.to_dict("records")
            except Exception as e:
                print(f"Contrast scores failed for {pair_key}: {e}")
                cr["contrast_scores"] = []

            contrast_results[pair_key] = cr

        results.contrast_results = contrast_results

        # For the first contrast, also populate top-level fields
        # so that Stage 3 can display something immediately
        if contrast_results:
            first_key = list(contrast_results.keys())[0]
            first = contrast_results[first_key]
            results.pos_neighbors = first.get("pos_neighbors", [])
            results.neg_neighbors = first.get("neg_neighbors", [])
            results.clusters_summary = first.get("clusters_summary", [])
            results.clusters_members = first.get("clusters_members", [])
            results.cluster_snippets_pos = first.get("cluster_snippets_pos", [])
            results.cluster_snippets_neg = first.get("cluster_snippets_neg", [])
            results.beta_snippets_pos = first.get("beta_snippets_pos", [])
            results.beta_snippets_neg = first.get("beta_snippets_neg", [])
            results.doc_scores = first.get("contrast_scores", [])

        # Finalize
        run.results = results
        run.status = "complete"
        run.ssd_group_model = sg

        self.progress.emit(95, "Saving results...")
        ProjectIO.save_run_config(run)
        ProjectIO.save_run_results(run)

        self.progress.emit(100, "Complete!")
        self.finished.emit(run)
