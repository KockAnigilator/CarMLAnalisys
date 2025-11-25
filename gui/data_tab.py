from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QProgressBar,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
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

    def _select_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите CSV файл", str(Path.cwd()), "CSV Files (*.csv)"
        )
        if not file_path:
            return
        self.current_path = Path(file_path)
        self.path_display.setText(file_path)
        self._load_data(file_path)

    def _load_data(self, file_path: str) -> None:
        worker = WorkerThread(self.predictor.load_data, file_path)
        worker.signals.progress.connect(self.progress.setValue)
        worker.signals.finished.connect(self._on_data_loaded)
        worker.signals.error.connect(self._on_error)
        worker.start()

    def _on_data_loaded(self, summary) -> None:
        self.progress.setValue(100)
        self.summary_text.setPlainText(
            f"Размер: {humanize_shape(summary.shape)}\n\n{summary.info}"
        )
        self._populate_table(summary.head)
        self.data_loaded.emit(self.predictor.raw_df)

    def _populate_table(self, dataframe: pd.DataFrame) -> None:
        self.preview_table.setRowCount(len(dataframe))
        self.preview_table.setColumnCount(len(dataframe.columns))
        self.preview_table.setHorizontalHeaderLabels(dataframe.columns.tolist())
        for row_idx, (_, row) in enumerate(dataframe.iterrows()):
            for col_idx, value in enumerate(row):
                self.preview_table.setItem(
                    row_idx, col_idx, QTableWidgetItem(str(value))
                )

    def _run_preprocessing(self) -> None:
        if self.predictor.raw_df is None:
            self._on_error(ValueError("Сначала загрузите данные."))
            return

        config = PreprocessingConfig(
            target_column=self.target_input.text().strip(),
            drop_columns=[
                col.strip()
                for col in self.drop_columns_input.text().split(",")
                if col.strip()
            ],
            high_missing_threshold=self.missing_spin.value() / 100,
        )

        worker = WorkerThread(self.predictor.preprocess_data, config)
        worker.signals.progress.connect(self.progress.setValue)
        worker.signals.finished.connect(self._on_preprocessed)
        worker.signals.error.connect(self._on_error)
        worker.start()

    def _on_preprocessed(self, dataframe: pd.DataFrame) -> None:
        self.progress.setValue(100)
        self.summary_text.append(
            f"\nПредобработанные данные: {humanize_shape(dataframe.shape)}"
        )
        self.data_preprocessed.emit(dataframe)

    def _on_error(self, error: Exception) -> None:  # pragma: no cover - обратная связь GUI
        self.summary_text.append(f"\nОшибка: {error}")
        self.progress.setValue(0)

