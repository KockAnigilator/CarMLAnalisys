from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QMainWindow, QTabWidget

from core import CarPricePredictor

from .analysis_tab import AnalysisTab
from .data_tab import DataTab
from .model_tab import ModelTab


class MainWindow(QMainWindow):
    """Primary application window hosting the workflow tabs."""

    def __init__(self, predictor: Optional[CarPricePredictor] = None) -> None:
        super().__init__()
        self.predictor = predictor or CarPricePredictor()
        self.setWindowTitle("Car ML Analysis")
        self.resize(1400, 900)
        self._init_ui()

    def _init_ui(self) -> None:
        tabs = QTabWidget()
        self.data_tab = DataTab(self.predictor)
        self.analysis_tab = AnalysisTab(self.predictor)
        self.model_tab = ModelTab(self.predictor)

        self.data_tab.data_preprocessed.connect(self.analysis_tab.on_data_preprocessed)

        tabs.addTab(self.data_tab, "Данные")
        tabs.addTab(self.analysis_tab, "Аналитика")
        tabs.addTab(self.model_tab, "Модели")
        self.setCentralWidget(tabs)

