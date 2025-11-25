from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from core import CarPricePredictor
from utils import FigureConverter, WorkerThread


class AnalysisTab(QWidget):
    """Display statistics and generated visualizations."""

    def __init__(self, predictor: CarPricePredictor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.predictor = predictor
        self.cleaned_ready = False
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        self.output_label = QLabel("Папка сохранения: ./artifacts")
        select_button = QPushButton("Изменить папку")
        select_button.clicked.connect(self._select_directory)

        analyze_button = QPushButton("Запустить анализ")
        analyze_button.clicked.connect(self._run_analysis)
        analyze_button.setEnabled(True)
        controls.addWidget(self.output_label)
        controls.addWidget(select_button)
        controls.addWidget(analyze_button)

        stats_box = QGroupBox("Файлы статистики")
        stats_layout = QVBoxLayout()
        self.numeric_label = QLabel("Числовые признаки: —")
        self.categorical_label = QLabel("Категориальные признаки: —")
        stats_layout.addWidget(self.numeric_label)
        stats_layout.addWidget(self.categorical_label)
        stats_box.setLayout(stats_layout)

        charts_box = QGroupBox("Визуализации")
        charts_layout = QHBoxLayout()
        self.hist_label = QLabel()
        self.box_label = QLabel()
        self.corr_label = QLabel()
        charts_layout.addWidget(self.hist_label)
        charts_layout.addWidget(self.box_label)
        charts_layout.addWidget(self.corr_label)
        charts_box.setLayout(charts_layout)

        self.progress = QProgressBar()

        layout.addLayout(controls)
        layout.addWidget(stats_box)
        layout.addWidget(charts_box)
        layout.addWidget(self.progress)

        self.output_dir = Path.cwd() / "artifacts"
        self.output_dir.mkdir(exist_ok=True)

    def on_data_preprocessed(self, *_args) -> None:
        self.cleaned_ready = True

    def _select_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Папка для сохранения", str(self.output_dir)
        )
        if directory:
            self.output_dir = Path(directory)
            self.output_label.setText(f"Папка сохранения: {directory}")

    def _run_analysis(self) -> None:
        if not self.cleaned_ready or self.predictor.cleaned_df is None:
            self.numeric_label.setText("Сначала выполните предобработку.")
            return

        worker = WorkerThread(self.predictor.analyze, self.output_dir)
        worker.signals.progress.connect(self.progress.setValue)
        worker.signals.finished.connect(self._on_analysis_ready)
        worker.signals.error.connect(self._on_error)
        worker.start()

    def _on_analysis_ready(self, artifacts) -> None:
        self.progress.setValue(100)
        if artifacts.numeric_stats_path:
            self.numeric_label.setText(
                f"Числовые признаки: {artifacts.numeric_stats_path}"
            )
        if artifacts.categorical_stats_path:
            self.categorical_label.setText(
                f"Категориальные признаки: {artifacts.categorical_stats_path}"
            )

        viz = artifacts.visualizations
        if viz and viz.price_hist:
            self.hist_label.setPixmap(FigureConverter.to_pixmap(viz.price_hist))
        if viz and viz.price_box:
            self.box_label.setPixmap(FigureConverter.to_pixmap(viz.price_box))
        if viz and viz.correlation_heatmap:
            self.corr_label.setPixmap(FigureConverter.to_pixmap(viz.correlation_heatmap))

    def _on_error(self, error: Exception) -> None:  # pragma: no cover - GUI feedback
        self.numeric_label.setText(f"Ошибка: {error}")
        self.progress.setValue(0)

