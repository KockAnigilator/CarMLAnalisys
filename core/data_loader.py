from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Optional

import pandas as pd


@dataclass
class DataSummary:
    """Container describing the high-level characteristics of a dataset."""

    shape: tuple[int, int]
    head: pd.DataFrame
    dtypes: pd.Series
    missing: pd.DataFrame
    info: str


class DataLoader:
    """Handle locating CSV sources and loading them into pandas."""

    def __init__(self) -> None:
        self.dataframe: Optional[pd.DataFrame] = None
        self.source_path: Optional[Path] = None

    @staticmethod
    def find_csv_files(directory: str | Path) -> list[Path]:
        directory = Path(directory)
        return sorted(directory.glob("*.csv"))

    def load_csv(self, path: str | Path) -> pd.DataFrame:
        csv_path = Path(path)
        self.dataframe = pd.read_csv(csv_path)
        self.source_path = csv_path
        return self.dataframe.copy()

    def describe(self) -> DataSummary:
        if self.dataframe is None:
            raise ValueError("Dataset is not loaded yet.")

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

