from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    GradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.linear_model import (
    ElasticNet,
    Lasso,
    LinearRegression,
    Ridge,
)
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVR


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
        if dataframe.empty:
            raise ValueError("Dataframe is empty. Cannot train models.")
        
        if self.target_column not in dataframe.columns:
            raise ValueError(f"Target column '{self.target_column}' was not found.")

        X = dataframe.drop(columns=[self.target_column])
        y = dataframe[self.target_column]
        
        if X.empty or len(X) < 2:
            raise ValueError("Not enough data to train models.")

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )

        categorical_features = X.select_dtypes(exclude="number").columns.tolist()
        numeric_features = X.select_dtypes(include="number").columns.tolist()

        # Создаем трансформеры только для существующих типов данных
        transformers = []
        
        if numeric_features:
            transformers.append(
                (
                    "num",
                    Pipeline([("scaler", StandardScaler())]),
                    numeric_features,
                )
            )
        
        if categorical_features:
            transformers.append(
                (
                    "cat",
                    Pipeline(
                        [("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]
                    ),
                    categorical_features,
                )
            )
        
        if not transformers:
            raise ValueError("Нет признаков для обучения. Проверьте предобработку.")

        preprocessor = ColumnTransformer(
            transformers=transformers,
            remainder="drop",
        )

        # Проверяем размерность данных для выбора подходящих моделей
        n_samples = len(X_train)
        
        models: dict[str, Any] = {
            "random_forest": RandomForestRegressor(
                n_estimators=rf_estimators, 
                random_state=random_state,
                max_depth=20,
                min_samples_split=5,
                n_jobs=-1
            ),
            "gradient_boosting": GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=random_state
            ),
            "linear_regression": LinearRegression(),
            "ridge": Ridge(alpha=1.0, random_state=random_state),
            "lasso": Lasso(alpha=0.1, random_state=random_state, max_iter=2000),
            "elastic_net": ElasticNet(alpha=0.1, l1_ratio=0.5, random_state=random_state, max_iter=2000),
        }
        
        # SVM только для небольших датасетов (может быть медленным)
        if n_samples < 5000:
            models["svr"] = SVR(kernel='rbf', C=100, gamma='scale', epsilon=0.1)

        for name, regressor in models.items():
            try:
                pipeline = Pipeline(
                    steps=[("preprocessor", preprocessor), ("model", regressor)]
                )
                pipeline.fit(X_train, y_train)
                predictions = pipeline.predict(X_test)
                
                # Проверяем на некорректные предсказания (NaN, Inf)
                if not np.isfinite(predictions).all():
                    print(f"Предупреждение: Модель {name} выдала некорректные предсказания (NaN/Inf). Пропускаем.")
                    continue
                
                # Проверяем на разумность метрик
                metrics = self._evaluate(y_test, predictions)
                
                # Если метрики явно некорректные (очень большие числа или отрицательный R² близкий к -inf)
                if abs(metrics['r2']) > 1e10 or metrics['rmse'] > 1e10:
                    print(f"Предупреждение: Модель {name} выдала некорректные метрики. Пропускаем.")
                    continue
                
                self.results[name] = ModelTrainingResult(
                    model_name=name, pipeline=pipeline, metrics=metrics
                )
            except Exception as e:
                print(f"Ошибка при обучении модели {name}: {e}")
                continue
                
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
        mse = mean_squared_error(y_true, y_pred)
        return {
            "mae": mean_absolute_error(y_true, y_pred),
            "mse": mse,
            "rmse": np.sqrt(mse),  # Вычисляем RMSE вручную для совместимости
            "r2": r2_score(y_true, y_pred),
        }

