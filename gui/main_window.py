from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QMainWindow, QTabWidget

from core import CarPricePredictor

from .analysis_tab import AnalysisTab
from .data_tab import DataTab
from .model_tab import ModelTab


class MainWindow(QMainWindow):
    """Главное окно приложения с вкладками рабочего процесса."""

    def __init__(self, predictor: Optional[CarPricePredictor] = None) -> None:
        super().__init__()
        self.predictor = predictor or CarPricePredictor()
        self.setWindowTitle("Car ML Analysis")
        # Разрешение 16:9
        self.resize(1600, 900)
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

    def closeEvent(self, event) -> None:
        """Гарантируем завершение всех потоков при закрытии приложения."""
        # Вызываем cleanup для всех вкладок
        if hasattr(self, 'data_tab'):
            self.data_tab._cleanup_worker()
        if hasattr(self, 'analysis_tab'):
            self.analysis_tab._cleanup_worker()
        if hasattr(self, 'model_tab'):
            self.model_tab._cleanup_worker()
        event.accept()