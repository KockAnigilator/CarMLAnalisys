from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Optional

import pandas as pd


@dataclass
class DataSummary:
    """Контейнер, описывающий ключевые характеристики набора данных."""

    shape: tuple[int, int]
    head: pd.DataFrame
    dtypes: pd.Series
    missing: pd.DataFrame
    info: str


class DataLoader:
    """Отвечает за поиск CSV и загрузку их в pandas."""

    def __init__(self) -> None:
        self.dataframe: Optional[pd.DataFrame] = None
        self.source_path: Optional[Path] = None

    @staticmethod
    def find_csv_files(directory: str | Path) -> list[Path]:
        directory = Path(directory)
        return sorted(directory.glob("*.csv"))

    def load_csv(self, path: str | Path) -> pd.DataFrame:
        try:
            csv_path = Path(path)
            if not csv_path.exists():
                raise FileNotFoundError(f"Файл {csv_path} не существует")
            
            self.dataframe = pd.read_csv(csv_path)
            if self.dataframe.empty:
                raise ValueError("CSV файл пуст")
                
            self.source_path = csv_path
            return self.dataframe.copy()
        except Exception as e:
            self.dataframe = None
            self.source_path = None
            raise Exception(f"Ошибка загрузки CSV: {str(e)}") from e

    def describe(self) -> DataSummary:
        if self.dataframe is None:
            raise ValueError("Dataset is not loaded yet.")
        
        if self.dataframe.empty:
            raise ValueError("Dataset is empty.")

        buffer = StringIO()
        self.dataframe.info(buf=buffer)
        info_text = buffer.getvalue()
        missing = self.dataframe.isna().sum().rename("missing_count")
        missing_pct = (missing / len(self.dataframe) * 100).rename("missing_pct")
        missing_summary = pd.concat([missing, missing_pct], axis=1)

        return DataSummary(
            shape=self.dataframe.shape,
            head=self.dataframe.head(),
            dtypes=self.dataframe.dtypes,
            missing=missing_summary,
            info=info_text,
        )
