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
    """Координирует полный аналитический конвейер."""

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

    def predict(self, input_data: pd.DataFrame, model_name: str) -> pd.DataFrame:
        """
        Выполняет предсказания на новых данных.
        
        Важно: Входные данные должны быть УЖЕ предобработаны 
        (т.е. прошли через preprocess_data с тем же config).
        Модель sklearn уже выполняет свою предобработку в pipeline.
        """
        if input_data.empty:
            raise ValueError("Input data is empty.")
        
        # Убираем target_column из входных данных, если он есть
        data_for_prediction = input_data.copy()
        if self.trainer.target_column in data_for_prediction.columns:
            data_for_prediction = data_for_prediction.drop(columns=[self.trainer.target_column])
        
        predictions = self.trainer.predict(model_name, data_for_prediction)
        result = input_data.copy()
        result["predicted_price"] = predictions
        return result
    
    def predict_raw(self, input_data: pd.DataFrame, model_name: str) -> pd.DataFrame:
        """
        Выполняет предсказания на сырых данных.
        Автоматически применяет ту же предобработку,
        что была использована при обучении.
        """
        if input_data.empty:
            raise ValueError("Input data is empty.")
        
        if self.cleaned_df is None:
            raise ValueError(
                "Сначала нужно выполнить preprocess_data для настройки предобработчика."
            )
        
        # Применяем ту же предобработку
        processed_data = self.preprocessor.preprocess(input_data)
        
        # Выполняем предсказание
        return self.predict(processed_data, model_name)

    def save_model(self, model_name: str, path: str | Path) -> Path:
        return self.trainer.save_model(model_name, path)

    def load_model(self, path: str | Path) -> ModelTrainingResult:
        return self.trainer.load_model(path)

