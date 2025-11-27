from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


@dataclass
class PreprocessingConfig:
    """Параметры предобработки, доступные пользователю."""

    target_column: str = "price"
    drop_columns: list[str] = field(default_factory=lambda: ["car_ID", "carwidth"])
    high_missing_threshold: float = 0.3
    drop_constant: bool = True
    encode_columns: Optional[list[str]] = None


class DataPreprocessor:
    """Выполняет очистку, заполнение пропусков и кодирование категорий."""

    def __init__(self, config: Optional[PreprocessingConfig] = None) -> None:
        self.config = config or PreprocessingConfig()
        self.cleaned_frame: Optional[pd.DataFrame] = None

    def preprocess(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        df = dataframe.copy()
        df = self._drop_high_missing(df)
        df = self._drop_columns(df)
        if self.config.drop_constant:
            df = self._drop_constant(df)
        df = self._fill_missing(df)
        df = self._encode_categoricals(df)
        self.cleaned_frame = df
        return df

    def _drop_high_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        threshold = int(len(df) * self.config.high_missing_threshold)
        mask = df.isna().sum()
        columns_to_drop = mask[mask > threshold].index.tolist()
        return df.drop(columns=columns_to_drop)

    def _drop_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        cols = [col for col in self.config.drop_columns if col in df.columns]
        return df.drop(columns=cols, errors="ignore")

    def _drop_constant(self, df: pd.DataFrame) -> pd.DataFrame:
        nunique = df.nunique()
        constant_cols = nunique[nunique <= 1].index.tolist()
        return df.drop(columns=constant_cols)

    def _fill_missing(self, df: pd.DataFrame) -> pd.DataFrame:
        numeric_cols = df.select_dtypes(include="number").columns
        categorical_cols = df.select_dtypes(exclude="number").columns

        # Заполнение числовых столбцов медианой
        if len(numeric_cols) > 0:
            df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
        
        # Заполнение категориальных столбцов модой
        for col in categorical_cols:
            if df[col].isna().any():
                mode_values = df[col].mode()
                if len(mode_values) > 0:
                    df[col] = df[col].fillna(mode_values.iloc[0])
                else:
                    # Если моды нет, заполняем строкой "Unknown"
                    df[col] = df[col].fillna("Unknown")
        return df

    def _encode_categoricals(self, df: pd.DataFrame) -> pd.DataFrame:
        categorical_cols = df.select_dtypes(exclude="number").columns.tolist()
        if not categorical_cols:
            return df

        if self.config.encode_columns:
            categorical_cols = [
                col for col in categorical_cols if col in self.config.encode_columns
            ]
        
        # Проверяем, что есть что кодировать
        if categorical_cols:
            try:
                return pd.get_dummies(df, columns=categorical_cols, drop_first=True)
            except Exception as e:
                # Если ошибка кодирования, возвращаем исходные данные
                print(f"Предупреждение: Не удалось закодировать категориальные признаки: {e}")
                return df
        return df

