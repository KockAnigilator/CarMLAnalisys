from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core import CarPricePredictor
from utils import WorkerThread


class ModelTab(QWidget):
    """Обучает, оценивает и сохраняет модели машинного обучения."""

    def __init__(self, predictor: CarPricePredictor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.predictor = predictor
        self.models_ready = False
        self.selected_model = "random_forest"
        self.current_worker: Optional[WorkerThread] = None
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        config_box = QGroupBox("Параметры обучения")
        form = QFormLayout()
        self.test_size_input = QLineEdit("0.2")
        self.random_state_input = QLineEdit("42")
        self.estimators_input = QSpinBox()
        self.estimators_input.setRange(100, 1000)
        self.estimators_input.setValue(300)
        self.model_selector = QComboBox()
        self.model_selector.addItems(["random_forest", "linear_regression"])
        self.model_selector.currentTextChanged.connect(self._on_model_changed)
        train_button = QPushButton("Обучить модели")
        train_button.clicked.connect(self._train_models)
        form.addRow("Test size (0-1):", self.test_size_input)
        form.addRow("Random state:", self.random_state_input)
        form.addRow("Trees (RF):", self.estimators_input)
        form.addRow("Текущая модель:", self.model_selector)
        form.addWidget(train_button)
        config_box.setLayout(form)

        metrics_box = QGroupBox("Метрики")
        metrics_layout = QVBoxLayout()
        self.metrics_text = QTextEdit()
        self.metrics_text.setReadOnly(True)
        metrics_layout.addWidget(self.metrics_text)
        metrics_box.setLayout(metrics_layout)

        model_actions = QHBoxLayout()
        save_button = QPushButton("Сохранить выбранную модель")
        save_button.clicked.connect(self._save_model)
        load_button = QPushButton("Загрузить модель")
        load_button.clicked.connect(self._load_model)
        predict_button = QPushButton("Предсказать по CSV")
        predict_button.clicked.connect(self._predict_new_data)
        model_actions.addWidget(save_button)
        model_actions.addWidget(load_button)
        model_actions.addWidget(predict_button)

        self.progress = QProgressBar()

        layout.addWidget(config_box)
        layout.addWidget(metrics_box)
        layout.addLayout(model_actions)
        layout.addWidget(self.progress)

    def _cleanup_worker(self) -> None:
        """Безопасно завершает текущий worker."""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.stop()
        self.current_worker = None

    def _on_model_changed(self, model_name: str) -> None:
        if model_name:
            self.selected_model = model_name

    def _train_models(self) -> None:
        if self.predictor.cleaned_df is None:
            self.metrics_text.setPlainText("Сначала выполните предобработку данных.")
            return
        try:
            test_size = float(self.test_size_input.text())
            random_state = int(self.random_state_input.text())
        except ValueError:
            self.metrics_text.setPlainText("Проверьте корректность параметров.")
            return

        self._cleanup_worker()

        self.current_worker = WorkerThread(
            self.predictor.train_models,
            test_size=test_size,
            random_state=random_state,
            rf_estimators=self.estimators_input.value(),
        )
        self.current_worker.signals.progress.connect(self.progress.setValue)
        self.current_worker.signals.finished.connect(self._on_trained)
        self.current_worker.signals.error.connect(self._on_error)
        self.current_worker.start()

    def _on_trained(self, results) -> None:
        self.progress.setValue(100)
        self.models_ready = True
        self._refresh_model_selector(results.keys())
        message_lines = []
        for name, result in results.items():
            metrics = ", ".join(f"{k.upper()}: {v:.4f}" for k, v in result.metrics.items())
            message_lines.append(f"{name}: {metrics}")
        self.metrics_text.setPlainText("\n".join(message_lines))
        self._cleanup_worker()

    def _save_model(self) -> None:
        if not self.models_ready:
            self.metrics_text.append("Нет обученных моделей для сохранения.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить модель", f"{self.selected_model}.joblib", "Joblib (*.joblib)"
        )
        if not path:
            return
        saved_path = self.predictor.save_model(self.selected_model, path)
        self.metrics_text.append(f"Модель сохранена: {saved_path}")

    def _load_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Загрузить модель", str(Path.cwd()), "Joblib (*.joblib)"
        )
        if not path:
            return
        result = self.predictor.load_model(path)
        self.selected_model = result.model_name
        if self.model_selector.findText(result.model_name) == -1:
            self.model_selector.addItem(result.model_name)
        self.model_selector.setCurrentText(result.model_name)
        metrics = ", ".join(f"{k.upper()}: {v:.4f}" for k, v in result.metrics.items())
        self.metrics_text.append(f"Загружена модель {result.model_name}: {metrics}")
        self.models_ready = True

    def _predict_new_data(self) -> None:
        if not self.models_ready:
            self.metrics_text.append("Сначала обучите или загрузите модель.")
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "CSV для предсказаний", str(Path.cwd()), "CSV Files (*.csv)"
        )
        if not file_path:
            return
        
        try:
            dataframe = pd.read_csv(file_path)
            if dataframe.empty:
                self.metrics_text.append("Ошибка: CSV файл пуст.")
                return
            
            # Используем predict_raw для автоматической предобработки
            preds = self.predictor.predict_raw(dataframe, self.selected_model)
            
            # Показываем только предсказания
            preview_cols = [col for col in preds.columns if col == 'predicted_price' or col in dataframe.columns[:5]]
            preview = preds[preview_cols].head(10).to_string(index=False)
            self.metrics_text.append(f"Предсказания ({self.selected_model}):\n{preview}")
            
            # Предложить сохранение
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Сохранить предсказания", "predictions.csv", "CSV Files (*.csv)"
            )
            if save_path:
                preds.to_csv(save_path, index=False)
                self.metrics_text.append(f"Предсказания сохранены в: {save_path}")
        except Exception as e:
            self.metrics_text.append(f"Ошибка при предсказании: {str(e)}")

    def _refresh_model_selector(self, model_names) -> None:
        self.model_selector.blockSignals(True)
        self.model_selector.clear()
        self.model_selector.addItems(list(model_names))
        if self.selected_model in model_names:
            self.model_selector.setCurrentText(self.selected_model)
        else:
            self.model_selector.setCurrentIndex(0)
            self.selected_model = self.model_selector.currentText()
        self.model_selector.blockSignals(False)

    def _on_error(self, error: Exception) -> None:  # pragma: no cover - обратная связь GUI
        self.metrics_text.append(f"Ошибка: {error}")
        self.progress.setValue(0)
        self._cleanup_worker()

    def closeEvent(self, event) -> None:
        """Гарантируем завершение потоков при закрытии вкладки."""
        self._cleanup_worker()
        event.accept()

