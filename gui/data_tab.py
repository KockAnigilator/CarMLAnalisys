from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QProgressBar, QSizePolicy, QSpinBox, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget, QMessageBox
)

from core import CarPricePredictor, PreprocessingConfig
from utils import WorkerThread, humanize_shape


class DataTab(QWidget):
    """Отвечает за загрузку датасета и параметры предобработки."""

    data_loaded = Signal(pd.DataFrame)
    data_preprocessed = Signal(pd.DataFrame)

    def __init__(self, predictor: CarPricePredictor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.predictor = predictor
        self.current_path: Optional[Path] = None
        self.current_worker: Optional[WorkerThread] = None
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        load_box = QGroupBox("Загрузка данных")
        load_layout = QHBoxLayout()
        self.path_display = QLineEdit()
        self.path_display.setReadOnly(True)
        load_button = QPushButton("Выбрать CSV")
        load_button.clicked.connect(self._select_file)
        load_layout.addWidget(QLabel("Файл:"))
        load_layout.addWidget(self.path_display)
        load_layout.addWidget(load_button)
        load_box.setLayout(load_layout)

        summary_box = QGroupBox("Статистика и превью")
        summary_layout = QGridLayout()
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.preview_table = QTableWidget()
        self.preview_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        summary_layout.addWidget(self.summary_text, 0, 0)
        summary_layout.addWidget(self.preview_table, 0, 1)
        summary_box.setLayout(summary_layout)

        preprocess_box = QGroupBox("Настройки предобработки")
        form = QFormLayout()
        self.target_input = QLineEdit("price")
        self.drop_columns_input = QLineEdit("car_ID, carwidth")
        self.missing_spin = QSpinBox()
        self.missing_spin.setRange(0, 100)
        self.missing_spin.setValue(30)
        preprocess_button = QPushButton("Запустить предобработку")
        preprocess_button.clicked.connect(self._run_preprocessing)
        form.addRow("Целевая колонка:", self.target_input)
        form.addRow("Удалить столбцы:", self.drop_columns_input)
        form.addRow("Порог пропусков (%):", self.missing_spin)
        form.addRow(preprocess_button)
        preprocess_box.setLayout(form)

        self.progress = QProgressBar()
        self.progress.setValue(0)

        main_layout.addWidget(load_box)
        main_layout.addWidget(summary_box)
        main_layout.addWidget(preprocess_box)
        main_layout.addWidget(self.progress)

    def _cleanup_worker(self) -> None:
        """Безопасно завершает текущий worker."""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.stop()
        self.current_worker = None

    def _select_file(self) -> None:
        try:
            # Завершаем предыдущий worker если он есть
            self._cleanup_worker()
            
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Выберите CSV файл", str(Path.cwd()), "CSV Files (*.csv)"
            )
            if not file_path:
                return
            self.current_path = Path(file_path)
            self.path_display.setText(file_path)
            self._load_data(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при выборе файла: {str(e)}")

    def _load_data(self, file_path: str) -> None:
        try:
            self._cleanup_worker()
            
            self.current_worker = WorkerThread(self.predictor.load_data, file_path)
            self.current_worker.signals.progress.connect(self.progress.setValue)
            self.current_worker.signals.finished.connect(self._on_data_loaded)
            self.current_worker.signals.error.connect(self._on_error)
            self.current_worker.start()
        except Exception as e:
            self._on_error(e)

    def _on_data_loaded(self, summary) -> None:
        try:
            self.progress.setValue(100)
            self.summary_text.setPlainText(
                f"Размер: {humanize_shape(summary.shape)}\n\n{summary.info}"
            )
            self._populate_table(summary.head)
            self.data_loaded.emit(self.predictor.raw_df)
            # Очищаем worker после успешного завершения
            self._cleanup_worker()
        except Exception as e:
            self._on_error(e)

    def _populate_table(self, dataframe: pd.DataFrame) -> None:
        try:
            self.preview_table.setRowCount(len(dataframe))
            self.preview_table.setColumnCount(len(dataframe.columns))
            self.preview_table.setHorizontalHeaderLabels(dataframe.columns.tolist())
            for row_idx, (_, row) in enumerate(dataframe.iterrows()):
                for col_idx, value in enumerate(row):
                    self.preview_table.setItem(
                        row_idx, col_idx, QTableWidgetItem(str(value))
                    )
        except Exception as e:
            print(f"Ошибка при заполнении таблицы: {e}")

    def _run_preprocessing(self) -> None:
        try:
            if self.predictor.raw_df is None:
                self._on_error(ValueError("Сначала загрузите данные."))
                return

            self._cleanup_worker()

            config = PreprocessingConfig(
                target_column=self.target_input.text().strip(),
                drop_columns=[
                    col.strip()
                    for col in self.drop_columns_input.text().split(",")
                    if col.strip()
                ],
                high_missing_threshold=self.missing_spin.value() / 100,
            )

            self.current_worker = WorkerThread(self.predictor.preprocess_data, config)
            self.current_worker.signals.progress.connect(self.progress.setValue)
            self.current_worker.signals.finished.connect(self._on_preprocessed)
            self.current_worker.signals.error.connect(self._on_error)
            self.current_worker.start()
        except Exception as e:
            self._on_error(e)

    def _on_preprocessed(self, dataframe: pd.DataFrame) -> None:
        try:
            self.progress.setValue(100)
            self.summary_text.append(
                f"\nПредобработанные данные: {humanize_shape(dataframe.shape)}"
            )
            self.data_preprocessed.emit(dataframe)
            self._cleanup_worker()
        except Exception as e:
            self._on_error(e)

    def _on_error(self, error: Exception) -> None:
        error_msg = f"Ошибка: {error}"
        self.summary_text.append(f"\n{error_msg}")
        self.progress.setValue(0)
        QMessageBox.critical(self, "Ошибка", error_msg)
        self._cleanup_worker()

    def closeEvent(self, event) -> None:
        """Гарантируем завершение потоков при закрытии вкладки."""
        self._cleanup_worker()
        event.accept()