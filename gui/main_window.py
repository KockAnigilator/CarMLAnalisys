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
        # Фиксированное разрешение 16:9
        self.setFixedSize(1600, 900)
        self._init_ui()
        self._apply_styles()

    def _init_ui(self) -> None:
        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.North)
        self.data_tab = DataTab(self.predictor)
        self.analysis_tab = AnalysisTab(self.predictor)
        self.model_tab = ModelTab(self.predictor)

        self.data_tab.data_preprocessed.connect(self.analysis_tab.on_data_preprocessed)

        tabs.addTab(self.data_tab, "📊 Данные")
        tabs.addTab(self.analysis_tab, "📈 Аналитика")
        tabs.addTab(self.model_tab, "🤖 Модели")
        self.setCentralWidget(tabs)

    def _apply_styles(self) -> None:
        """Применяет современные стили к приложению."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #d0d0d0;
                background-color: white;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                color: #333333;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-size: 12pt;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background-color: #2196F3;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #bbdefb;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 11pt;
                border: 2px solid #bdbdbd;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #2196F3;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 10pt;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
            QLineEdit, QSpinBox, QComboBox {
                border: 2px solid #bdbdbd;
                border-radius: 4px;
                padding: 6px;
                font-size: 10pt;
                background-color: white;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 2px solid #2196F3;
            }
            QTextEdit {
                border: 2px solid #bdbdbd;
                border-radius: 4px;
                background-color: white;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9pt;
            }
            QTableWidget {
                border: 2px solid #bdbdbd;
                border-radius: 4px;
                background-color: white;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #bbdefb;
                color: #000000;
            }
            QProgressBar {
                border: 2px solid #bdbdbd;
                border-radius: 4px;
                text-align: center;
                font-weight: bold;
                background-color: #e0e0e0;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
            QLabel {
                color: #333333;
                font-size: 10pt;
            }
        """)

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