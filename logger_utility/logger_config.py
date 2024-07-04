import sys
from loguru import logger
from pathlib import Path

# Пример использования
# from logger_utility.logger_config import logger
# logger.info('HELLO WORLD')
# logger.exception('THIS IS ERROR MESSAGE')

# Удаление всех существующих обработчиков, чтобы избежать дублирования логов
logger.remove()

# Директория для хранения логов
logs_folder = Path('logs')
logs_folder.mkdir(parents=True, exist_ok=True)

# Формат вывода логов
format_log = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <b>{message}</b>"

# Добавление файла для записи логов уровня "INFO".
logger.add(logs_folder / 'logs.log', format=format_log, level="INFO", rotation="1 MB", filter=lambda record: record["level"].name == "INFO")
# Добавление файла для записи логов уровня "ERROR" с дополнительной информацией для диагностики.
logger.add(logs_folder / 'exceptions.log', level="ERROR", backtrace=True, diagnose=True, enqueue=True, rotation="1 MB", filter=lambda record: record["level"].name == "ERROR")

# Проверка на наличие sys.stdout перед добавлением обработчика вывода в консоль
if sys.stdout:
    # Включение вывода в консоль без вывода микросекунд и деталей местоположения в коде
    logger.add(sys.stdout, format=format_log, level="INFO", filter=lambda record: record["level"].name == "INFO")
    logger.info(f'Логи будут хранится в папке: {logs_folder.absolute()}')