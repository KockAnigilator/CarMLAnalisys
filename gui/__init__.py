"""GUI-пакет, предоставляющий виджеты PySide6 для CarMLAnalysis."""

from .main_window import MainWindow
from .data_tab import DataTab
from .analysis_tab import AnalysisTab
from .model_tab import ModelTab

__all__ = ["MainWindow", "DataTab", "AnalysisTab", "ModelTab"]