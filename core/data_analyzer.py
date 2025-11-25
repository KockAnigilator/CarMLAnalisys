from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from utils import MatplotlibStyler


@dataclass
class VisualizationArtifacts:
    price_hist: Optional[plt.Figure] = None
    price_box: Optional[plt.Figure] = None
    correlation_heatmap: Optional[plt.Figure] = None


class DataAnalyzer:
    """Generate descriptive statistics and visualizations."""

    def __init__(self) -> None:
        MatplotlibStyler.apply()

    def numeric_statistics(
        self, dataframe: pd.DataFrame, output_path: Optional[Path] = None
    ) -> pd.DataFrame:
        numeric_df = dataframe.select_dtypes(include="number")
        quantiles = numeric_df.quantile([0.1, 0.25, 0.75, 0.9]).T.add_prefix("q_")
        stats = pd.DataFrame(
            {
                "min": numeric_df.min(),
                "max": numeric_df.max(),
                "mean": numeric_df.mean(),
                "median": numeric_df.median(),
                "variance": numeric_df.var(),
                "std": numeric_df.std(),
            }
        )
        stats = stats.join(quantiles)
        if output_path:
            stats.to_csv(output_path, index=True)
        return stats

    def categorical_statistics(
        self, dataframe: pd.DataFrame, output_path: Optional[Path] = None
    ) -> pd.DataFrame:
        categorical_df = dataframe.select_dtypes(exclude="number")
        rows = []
        for column in categorical_df.columns:
            series = categorical_df[column].dropna()
            mode = series.mode().iloc[0] if not series.empty else ""
            mode_freq = (series == mode).sum()
            rows.append(
                {
                    "column": column,
                    "unique_count": series.nunique(),
                    "mode": mode,
                    "mode_frequency": mode_freq,
                    "mode_percentage": mode_freq / max(len(series), 1),
                }
            )
        stats = pd.DataFrame(rows).set_index("column")
        if output_path:
            stats.to_csv(output_path, index=True)
        return stats

    def build_visualizations(
        self, dataframe: pd.DataFrame, target_column: str
    ) -> VisualizationArtifacts:
        artifacts = VisualizationArtifacts()
        if target_column not in dataframe.columns:
            return artifacts

        price_series = dataframe[target_column]

        fig_hist, ax_hist = plt.subplots(figsize=(8, 4))
        sns.histplot(price_series, kde=True, ax=ax_hist)
        ax_hist.set_title("Price Distribution")
        artifacts.price_hist = fig_hist

        fig_box, ax_box = plt.subplots(figsize=(6, 4))
        sns.boxplot(x=price_series, ax=ax_box)
        ax_box.set_title("Price Boxplot")
        artifacts.price_box = fig_box

        numeric_df = dataframe.select_dtypes(include="number")
        if numeric_df.shape[1] > 1:
            fig_corr, ax_corr = plt.subplots(figsize=(8, 6))
            sns.heatmap(numeric_df.corr(), annot=False, cmap="coolwarm", ax=ax_corr)
            ax_corr.set_title("Correlation Heatmap")
            artifacts.correlation_heatmap = fig_corr

        return artifacts

