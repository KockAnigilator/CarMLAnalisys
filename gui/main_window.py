from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QMainWindow, QTabWidget

from core import CarPricePredictor

from .analysis_tab import AnalysisTab
from .conclusions_tab import ConclusionsTab
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
        self.conclusions_tab = ConclusionsTab(self.predictor)

        self.data_tab.data_preprocessed.connect(self.analysis_tab.on_data_preprocessed)
        self.model_tab.models_trained.connect(self.conclusions_tab._refresh_conclusions)

        tabs.addTab(self.data_tab, "Данные")
        tabs.addTab(self.analysis_tab, "Аналитика")
        tabs.addTab(self.model_tab, "Модели")
        tabs.addTab(self.conclusions_tab, "Выводы")
        self.setCentralWidget(tabs)

    def _apply_styles(self) -> None:
        """Применяет строгий деловой стиль к приложению."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: #ffffff;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                color: #333333;
                padding: 8px 24px;
                margin-right: 1px;
                border: 1px solid #cccccc;
                border-bottom: none;
                font-size: 11pt;
                font-weight: normal;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #000000;
                border-bottom: 2px solid #2c3e50;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background-color: #f8f8f8;
            }
            QGroupBox {
                font-weight: 600;
                font-size: 10pt;
                border: 1px solid #cccccc;
                margin-top: 12px;
                padding-top: 18px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #2c3e50;
            }
            QPushButton {
                background-color: #2c3e50;
                color: #ffffff;
                border: 1px solid #1a252f;
                padding: 7px 18px;
                font-size: 10pt;
                font-weight: 500;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #34495e;
                border: 1px solid #2c3e50;
            }
            QPushButton:pressed {
                background-color: #1a252f;
            }
            QPushButton:disabled {
                background-color: #e0e0e0;
                color: #999999;
                border: 1px solid #cccccc;
            }
            QLineEdit, QSpinBox, QComboBox {
                border: 1px solid #cccccc;
                padding: 6px 8px;
                font-size: 10pt;
                background-color: #ffffff;
                min-height: 22px;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 2px solid #2c3e50;
                background-color: #fafafa;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid #333333;
                width: 0;
                height: 0;
            }
            QTextEdit {
                border: 1px solid #cccccc;
                background-color: #ffffff;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9pt;
                selection-background-color: #e3f2fd;
            }
            QTextEdit:focus {
                border: 2px solid #2c3e50;
            }
            QTableWidget {
                border: 1px solid #cccccc;
                background-color: #ffffff;
                gridline-color: #e0e0e0;
                selection-background-color: #e3f2fd;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #000000;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                padding: 6px;
                font-weight: 600;
                font-size: 9pt;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                text-align: center;
                font-weight: 500;
                font-size: 9pt;
                background-color: #f0f0f0;
                height: 22px;
            }
            QProgressBar::chunk {
                background-color: #2c3e50;
            }
            QLabel {
                color: #333333;
                font-size: 10pt;
            }
            QFormLayout {
                spacing: 8px;
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