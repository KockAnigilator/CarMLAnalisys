@echo off
echo ================================================
echo  Car ML Analysis - Система анализа цен автомобилей
echo ================================================
echo.

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден! Установите Python 3.8+ и добавьте его в PATH.
    pause
    exit /b 1
)

echo [OK] Python найден
echo.

REM Проверяем зависимости
echo Проверка зависимостей...
python -c "import pandas, numpy, sklearn, PySide6" >nul 2>&1
if errorlevel 1 (
    echo [ВНИМАНИЕ] Не все зависимости установлены.
    echo Устанавливаю зависимости...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось установить зависимости.
        pause
        exit /b 1
    )
)

echo [OK] Все зависимости установлены
echo.
echo Запускаю приложение...
echo.

REM Запускаем приложение
python main.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Приложение завершилось с ошибкой.
    pause
    exit /b 1
)

exit /b 0
