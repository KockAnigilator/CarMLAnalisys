from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any, Callable, Iterable

import matplotlib.pyplot as plt
import seaborn as sns
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QPixmap


class MatplotlibStyler:
    """Utility for applying a consistent Matplotlib/Seaborn style."""

    PALETTE = "husl"
    STYLE = "seaborn-v0_8"

    @staticmethod
    def apply() -> None:
        """Apply the default plotting style used across the application."""
        sns.set_theme(style=MatplotlibStyler.STYLE, palette=MatplotlibStyler.PALETTE)
        plt.rcParams["figure.autolayout"] = True


class FigureConverter:
    """Convert Matplotlib figures into Qt-friendly pixmaps."""

    @staticmethod
    def to_pixmap(figure: plt.Figure) -> QPixmap:
        buffer = BytesIO()
        figure.savefig(buffer, format="png")
        buffer.seek(0)
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.read(), "PNG")
        plt.close(figure)
        return pixmap


def humanize_shape(shape: Iterable[int]) -> str:
    """Return a friendly (rows x cols) description."""
    try:
        rows, cols = shape
    except ValueError:
        rows, cols = shape[0], None
    if cols is None:
        return f"{rows} rows"
    return f"{rows} rows x {cols} columns"


class WorkerSignals(QObject):
    """Qt signals emitted by WorkerThread instances."""

    finished = Signal(object)
    error = Signal(Exception)
    progress = Signal(int)


class WorkerThread(QThread):
    """Generic background worker for long-running tasks."""

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            result = self._run_with_optional_progress()
            self.signals.finished.emit(result)
        except Exception as exc:  # pragma: no cover - surface to GUI
            self.signals.error.emit(exc)

    def _run_with_optional_progress(self) -> Any:
        try:
            return self.fn(
                *self.args, progress_callback=self.signals.progress.emit, **self.kwargs
            )
        except TypeError:
            return self.fn(*self.args, **self.kwargs)

