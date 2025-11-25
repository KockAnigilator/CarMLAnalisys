from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from .data_analyzer import DataAnalyzer, VisualizationArtifacts
from .data_loader import DataLoader, DataSummary
from .data_preprocessor import DataPreprocessor, PreprocessingConfig
from .model_trainer import ModelTrainer, ModelTrainingResult


@dataclass
class AnalysisArtifacts:
    numeric_stats_path: Optional[Path] = None
    categorical_stats_path: Optional[Path] = None
    visualizations: Optional[VisualizationArtifacts] = None


class CarPricePredictor:
    """Coordinate the full analytics workflow."""

    def __init__(self) -> None:
        self.loader = DataLoader()
        self.preprocessor = DataPreprocessor()
        self.analyzer = DataAnalyzer()
        self.trainer = ModelTrainer()
        self.raw_df: Optional[pd.DataFrame] = None
        self.cleaned_df: Optional[pd.DataFrame] = None
        self.analysis_artifacts: Optional[AnalysisArtifacts] = None

    def load_data(self, path: str | Path) -> DataSummary:
        self.raw_df = self.loader.load_csv(path)
        return self.loader.describe()

    def preprocess_data(
        self, config: Optional[PreprocessingConfig] = None
    ) -> pd.DataFrame:
        if self.raw_df is None:
            raise ValueError("Load data before preprocessing.")
        if config:
            self.preprocessor = DataPreprocessor(config)
        self.cleaned_df = self.preprocessor.preprocess(self.raw_df)
        self.trainer.target_column = self.preprocessor.config.target_column
        return self.cleaned_df

    def analyze(
        self, output_dir: str | Path, target_column: Optional[str] = None
    ) -> AnalysisArtifacts:
        if self.cleaned_df is None:
            raise ValueError("Preprocess data before running analysis.")
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        numeric_path = out_dir / "numeric_statistics.csv"
        categorical_path = out_dir / "categorical_statistics.csv"

        self.analyzer.numeric_statistics(self.cleaned_df, numeric_path)
        self.analyzer.categorical_statistics(self.cleaned_df, categorical_path)

        visualizations = self.analyzer.build_visualizations(
            self.cleaned_df,
            target_column or self.preprocessor.config.target_column,
        )

        self.analysis_artifacts = AnalysisArtifacts(
            numeric_stats_path=numeric_path,
            categorical_stats_path=categorical_path,
            visualizations=visualizations,
        )
        return self.analysis_artifacts

    def train_models(
        self,
        test_size: float = 0.2,
        random_state: int = 42,
        rf_estimators: int = 300,
    ) -> dict[str, ModelTrainingResult]:
        if self.cleaned_df is None:
            raise ValueError("Preprocess data before training models.")
        return self.trainer.train(
            self.cleaned_df,
            test_size=test_size,
            random_state=random_state,
            rf_estimators=rf_estimators,
        )

    def predict(self, input_data: pd.DataFrame, model_name: str) -> pd.Series:
        predictions = self.trainer.predict(model_name, input_data)
        return pd.Series(predictions, name="predicted_price")

    def save_model(self, model_name: str, path: str | Path) -> Path:
        return self.trainer.save_model(model_name, path)

    def load_model(self, path: str | Path) -> ModelTrainingResult:
        return self.trainer.load_model(path)

