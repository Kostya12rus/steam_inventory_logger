@echo off
REM Определяем путь к проекту относительно текущего местоположения батника
set PROJECT_DIR=%~dp0

REM Обновляем pip
python.exe -m pip install --upgrade pip

REM Переходим в директорию проекта
cd /d "%PROJECT_DIR%"

REM Устанавливаем зависимости
python.exe -m pip install -r requirements.txt

REM Запускаем основной скрипт
python.exe main_flet.py

REM Ожидаем нажатия клавиши для завершения
pause
