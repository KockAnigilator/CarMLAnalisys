from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
from PySide6.QtCore import Qt, Signal
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
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # Секция загрузки данных
        load_box = QGroupBox("Загрузка данных")
        load_layout = QHBoxLayout()
        load_layout.setSpacing(8)
        self.path_display = QLineEdit()
        self.path_display.setReadOnly(True)
        self.path_display.setPlaceholderText("Выберите CSV файл для загрузки...")
        load_button = QPushButton("Выбрать CSV")
        load_button.clicked.connect(self._select_file)
        load_layout.addWidget(QLabel("Файл:"))
        load_layout.addWidget(self.path_display, 1)
        load_layout.addWidget(load_button)
        load_box.setLayout(load_layout)

        # Статус загрузки
        self.status_label = QLabel("Статус: Данные не загружены")
        self.status_label.setStyleSheet("color: #666666; font-style: italic;")

        # Секция статистики и превью
        summary_box = QGroupBox("Статистика и превью данных")
        summary_layout = QGridLayout()
        summary_layout.setSpacing(8)
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setPlaceholderText("Статистика загруженных данных появится здесь...")
        self.preview_table = QTableWidget()
        self.preview_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectRows)
        summary_layout.addWidget(self.summary_text, 0, 0, 1, 1)
        summary_layout.addWidget(self.preview_table, 0, 1, 1, 1)
        summary_layout.setColumnStretch(0, 1)
        summary_layout.setColumnStretch(1, 2)
        summary_box.setLayout(summary_layout)

        # Секция предобработки
        preprocess_box = QGroupBox("Настройки предобработки")
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)
        self.target_input = QLineEdit("price")
        self.target_input.setPlaceholderText("Название столбца с целевой переменной")
        self.target_input.textChanged.connect(self._validate_target_column)
        self.drop_columns_input = QLineEdit("car_ID, carwidth")
        self.drop_columns_input.setPlaceholderText("Столбцы для удаления (через запятую)")
        self.missing_spin = QSpinBox()
        self.missing_spin.setRange(0, 100)
        self.missing_spin.setValue(30)
        self.missing_spin.setSuffix("%")
        self.preprocess_button = QPushButton("Запустить предобработку")
        self.preprocess_button.clicked.connect(self._run_preprocessing)
        self.preprocess_button.setEnabled(False)
        form.addRow("Целевая колонка:", self.target_input)
        form.addRow("Удалить столбцы:", self.drop_columns_input)
        form.addRow("Порог пропусков:", self.missing_spin)
        form.addRow("", self.preprocess_button)
        preprocess_box.setLayout(form)

        # Прогресс бар
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setTextVisible(True)

        main_layout.addWidget(load_box)
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(summary_box, 1)
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
                self, "Выберите CSV файл", str(Path.cwd()), "CSV Files (*.csv);;All Files (*)"
            )
            if not file_path:
                return
            
            # Проверяем расширение файла
            if not file_path.lower().endswith('.csv'):
                QMessageBox.warning(
                    self, 
                    "Предупреждение", 
                    "Выбранный файл не имеет расширения .csv. Продолжить?"
                )
            
            self.current_path = Path(file_path)
            self.path_display.setText(file_path)
            self.status_label.setText("Статус: Загрузка данных...")
            self.status_label.setStyleSheet("color: #2196F3; font-style: normal;")
            self._load_data(file_path)
        except Exception as e:
            error_msg = f"Ошибка при выборе файла:\n{str(e)}"
            QMessageBox.critical(self, "Ошибка", error_msg)
            self.status_label.setText(f"Статус: Ошибка - {str(e)}")
            self.status_label.setStyleSheet("color: #d32f2f; font-style: normal;")

    def _load_data(self, file_path: str) -> None:
        try:
            self._cleanup_worker()
            self.progress.setValue(0)
            
            # Валидация файла перед загрузкой
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Файл не найден: {file_path}")
            if path.stat().st_size == 0:
                raise ValueError("Файл пуст")
            
            self.current_worker = WorkerThread(self.predictor.load_data, file_path)
            self.current_worker.signals.progress.connect(self.progress.setValue)
            self.current_worker.signals.finished.connect(self._on_data_loaded)
            self.current_worker.signals.error.connect(self._on_error)
            self.current_worker.start()
        except FileNotFoundError as e:
            self._on_error(e, "Файл не найден")
        except ValueError as e:
            self._on_error(e, "Ошибка валидации файла")
        except Exception as e:
            self._on_error(e, "Неожиданная ошибка при загрузке")

    def _on_data_loaded(self, summary) -> None:
        try:
            self.progress.setValue(100)
            
            # Форматируем информацию о данных
            info_text = f"Размер данных: {humanize_shape(summary.shape)}\n"
            info_text += f"Строк: {summary.shape[0]}, Столбцов: {summary.shape[1]}\n\n"
            info_text += "Информация о данных:\n"
            info_text += summary.info
            info_text += "\n\nПропущенные значения:\n"
            missing_info = summary.missing[summary.missing['missing_count'] > 0]
            if len(missing_info) > 0:
                info_text += missing_info.to_string()
            else:
                info_text += "Пропущенных значений не обнаружено"
            
            self.summary_text.setPlainText(info_text)
            self._populate_table(summary.head)
            self.data_loaded.emit(self.predictor.raw_df)
            
            # Обновляем статус
            self.status_label.setText(
                f"Статус: Данные загружены успешно ({summary.shape[0]} строк, {summary.shape[1]} столбцов)"
            )
            self.status_label.setStyleSheet("color: #2e7d32; font-style: normal;")
            
            # Включаем кнопку предобработки
            self.preprocess_button.setEnabled(True)
            self._validate_target_column()
            
            # Очищаем worker после успешного завершения
            self._cleanup_worker()
        except Exception as e:
            self._on_error(e, "Ошибка при обработке загруженных данных")

    def _populate_table(self, dataframe: pd.DataFrame) -> None:
        try:
            # Ограничиваем количество отображаемых строк для производительности
            max_rows = min(100, len(dataframe))
            preview_df = dataframe.head(max_rows)
            
            self.preview_table.setRowCount(len(preview_df))
            self.preview_table.setColumnCount(len(preview_df.columns))
            self.preview_table.setHorizontalHeaderLabels(preview_df.columns.tolist())
            
            for row_idx, (_, row) in enumerate(preview_df.iterrows()):
                for col_idx, value in enumerate(row):
                    item = QTableWidgetItem(str(value))
                    # Форматируем числовые значения
                    try:
                        dtype = dataframe.dtypes.iloc[col_idx]
                        if pd.api.types.is_numeric_dtype(dtype):
                            num_val = float(value)
                            if pd.api.types.is_integer_dtype(dtype):
                                item.setText(str(int(num_val)))
                            else:
                                item.setText(f"{num_val:.2f}")
                    except (ValueError, TypeError, IndexError):
                        pass
                    self.preview_table.setItem(row_idx, col_idx, item)
            
            # Автоматически подгоняем ширину столбцов
            self.preview_table.resizeColumnsToContents()
            
            if len(dataframe) > max_rows:
                self.status_label.setText(
                    self.status_label.text() + f" (показано {max_rows} из {len(dataframe)} строк)"
                )
        except Exception as e:
            error_msg = f"Ошибка при заполнении таблицы: {str(e)}"
            print(error_msg)
            QMessageBox.warning(self, "Предупреждение", error_msg)

    def _validate_target_column(self) -> None:
        """Проверяет, существует ли целевая колонка в загруженных данных."""
        if self.predictor.raw_df is None:
            return
        
        target_col = self.target_input.text().strip()
        if target_col and target_col in self.predictor.raw_df.columns:
            self.target_input.setStyleSheet("")
        elif target_col:
            self.target_input.setStyleSheet("border: 2px solid #d32f2f;")

    def _run_preprocessing(self) -> None:
        try:
            if self.predictor.raw_df is None:
                QMessageBox.warning(
                    self, 
                    "Предупреждение", 
                    "Сначала загрузите данные.\n\nИспользуйте кнопку 'Выбрать CSV' для загрузки файла."
                )
                return

            # Валидация целевой колонки
            target_col = self.target_input.text().strip()
            if not target_col:
                QMessageBox.warning(
                    self,
                    "Ошибка валидации",
                    "Укажите название целевой колонки."
                )
                self.target_input.setFocus()
                return
            
            if target_col not in self.predictor.raw_df.columns:
                available_cols = ", ".join(self.predictor.raw_df.columns.tolist()[:10])
                QMessageBox.warning(
                    self,
                    "Ошибка валидации",
                    f"Колонка '{target_col}' не найдена в данных.\n\n"
                    f"Доступные колонки: {available_cols}"
                    + ("..." if len(self.predictor.raw_df.columns) > 10 else "")
                )
                self.target_input.setFocus()
                return

            self._cleanup_worker()
            self.progress.setValue(0)
            self.status_label.setText("Статус: Выполняется предобработка...")
            self.status_label.setStyleSheet("color: #2196F3; font-style: normal;")

            config = PreprocessingConfig(
                target_column=target_col,
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
        except ValueError as e:
            self._on_error(e, "Ошибка валидации параметров")
        except Exception as e:
            self._on_error(e, "Ошибка при запуске предобработки")

    def _on_preprocessed(self, dataframe: pd.DataFrame) -> None:
        try:
            self.progress.setValue(100)
            
            # Обновляем информацию
            preprocess_info = f"\n\n{'='*50}\n"
            preprocess_info += f"Предобработанные данные: {humanize_shape(dataframe.shape)}\n"
            preprocess_info += f"Строк: {dataframe.shape[0]}, Столбцов: {dataframe.shape[1]}\n"
            preprocess_info += f"{'='*50}\n"
            
            self.summary_text.append(preprocess_info)
            self.data_preprocessed.emit(dataframe)
            
            # Обновляем статус
            self.status_label.setText(
                f"Статус: Предобработка завершена успешно ({dataframe.shape[0]} строк, {dataframe.shape[1]} столбцов)"
            )
            self.status_label.setStyleSheet("color: #2e7d32; font-style: normal;")
            
            self._cleanup_worker()
        except Exception as e:
            self._on_error(e, "Ошибка при обработке предобработанных данных")

    def _on_error(self, error: Exception, context: str = "Ошибка") -> None:
        """Улучшенная обработка ошибок с детальными сообщениями."""
        error_type = type(error).__name__
        error_msg = str(error)
        
        # Формируем понятное сообщение для пользователя
        if isinstance(error, FileNotFoundError):
            user_msg = f"Файл не найден.\n\n{error_msg}"
        elif isinstance(error, ValueError):
            user_msg = f"Ошибка валидации данных.\n\n{error_msg}"
        elif isinstance(error, pd.errors.EmptyDataError):
            user_msg = "CSV файл пуст или поврежден."
        elif isinstance(error, pd.errors.ParserError):
            user_msg = f"Ошибка парсинга CSV файла.\n\nВозможные причины:\n- Неправильный разделитель\n- Поврежденный файл\n- Неподдерживаемая кодировка\n\nДетали: {error_msg}"
        elif isinstance(error, MemoryError):
            user_msg = "Недостаточно памяти для загрузки файла.\n\nПопробуйте использовать файл меньшего размера."
        elif isinstance(error, PermissionError):
            user_msg = "Нет доступа к файлу.\n\nУбедитесь, что файл не открыт в другой программе."
        else:
            user_msg = f"{context}\n\nТип ошибки: {error_type}\n\n{error_msg}"
        
        # Обновляем UI
        self.summary_text.append(f"\n[ОШИБКА] {user_msg}")
        self.progress.setValue(0)
        self.status_label.setText(f"Статус: Ошибка - {error_type}")
        self.status_label.setStyleSheet("color: #d32f2f; font-style: normal;")
        
        # Показываем диалог с ошибкой
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setWindowTitle("Ошибка")
        msg_box.setText(context)
        msg_box.setInformativeText(user_msg)
        msg_box.setDetailedText(f"Полная информация об ошибке:\n\n{error_type}: {error_msg}\n\n{error.__traceback__}")
        msg_box.exec()
        
        self._cleanup_worker()

    def closeEvent(self, event) -> None:
        """Гарантируем завершение потоков при закрытии вкладки."""
        self._cleanup_worker()
        event.accept()