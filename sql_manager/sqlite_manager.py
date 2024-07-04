import datetime
import json
import pickle
import sqlite3
import threading
import zlib
from .cyber_safe import store_encrypted_data as encrypt, retrieve_encrypted_data as decrypt
from logger_utility.logger_config import logger

tables_structure = {
    'setting':
        '''
            name        TEXT UNIQUE,
            value       TEXT
        ''',
    'history':
        '''
            time_update INTEGER,
            app_id INTEGER,
            items TEXT
        ''',
}

class SqliteDatabaseManager:
    def __init__(self):
        self.db_name = 'data.db'
        self.db_connection = sqlite3.connect(self.db_name, check_same_thread=False)
        self.__db_lock = threading.Lock()
        self._secret_key = None
        self.__create_all_tables()

    def encrypt_data(self, data: any) -> bytes | None:
        """
        Шифрует и сжимает предоставленные данные.

        Этот метод сериализует и сжимает данные с использованием zlib, затем шифрует их,
        если установлен секретный ключ. Возвращает зашифрованные данные в байтовом формате.
        В случае ошибки записывает информацию об ошибке в лог и возвращает None.

        Args:
            data (any): Данные для шифрования и сжатия.

        Returns:
            bytes | None: Зашифрованные данные в байтовом формате или None в случае ошибки.
        """
        try:
            # Сериализация и сжатие данных
            serialized_data = zlib.compress(pickle.dumps(data))
            # Шифрование данных, если установлен секретный ключ
            if isinstance(self._secret_key, str | int | float):
                serialized_data = encrypt(serialized_data, str(self._secret_key))
            # Возврат зашифрованных данных
            return serialized_data
        except Exception as error:
            # Логирование ошибки при шифровании
            logger.exception(f"Ошибка при шифровании данных: {type(error).__name__}")
            return None

    def decrypt_data(self, data: bytes) -> any:
        """
        Дешифрует и разжимает предоставленные данные.

        Этот метод сначала пытается дешифровать данные с использованием секретного ключа,
        затем разжимает их. Возвращает десериализованные данные в случае успеха.
        В случае ошибки записывает информацию об ошибке в лог и возвращает None.

        Args:
            data (bytes): Данные для дешифрования и разжатия.

        Returns:
            Десериализованные данные после дешифрования и разжатия или None в случае ошибки.
        """
        try:
            # Подготовка данных для дешифрования
            compressed_data = data
            # Дешифрование данных, если установлен секретный ключ
            if isinstance(self._secret_key, str | int | float):
                compressed_data = decrypt(str(self._secret_key), compressed_data)
            # Разжатие и десериализация данных
            return pickle.loads(zlib.decompress(compressed_data))
        except Exception as error:
            # Логирование ошибки при дешифровании
            logger.exception(f"Ошибка при дешифровании данных: {type(error).__name__}")
            return None

    def __connect(self):
        return sqlite3.connect(self.db_name, check_same_thread=False)

    def __create_table(self, table_name: str, table_params: str) -> None:
        try:
            with self.__connect() as conn:
                cursor = conn.cursor()
                cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({table_params});")
        except sqlite3.OperationalError:
            pass

    def __create_all_tables(self) -> None:
        for table_name in tables_structure:
            self.__create_table(table_name, tables_structure[table_name])

    def save_history(self, time_update: datetime.datetime, items: dict, app_id: int) -> bool:
        try:
            # Сериализуем словарь в JSON
            items_json = json.dumps(items)
            # Конвертируем datetime в UNIX timestamp
            timestamp = int(time_update.timestamp())

            # Устанавливаем блокировку и открываем соединение
            with self.__db_lock, self.__connect() as conn:
                # Создаем курсор
                cursor = conn.cursor()
                try:
                    # Выполняем SQL-запрос
                    cursor.execute(
                        "INSERT INTO history (time_update, app_id, items) VALUES (?, ?, ?)",
                        (timestamp, app_id, items_json)
                    )
                    # Фиксируем транзакцию
                    conn.commit()
                finally:
                    # Всегда закрываем курсор после использования
                    cursor.close()
                return True
        except Exception as e:
            logger.exception(f"Ошибка при сохранении истории: {e}")
            return False

    def get_recent_history(self) -> list:
        try:
            # Устанавливаем блокировку и открываем соединение
            with self.__db_lock, self.__connect() as conn:
                # Создаем курсор
                cursor = conn.cursor()
                try:
                    # Выполняем SQL-запрос
                    cursor.execute(
                        "SELECT time_update, app_id, items FROM history ORDER BY time_update DESC"
                    )
                    # Получаем результаты
                    rows = cursor.fetchall()
                    # Преобразуем результаты в список словарей
                    history = [
                        {
                            'time_update': datetime.datetime.fromtimestamp(row[0]),
                            'app_id': row[1],
                            'items': json.loads(row[2])
                        } for row in rows
                    ]
                finally:
                    # Всегда закрываем курсор после использования
                    cursor.close()
                return history
        except Exception as e:
            logger.exception(f"Ошибка при получении истории: {e}")
            return []


    def save_setting(self, name: str, value: str | list | dict) -> None:
        """
        Сохраняет или обновляет значение настройки в базе данных.

        Этот метод позволяет сохранять настройки различных типов (строка, список или словарь)
        в базе данных. Если настройка данного типа уже существует, она будет обновлена.

        Args:
            name (str): Название настройки.
            value (str | list | dict): Значение настройки, которое может быть типа строка, список или словарь.

        Returns:
            None

        Raises:
            Ошибки, связанные с базой данных или сериализацией данных, могут быть перехвачены и
            обработаны внутри метода. Ошибки будут выводиться на экран.
        """

        try:
            with self.__db_lock, self.__connect() as conn:
                # Если значение настройки является списком или словарем, преобразуем его в JSON-строку
                if isinstance(value, (list, dict)):
                    value = json.dumps(value)
                    
                # Создание курсора для работы с базой данных
                cursor = conn.cursor()
                # Формирование и выполнение SQL-запроса для вставки или обновления данных настройки
                cursor.execute("INSERT OR REPLACE INTO setting (name, value) VALUES (?, ?)", (name, value))
                # Фиксация изменений в базе данных
                self.db_connection.commit()

        except Exception:
            # Вывод информации об ошибке, если она возникла
            logger.exception(f"Ошибка при обновлении настройки '{name}'")

    def get_setting(self, name: str) -> str | list | None:
        """
        Получает значение настройки из базы данных по её имени.

        Пытается получить значение настройки из базы данных. Если это значение в формате JSON (список или словарь),
        функция пытается его десериализовать и вернуть в виде объекта Python. Если десериализация не удаётся,
        возвращает значение настройки как есть. Если такой настройки нет в базе данных, возвращает None.

        Args:
            name (str): Название настройки, значение которой нужно получить.

        Returns:
            str | list | None: Значение настройки (строка или список) или None, если такой настройки нет.

        Raises:
            Ошибки, связанные с базой данных или десериализацией данных, могут быть перехвачены и
            обработаны внутри метода. Ошибки будут выводиться на экран.
        """

        try:
            with self.__db_lock, self.__connect() as conn:
                # Создание курсора для работы с базой данных
                cursor = conn.cursor()
                # Выполнение SQL-запроса для получения значения настройки по имени
                cursor.execute("SELECT value FROM setting WHERE name=?", (name,))
                # Получение результата запроса
                row = cursor.fetchone()
                if row:
                    # Попытка десериализовать значение настройки
                    value = row[0]
                    try:
                        return json.loads(value)
                    except:
                        pass
                    return value
                # Если такой настройки нет в базе данных, возвращаем None
                return None

        except Exception:
            # Вывод информации об ошибке, если она возникла
            logger.exception(f"Ошибка при получении настройки '{name}'")

sqlite_manager = SqliteDatabaseManager()
