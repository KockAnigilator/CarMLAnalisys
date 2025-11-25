from __future__ import annotations

import sys
import warnings

from PySide6.QtWidgets import QApplication

from core import CarPricePredictor
from gui import MainWindow


def main() -> int:
    warnings.filterwarnings("ignore")
    app = QApplication(sys.argv)
    predictor = CarPricePredictor()
    window = MainWindow(predictor)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

