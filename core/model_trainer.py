from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


@dataclass
class ModelTrainingResult:
    model_name: str
    pipeline: Pipeline
    metrics: Dict[str, float]


class ModelTrainer:
    """Обучает и оценивает модели машинного обучения."""

    def __init__(self, target_column: str = "price") -> None:
        self.target_column = target_column
        self.results: dict[str, ModelTrainingResult] = {}

    def train(
        self,
        dataframe: pd.DataFrame,
        test_size: float = 0.2,
        random_state: int = 42,
        rf_estimators: int = 300,
    ) -> dict[str, ModelTrainingResult]:
        if self.target_column not in dataframe.columns:
            raise ValueError(f"Target column '{self.target_column}' was not found.")

        X = dataframe.drop(columns=[self.target_column])
        y = dataframe[self.target_column]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )

        categorical_features = X.select_dtypes(exclude="number").columns.tolist()
        numeric_features = X.select_dtypes(include="number").columns.tolist()

        preprocessor = ColumnTransformer(
            transformers=[
                (
                    "num",
                    Pipeline([("scaler", StandardScaler())]),
                    numeric_features,
                ),
                (
                    "cat",
                    Pipeline(
                        [("encoder", OneHotEncoder(handle_unknown="ignore"))]
                    ),
                    categorical_features,
                ),
            ],
            remainder="drop",
        )

        models: dict[str, Any] = {
            "random_forest": RandomForestRegressor(
                n_estimators=rf_estimators, random_state=random_state
            ),
            "linear_regression": LinearRegression(),
        }

        for name, regressor in models.items():
            pipeline = Pipeline(
                steps=[("preprocessor", preprocessor), ("model", regressor)]
            )
            pipeline.fit(X_train, y_train)
            predictions = pipeline.predict(X_test)
            metrics = self._evaluate(y_test, predictions)
            self.results[name] = ModelTrainingResult(
                model_name=name, pipeline=pipeline, metrics=metrics
            )
        return self.results

    def predict(self, model_name: str, dataframe: pd.DataFrame) -> np.ndarray:
        if model_name not in self.results:
            raise ValueError(f"Model '{model_name}' has not been trained.")
        pipeline = self.results[model_name].pipeline
        return pipeline.predict(dataframe)

    def save_model(self, model_name: str, path: str | Path) -> Path:
        if model_name not in self.results:
            raise ValueError(f"Model '{model_name}' has not been trained.")
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.results[model_name], output_path)
        return output_path

    def load_model(self, path: str | Path) -> ModelTrainingResult:
        model_result: ModelTrainingResult = joblib.load(path)
        self.results[model_result.model_name] = model_result
        self.target_column = self.target_column or "price"
        return model_result

    @staticmethod
    def _evaluate(y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, float]:
        return {
            "mae": mean_absolute_error(y_true, y_pred),
            "mse": mean_squared_error(y_true, y_pred),
            "rmse": mean_squared_error(y_true, y_pred, squared=False),
            "r2": r2_score(y_true, y_pred),
        }

