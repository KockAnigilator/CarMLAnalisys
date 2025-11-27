from __future__ import annotations

import sys
import warnings
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox

from core import CarPricePredictor
from gui.main_window import MainWindow  # Измените импорт


def excepthook(exc_type, exc_value, exc_tb):
    """Глобальный обработчик исключений для Qt"""
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(f"Необработанное исключение: {tb}")
    
    # Показываем сообщение об ошибке
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Critical)
    msg.setText("Произошла критическая ошибка")
    msg.setInformativeText(f"{exc_type.__name__}: {exc_value}")
    msg.setWindowTitle("Ошибка")
    msg.setDetailedText(tb)
    msg.exec()


def main() -> int:
    # Устанавливаем глобальный обработчик исключений
    sys.excepthook = excepthook
    
    warnings.filterwarnings("ignore")
    app = QApplication(sys.argv)
    
    try:
        predictor = CarPricePredictor()
        window = MainWindow(predictor)
        window.show()
        return app.exec()
    except Exception as e:
        excepthook(type(e), e, e.__traceback__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())