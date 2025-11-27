from __future__ import annotations

from io import BytesIO
from typing import Any, Callable, Iterable, Optional, Union

import matplotlib.pyplot as plt
import seaborn as sns

try:
    from PySide6.QtCore import QObject, QThread, Signal
    from PySide6.QtGui import QPixmap
except Exception as exc:
    QObject = None
    QThread = None
    Signal = None
    QPixmap = None
    _QT_IMPORT_ERROR = exc
else:
    _QT_IMPORT_ERROR = None


class MatplotlibStyler:
    """Утилита для применения единого стиля Matplotlib/Seaborn."""

    PALETTE = "husl"
    STYLE = "seaborn-v0_8"

    @staticmethod
    def apply() -> None:
        """Применяет стиль построений, принятый во всём приложении."""
        try:
            sns.set_theme(
                style=MatplotlibStyler.STYLE, palette=MatplotlibStyler.PALETTE
            )
        except ValueError:
            sns.set_theme(palette=MatplotlibStyler.PALETTE)
            plt.style.use(MatplotlibStyler.STYLE)
        plt.rcParams["figure.autolayout"] = True


class FigureConverter:
    """Преобразует фигуры Matplotlib в пригодные для Qt пиксмапы."""

    @staticmethod
    def to_pixmap(figure: plt.Figure) -> QPixmap:  # type: ignore
        if QPixmap is None:
            raise ImportError(
                "PySide6 недоступен, поэтому нельзя создать QPixmap."
            ) from _QT_IMPORT_ERROR
        buffer = BytesIO()
        figure.savefig(buffer, format="png", dpi=100, bbox_inches='tight')
        buffer.seek(0)
        pixmap = QPixmap()
        pixmap.loadFromData(buffer.getvalue(), "PNG")
        plt.close(figure)
        return pixmap


def humanize_shape(shape: Iterable[int]) -> str:
    """Возвращает человекочитаемое описание формата (строки x столбцы)."""
    try:
        rows, cols = shape
    except ValueError:
        rows, cols = shape[0], None
    if cols is None:
        return f"{rows} rows"
    return f"{rows} rows x {cols} columns"


if QObject is not None and QThread is not None and Signal is not None:

    class WorkerSignals(QObject):
        """Qt-сигналы, которые испускают экземпляры WorkerThread."""

        finished = Signal(object)
        error = Signal(Exception)
        progress = Signal(int)


    class WorkerThread(QThread):
        """Универсальный фоновый поток для длительных задач."""

        def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
            super().__init__()
            self.fn = fn
            self.args = args
            self.kwargs = kwargs
            self.signals = WorkerSignals()
            self._is_running = False

        def run(self) -> None:
            self._is_running = True
            try:
                result = self._run_with_optional_progress()
                self.signals.finished.emit(result)
            except Exception as exc:
                self.signals.error.emit(exc)
            finally:
                self._is_running = False

        def _run_with_optional_progress(self) -> Any:
            try:
                # Проверяем, принимает ли функция progress_callback
                import inspect
                sig = inspect.signature(self.fn)
                if 'progress_callback' in sig.parameters:
                    return self.fn(
                        *self.args,
                        progress_callback=self.signals.progress.emit,
                        **self.kwargs,
                    )
                else:
                    return self.fn(*self.args, **self.kwargs)
            except Exception as e:
                raise e

        def stop(self) -> None:
            """Безопасная остановка потока."""
            if self.isRunning():
                # Сначала пробуем дождаться естественного завершения
                if not self.wait(100):
                    # Если поток не завершился, принудительно завершаем
                    self.terminate()
                    self.wait()  # Ждем завершения без таймаута
                
        def __del__(self) -> None:
            """Деструктор - гарантируем завершение потока."""
            if self.isRunning():
                self.wait(100)
                if self.isRunning():
                    self.terminate()
                    self.wait()

else:

    class WorkerSignals:
        """Заглушка WorkerSignals на случай отсутствия PySide6."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise ImportError(
                "PySide6 недоступен, сигналы и фоновые потоки отключены."
            ) from _QT_IMPORT_ERROR


    class WorkerThread:
        """Заглушка WorkerThread на случай отсутствия PySide6."""

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise ImportError(
                "PySide6 недоступен, фоновые потоки GUI недоступны."
            ) from _QT_IMPORT_ERROR