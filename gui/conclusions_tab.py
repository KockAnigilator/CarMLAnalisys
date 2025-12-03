from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

from core import CarPricePredictor


class ConclusionsTab(QWidget):
    """Вкладка с выводами и рекомендациями по результатам анализа."""

    def __init__(self, predictor: CarPricePredictor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.predictor = predictor
        self._init_ui()
        self._refresh_conclusions()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # Кнопка обновления выводов
        refresh_layout = QHBoxLayout()
        refresh_button = QPushButton("Обновить выводы")
        refresh_button.clicked.connect(self._refresh_conclusions)
        self.status_label = QLabel("Статус: Выводы не сгенерированы")
        self.status_label.setStyleSheet("color: #666666; font-style: italic;")
        refresh_layout.addWidget(refresh_button)
        refresh_layout.addWidget(self.status_label, 1)
        layout.addLayout(refresh_layout)

        # Секция сравнения моделей
        models_box = QGroupBox("Сравнение моделей")
        models_layout = QVBoxLayout()
        
        # Таблица сравнения
        self.models_table = QTableWidget()
        self.models_table.setColumnCount(5)
        self.models_table.setHorizontalHeaderLabels([
            "Модель", "MAE", "RMSE", "R²", "Рейтинг"
        ])
        self.models_table.setAlternatingRowColors(True)
        self.models_table.setSelectionBehavior(QTableWidget.SelectRows)
        models_layout.addWidget(self.models_table)
        models_box.setLayout(models_layout)

        # Секция выводов и рекомендаций
        conclusions_box = QGroupBox("Выводы и рекомендации")
        conclusions_layout = QVBoxLayout()
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(300)
        
        self.conclusions_text = QTextEdit()
        self.conclusions_text.setReadOnly(True)
        self.conclusions_text.setPlaceholderText(
            "Выводы появятся здесь после обучения моделей.\n"
            "Нажмите 'Обновить выводы' для генерации."
        )
        scroll_area.setWidget(self.conclusions_text)
        
        conclusions_layout.addWidget(scroll_area)
        conclusions_box.setLayout(conclusions_layout)

        # Секция статистики данных
        data_stats_box = QGroupBox("Статистика данных")
        data_stats_layout = QVBoxLayout()
        self.data_stats_text = QTextEdit()
        self.data_stats_text.setReadOnly(True)
        self.data_stats_text.setPlaceholderText("Статистика данных появится здесь...")
        data_stats_layout.addWidget(self.data_stats_text)
        data_stats_box.setLayout(data_stats_layout)

        layout.addWidget(models_box, 1)
        layout.addWidget(conclusions_box, 1)
        layout.addWidget(data_stats_box, 1)

    def _refresh_conclusions(self) -> None:
        """Обновляет выводы на основе текущих данных и моделей."""
        try:
            # Проверяем наличие данных
            if self.predictor.cleaned_df is None:
                self._show_no_data_message()
                return

            # Загружаем метрики моделей
            metrics_data = self._load_metrics()
            if not metrics_data:
                self._show_no_models_message()
                return

            # Обновляем таблицу сравнения моделей
            self._update_models_table(metrics_data)

            # Генерируем выводы
            conclusions = self._generate_conclusions(metrics_data)
            self.conclusions_text.setPlainText(conclusions)

            # Обновляем статистику данных
            self._update_data_stats()

            self.status_label.setText("Статус: Выводы обновлены")
            self.status_label.setStyleSheet("color: #2e7d32; font-style: normal;")

        except Exception as e:
            self.status_label.setText(f"Статус: Ошибка - {str(e)}")
            self.status_label.setStyleSheet("color: #d32f2f; font-style: normal;")
            QMessageBox.warning(self, "Ошибка", f"Не удалось обновить выводы:\n{str(e)}")

    def _load_metrics(self) -> dict:
        """Загружает метрики моделей из JSON файла."""
        metrics_file = Path("artifacts") / "model_metrics.json"
        if not metrics_file.exists():
            return {}
        
        try:
            with open(metrics_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки метрик: {e}")
            return {}

    def _update_models_table(self, metrics_data: dict) -> None:
        """Обновляет таблицу сравнения моделей."""
        if not metrics_data:
            self.models_table.setRowCount(0)
            return

        # Сортируем модели по R² (лучшие первыми)
        sorted_models = sorted(
            metrics_data.items(),
            key=lambda x: x[1]['metrics'].get('r2', -float('inf')),
            reverse=True
        )

        self.models_table.setRowCount(len(sorted_models))

        for row_idx, (model_name, model_data) in enumerate(sorted_models):
            metrics = model_data.get('metrics', {})
            
            # Название модели
            self.models_table.setItem(row_idx, 0, QTableWidgetItem(model_name))
            
            # MAE
            mae = metrics.get('mae', 0)
            mae_item = QTableWidgetItem(f"{mae:.2f}")
            self.models_table.setItem(row_idx, 1, mae_item)
            
            # RMSE
            rmse = metrics.get('rmse', 0)
            rmse_item = QTableWidgetItem(f"{rmse:.2f}")
            self.models_table.setItem(row_idx, 2, rmse_item)
            
            # R²
            r2 = metrics.get('r2', 0)
            r2_item = QTableWidgetItem(f"{r2:.4f}")
            # Цветовая индикация для R²
            if r2 > 0.8:
                r2_item.setBackground(QColor(200, 255, 200))  # Светло-зеленый
            elif r2 > 0.6:
                r2_item.setBackground(QColor(255, 255, 200))  # Светло-желтый
            else:
                r2_item.setBackground(QColor(240, 240, 240))  # Светло-серый
            self.models_table.setItem(row_idx, 3, r2_item)
            
            # Рейтинг
            rating = f"#{row_idx + 1}"
            rating_item = QTableWidgetItem(rating)
            rating_item.setTextAlignment(Qt.AlignCenter)
            self.models_table.setItem(row_idx, 4, rating_item)

        # Автоматическая подгонка ширины столбцов
        self.models_table.resizeColumnsToContents()

    def _generate_conclusions(self, metrics_data: dict) -> str:
        """Генерирует выводы и рекомендации на основе метрик моделей."""
        if not metrics_data:
            return "Нет данных для анализа."

        conclusions = []
        conclusions.append("=" * 60)
        conclusions.append("ВЫВОДЫ И РЕКОМЕНДАЦИИ")
        conclusions.append("=" * 60)
        conclusions.append("")

        # Находим лучшую модель
        best_model = max(
            metrics_data.items(),
            key=lambda x: x[1]['metrics'].get('r2', -float('inf'))
        )
        best_name, best_data = best_model
        best_metrics = best_data['metrics']

        conclusions.append("ЛУЧШАЯ МОДЕЛЬ:")
        conclusions.append(f"  Модель: {best_name}")
        conclusions.append(f"  R² (коэффициент детерминации): {best_metrics.get('r2', 0):.4f}")
        conclusions.append(f"  MAE (средняя абсолютная ошибка): {best_metrics.get('mae', 0):.2f}")
        conclusions.append(f"  RMSE (корень из средней квадратичной ошибки): {best_metrics.get('rmse', 0):.2f}")
        conclusions.append("")

        # Анализ качества моделей
        conclusions.append("АНАЛИЗ КАЧЕСТВА МОДЕЛЕЙ:")
        r2_scores = {name: data['metrics'].get('r2', 0) 
                    for name, data in metrics_data.items()}
        
        excellent = [name for name, r2 in r2_scores.items() if r2 > 0.8]
        good = [name for name, r2 in r2_scores.items() if 0.6 < r2 <= 0.8]
        poor = [name for name, r2 in r2_scores.items() if r2 <= 0.6]

        if excellent:
            conclusions.append(f"  Отличное качество (R² > 0.8): {', '.join(excellent)}")
        if good:
            conclusions.append(f"  Хорошее качество (0.6 < R² ≤ 0.8): {', '.join(good)}")
        if poor:
            conclusions.append(f"  Низкое качество (R² ≤ 0.6): {', '.join(poor)}")
        conclusions.append("")

        # Рекомендации
        conclusions.append("РЕКОМЕНДАЦИИ:")
        
        if best_metrics.get('r2', 0) > 0.8:
            conclusions.append("  ✓ Модель показывает отличное качество предсказаний.")
            conclusions.append("  ✓ Можно использовать для практических применений.")
        elif best_metrics.get('r2', 0) > 0.6:
            conclusions.append("  ⚠ Модель показывает приемлемое качество.")
            conclusions.append("  ⚠ Рекомендуется дополнительная настройка параметров.")
        else:
            conclusions.append("  ✗ Модель показывает низкое качество.")
            conclusions.append("  ✗ Рекомендуется:")
            conclusions.append("    - Проверить качество данных")
            conclusions.append("    - Попробовать другие алгоритмы")
            conclusions.append("    - Увеличить объем обучающих данных")
        
        conclusions.append("")

        # Сравнение моделей
        conclusions.append("СРАВНИТЕЛЬНЫЙ АНАЛИЗ:")
        sorted_by_r2 = sorted(
            metrics_data.items(),
            key=lambda x: x[1]['metrics'].get('r2', -float('inf')),
            reverse=True
        )
        
        for idx, (name, data) in enumerate(sorted_by_r2[:3], 1):
            metrics = data['metrics']
            conclusions.append(f"  {idx}. {name}:")
            conclusions.append(f"     R² = {metrics.get('r2', 0):.4f}, "
                             f"MAE = {metrics.get('mae', 0):.2f}, "
                             f"RMSE = {metrics.get('rmse', 0):.2f}")
        
        conclusions.append("")

        # Общие выводы
        conclusions.append("ОБЩИЕ ВЫВОДЫ:")
        avg_r2 = sum(r2_scores.values()) / len(r2_scores) if r2_scores else 0
        conclusions.append(f"  Средний R² по всем моделям: {avg_r2:.4f}")
        
        if avg_r2 > 0.7:
            conclusions.append("  Данные хорошо подходят для машинного обучения.")
        elif avg_r2 > 0.5:
            conclusions.append("  Данные требуют дополнительной предобработки.")
        else:
            conclusions.append("  Данные могут быть недостаточно информативными.")
        
        conclusions.append("")

        return "\n".join(conclusions)

    def _update_data_stats(self) -> None:
        """Обновляет статистику данных."""
        if self.predictor.cleaned_df is None:
            self.data_stats_text.setPlainText("Данные не загружены.")
            return

        df = self.predictor.cleaned_df
        stats = []
        stats.append("СТАТИСТИКА ДАННЫХ")
        stats.append("=" * 40)
        stats.append(f"Размер данных: {df.shape[0]} строк × {df.shape[1]} столбцов")
        stats.append("")

        # Типы данных
        numeric_cols = df.select_dtypes(include='number').columns.tolist()
        categorical_cols = df.select_dtypes(exclude='number').columns.tolist()
        
        stats.append(f"Числовых признаков: {len(numeric_cols)}")
        stats.append(f"Категориальных признаков: {len(categorical_cols)}")
        stats.append("")

        # Пропущенные значения
        missing = df.isna().sum()
        missing_cols = missing[missing > 0]
        if len(missing_cols) > 0:
            stats.append(f"Столбцов с пропусками: {len(missing_cols)}")
            stats.append("Столбцы с наибольшим количеством пропусков:")
            for col, count in missing_cols.head(5).items():
                pct = (count / len(df)) * 100
                stats.append(f"  {col}: {count} ({pct:.1f}%)")
        else:
            stats.append("Пропущенных значений не обнаружено")
        
        stats.append("")

        # Основные статистики для числовых признаков
        if len(numeric_cols) > 0:
            stats.append("Основные статистики (числовые признаки):")
            desc = df[numeric_cols].describe()
            stats.append(desc.to_string())

        self.data_stats_text.setPlainText("\n".join(stats))

    def _show_no_data_message(self) -> None:
        """Показывает сообщение об отсутствии данных."""
        self.conclusions_text.setPlainText(
            "Данные не загружены или не предобработаны.\n\n"
            "Перейдите на вкладку 'Данные' и выполните предобработку."
        )
        self.models_table.setRowCount(0)
        self.data_stats_text.setPlainText("Данные не загружены.")
        self.status_label.setText("Статус: Данные не загружены")
        self.status_label.setStyleSheet("color: #d32f2f; font-style: normal;")

    def _show_no_models_message(self) -> None:
        """Показывает сообщение об отсутствии обученных моделей."""
        self.conclusions_text.setPlainText(
            "Модели не обучены.\n\n"
            "Перейдите на вкладку 'Модели' и обучите модели для получения выводов."
        )
        self.models_table.setRowCount(0)
        self.status_label.setText("Статус: Модели не обучены")
        self.status_label.setStyleSheet("color: #d32f2f; font-style: normal;")

