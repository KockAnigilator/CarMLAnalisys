from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QMessageBox,
    QGridLayout,
)

from core import CarPricePredictor
from utils import FigureConverter, WorkerThread


class AnalysisTab(QWidget):
    """Показывает статистику и построенные визуализации."""

    def __init__(self, predictor: CarPricePredictor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.predictor = predictor
        self.cleaned_ready = False
        self.current_worker: Optional[WorkerThread] = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # Секция управления
        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.output_label = QLabel("Папка сохранения: ./artifacts")
        select_button = QPushButton("Изменить папку")
        select_button.clicked.connect(self._select_directory)

        self.analyze_button = QPushButton("Запустить анализ")
        self.analyze_button.clicked.connect(self._run_analysis)
        self.analyze_button.setEnabled(False)
        controls.addWidget(self.output_label)
        controls.addWidget(select_button)
        controls.addWidget(self.analyze_button)

        # Статус
        self.status_label = QLabel("Статус: Данные не предобработаны")
        self.status_label.setStyleSheet("color: #666666; font-style: italic;")

        # Секция статистики
        stats_box = QGroupBox("Файлы статистики")
        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(8)
        self.numeric_label = QLabel("Числовые признаки: —")
        self.categorical_label = QLabel("Категориальные признаки: —")
        stats_layout.addWidget(self.numeric_label)
        stats_layout.addWidget(self.categorical_label)
        stats_box.setLayout(stats_layout)

        # Секция визуализаций с прокруткой
        charts_box = QGroupBox("Визуализации")
        charts_main_layout = QVBoxLayout()
        
        # Используем GridLayout для лучшего расположения графиков
        charts_grid = QGridLayout()
        charts_grid.setSpacing(10)
        
        # Создаем ScrollArea для графиков
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)
        
        charts_container = QWidget()
        charts_layout = QGridLayout(charts_container)
        charts_layout.setSpacing(15)
        
        # Создаем QLabel для каждого графика с правильным масштабированием
        self.hist_label = QLabel()
        self.hist_label.setAlignment(Qt.AlignCenter)
        self.hist_label.setScaledContents(False)
        self.hist_label.setText("Гистограмма распределения цены")
        self.hist_label.setStyleSheet("border: 1px solid #cccccc; background-color: #fafafa; min-height: 300px;")
        
        self.box_label = QLabel()
        self.box_label.setAlignment(Qt.AlignCenter)
        self.box_label.setScaledContents(False)
        self.box_label.setText("Boxplot цены")
        self.box_label.setStyleSheet("border: 1px solid #cccccc; background-color: #fafafa; min-height: 300px;")
        
        self.corr_label = QLabel()
        self.corr_label.setAlignment(Qt.AlignCenter)
        self.corr_label.setScaledContents(False)
        self.corr_label.setText("Тепловая карта корреляций")
        self.corr_label.setStyleSheet("border: 1px solid #cccccc; background-color: #fafafa; min-height: 300px;")
        
        # Размещаем графики в сетке
        charts_layout.addWidget(QLabel("Гистограмма распределения цены"), 0, 0)
        charts_layout.addWidget(self.hist_label, 1, 0)
        charts_layout.addWidget(QLabel("Boxplot цены"), 0, 1)
        charts_layout.addWidget(self.box_label, 1, 1)
        charts_layout.addWidget(QLabel("Тепловая карта корреляций"), 0, 2)
        charts_layout.addWidget(self.corr_label, 1, 2)
        
        charts_layout.setColumnStretch(0, 1)
        charts_layout.setColumnStretch(1, 1)
        charts_layout.setColumnStretch(2, 1)
        
        scroll_area.setWidget(charts_container)
        charts_main_layout.addWidget(scroll_area)
        charts_box.setLayout(charts_main_layout)

        # Прогресс бар
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(True)

        layout.addLayout(controls)
        layout.addWidget(self.status_label)
        layout.addWidget(stats_box)
        layout.addWidget(charts_box, 1)
        layout.addWidget(self.progress)

        self.output_dir = Path.cwd() / "artifacts"
        self.output_dir.mkdir(exist_ok=True)

    def _cleanup_worker(self) -> None:
        """Безопасно завершает текущий worker."""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.stop()
        self.current_worker = None

    def on_data_preprocessed(self, *_args) -> None:
        self.cleaned_ready = True
        self.analyze_button.setEnabled(True)
        self.status_label.setText("Статус: Данные готовы к анализу")
        self.status_label.setStyleSheet("color: #2e7d32; font-style: normal;")

    def _select_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Папка для сохранения", str(self.output_dir)
        )
        if directory:
            self.output_dir = Path(directory)
            self.output_label.setText(f"Папка сохранения: {directory}")

    def _run_analysis(self) -> None:
        if not self.cleaned_ready or self.predictor.cleaned_df is None:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Сначала выполните предобработку данных на вкладке 'Данные'."
            )
            return

        self._cleanup_worker()
        self.progress.setValue(0)
        self.status_label.setText("Статус: Выполняется анализ...")
        self.status_label.setStyleSheet("color: #2196F3; font-style: normal;")

        self.current_worker = WorkerThread(self.predictor.analyze, self.output_dir)
        self.current_worker.signals.progress.connect(self.progress.setValue)
        self.current_worker.signals.finished.connect(self._on_analysis_ready)
        self.current_worker.signals.error.connect(self._on_error)
        self.current_worker.start()

    def _on_analysis_ready(self, artifacts) -> None:
        try:
            self.progress.setValue(100)
            
            # Обновляем информацию о файлах статистики
            if artifacts.numeric_stats_path:
                self.numeric_label.setText(
                    f"Числовые признаки: {artifacts.numeric_stats_path.name}"
                )
            if artifacts.categorical_stats_path:
                self.categorical_label.setText(
                    f"Категориальные признаки: {artifacts.categorical_stats_path.name}"
                )

            # Отображаем графики с правильным масштабированием
            viz = artifacts.visualizations
            if viz:
                # Максимальный размер для графиков
                max_width = 600
                max_height = 400
                
                if viz.price_hist:
                    pixmap = FigureConverter.to_pixmap(viz.price_hist)
                    # Масштабируем сохраняя пропорции
                    scaled_pixmap = pixmap.scaled(
                        max_width, max_height, 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    self.hist_label.setPixmap(scaled_pixmap)
                    self.hist_label.setText("")
                
                if viz.price_box:
                    pixmap = FigureConverter.to_pixmap(viz.price_box)
                    scaled_pixmap = pixmap.scaled(
                        max_width, max_height,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.box_label.setPixmap(scaled_pixmap)
                    self.box_label.setText("")
                
                if viz.correlation_heatmap:
                    pixmap = FigureConverter.to_pixmap(viz.correlation_heatmap)
                    scaled_pixmap = pixmap.scaled(
                        max_width, max_height,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.corr_label.setPixmap(scaled_pixmap)
                    self.corr_label.setText("")
            
            # Обновляем статус
            self.status_label.setText("Статус: Анализ завершен успешно")
            self.status_label.setStyleSheet("color: #2e7d32; font-style: normal;")
            
            self._cleanup_worker()
        except Exception as e:
            self._on_error(e)

    def _on_error(self, error: Exception) -> None:
        """Улучшенная обработка ошибок."""
        error_msg = str(error)
        error_type = type(error).__name__
        
        self.numeric_label.setText(f"Ошибка: {error_type}")
        self.progress.setValue(0)
        self.status_label.setText(f"Статус: Ошибка - {error_type}")
        self.status_label.setStyleSheet("color: #d32f2f; font-style: normal;")
        
        QMessageBox.critical(
            self,
            "Ошибка анализа",
            f"Произошла ошибка при выполнении анализа:\n\n{error_msg}"
        )
        
        self._cleanup_worker()

    def closeEvent(self, event) -> None:
        """Гарантируем завершение потоков при закрытии вкладки."""
        self._cleanup_worker()
        event.accept()

