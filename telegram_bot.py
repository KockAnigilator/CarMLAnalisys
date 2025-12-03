"""
Telegram бот для получения метрик моделей машинного обучения.
Бот показывает JSON файл с метриками выбранной модели по запросу.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# API ключ Telegram бота
TELEGRAM_BOT_TOKEN = "8435012936:AAGbm2Mkmn8rzD73A8v4Nxd6vzqPzZuO4lc"

# Путь к файлу с метриками
METRICS_FILE = Path("artifacts") / "model_metrics.json"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    welcome_message = (
        "Добро пожаловать в бот для получения метрик моделей!\n\n"
        "Доступные команды:\n"
        "/start - показать это сообщение\n"
        "/models - показать список доступных моделей\n"
        "/metrics <имя_модели> - показать метрики выбранной модели в формате JSON\n"
        "/help - показать справку\n\n"
        "Пример: /metrics random_forest"
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help."""
    help_text = (
        "Справка по использованию бота:\n\n"
        "/models - получить список всех доступных моделей\n"
        "/metrics <имя_модели> - получить метрики модели в формате JSON\n\n"
        "Примеры:\n"
        "/metrics random_forest\n"
        "/metrics linear_regression\n\n"
        "Метрики включают:\n"
        "- MAE (Mean Absolute Error)\n"
        "- MSE (Mean Squared Error)\n"
        "- RMSE (Root Mean Squared Error)\n"
        "- R² (Coefficient of Determination)"
    )
    await update.message.reply_text(help_text)


async def list_models(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /models - показывает список доступных моделей."""
    try:
        if not METRICS_FILE.exists():
            await update.message.reply_text(
                " Файл с метриками не найден. "
                "Сначала обучите модели в приложении."
            )
            return

        with open(METRICS_FILE, 'r', encoding='utf-8') as f:
            metrics_data = json.load(f)

        if not metrics_data:
            await update.message.reply_text(" Нет доступных моделей.")
            return

        models_list = "Доступные модели:\n\n"
        for i, model_name in enumerate(metrics_data.keys(), 1):
            models_list += f"{i}. {model_name}\n"

        models_list += "\nИспользуйте /metrics <имя_модели> для получения метрик."
        await update.message.reply_text(models_list)

    except Exception as e:
        logger.error(f"Ошибка при получении списка моделей: {e}")
        await update.message.reply_text(
            f" Ошибка при получении списка моделей: {str(e)}"
        )


async def get_metrics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /metrics - показывает метрики выбранной модели."""
    try:
        if not METRICS_FILE.exists():
            await update.message.reply_text(
                " Файл с метриками не найден. "
                "Сначала обучите модели в приложении."
            )
            return

        # Получаем имя модели из аргументов команды
        if not context.args:
            await update.message.reply_text(
                "Укажите имя модели.\n"
                "Пример: /metrics random_forest\n"
                "Используйте /models для списка доступных моделей."
            )
            return

        model_name = " ".join(context.args).strip()

        with open(METRICS_FILE, 'r', encoding='utf-8') as f:
            metrics_data = json.load(f)

        if model_name not in metrics_data:
            available_models = ", ".join(metrics_data.keys())
            await update.message.reply_text(
                f"Модель '{model_name}' не найдена.\n\n"
                f"Доступные модели: {available_models}\n"
                "Используйте /models для полного списка."
            )
            return

        model_info = metrics_data[model_name]
        
        # Форматируем JSON для красивого отображения
        json_output = json.dumps(model_info, indent=2, ensure_ascii=False)
        
        # Отправляем JSON как документ для избежания проблем с парсингом
        import io
        json_bytes = json_output.encode('utf-8')
        json_file = io.BytesIO(json_bytes)
        json_file.name = f"{model_name}_metrics.json"
        
        # Отправляем файл с кратким описанием
        caption = f"Метрики модели: {model_name}"
        await update.message.reply_document(
            document=json_file,
            caption=caption
        )
        
        # Также отправляем краткую информацию текстом
        metrics_summary = model_info.get('metrics', {})
        summary_text = f"Метрики модели: {model_name}\n\n"
        for key, value in metrics_summary.items():
            summary_text += f"{key.upper()}: {value:.6f}\n"
        
        await update.message.reply_text(summary_text)

    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON: {e}")
        await update.message.reply_text(
            "Ошибка при чтении файла метрик. Файл поврежден."
        )
    except Exception as e:
        logger.error(f"Ошибка при получении метрик: {e}")
        await update.message.reply_text(
            f"Ошибка при получении метрик: {str(e)}"
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений."""
    text = update.message.text.lower()
    
    text_lower = text.lower()
    if "метрики" in text_lower or "metrics" in text_lower:
        await update.message.reply_text(
            "Используйте команду /metrics <имя_модели> для получения метрик.\n"
            "Пример: /metrics random_forest\n"
            "Используйте /models для списка доступных моделей."
        )
    elif "модели" in text_lower or "models" in text_lower:
        await list_models(update, context)
    else:
        await update.message.reply_text(
            "Не понимаю эту команду. Используйте /help для справки."
        )


def main() -> None:
    """Запускает Telegram бота."""
    # Создаем директорию для метрик, если её нет
    METRICS_FILE.parent.mkdir(exist_ok=True)
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("models", list_models))
    application.add_handler(CommandHandler("metrics", get_metrics))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем бота
    logger.info("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

