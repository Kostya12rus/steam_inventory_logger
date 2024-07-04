import os
import pathlib
import shutil
import subprocess
import time

# Установка текущей рабочей директории
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Инициализация путей и параметров
current_directory = pathlib.Path()
use_additional_cleanup = True
main_file_to_compile = 'main_flet.py'

compiled_name = 'SteamInventoryManager'
output_directory = current_directory / 'output'
icon_path = current_directory / 'assets' / 'icon.png'
product_name = 'Steam Inventory Manager'
file_description = ' '
product_version = '1.0.0'
file_version = '0.0.1.0'
company_name = 'Kostya12rus Inc.'
copyright_notice = f'Copyright 2023, {company_name}'
bundle_identifier = f'com.kostya12rus.cs2farmvertigo'

# Путь к каталогу 'userdata' (необходим для хранения настроек Steam и CS:GO).
# Используйте эту опцию, если каталог 'userdata' расположен в отдельной директории, не связанной с проектом.
# example: cs_userdata_main_path = pathlib.Path(r'C:\Users\Kostya\PycharmProjects\cs2_farm_vertigo\userdata')
cs_userdata_path = None

# Путь к файлу 'settings.db' (используется для хранения настроек программы).
# Используйте эту опцию, если файл 'settings.db' расположен в отдельной директории, не связанной с проектом.
# example: cs_userdata_main_path = pathlib.Path(r'C:\Users\Kostya\PycharmProjects\cs2_farm_vertigo\settings.db')
settings_db_path = None
# settings_db_path = pathlib.Path(r'E:\PycharmProjects\cs_go_farm_helper\dist\settings.db')

# Путь к каталогу 'logs' (необходим для хранения Логов приложения).
# Используйте эту опцию, если каталог 'logs' расположен в отдельной директории, не связанной с проектом.
# example: logs_path = pathlib.Path(r'C:\Users\Kostya\PycharmProjects\cs2_farm_vertigo\logs')
logs_path = None


# Удаление папки Output
if output_directory.is_dir():
    print(f"Deleting directory: {output_directory.as_posix()}")
    shutil.rmtree(output_directory)

# Запуск компиляции через flet pack с заданными параметрами
subprocess.run(
    [
        "flet", "pack",
        "-v", "-vv",
        "--name", compiled_name,
        # "--icon", icon_path,
        "--distpath", output_directory,
        "--product-name", product_name,
        "--file-description", file_description,
        "--product-version", product_version,
        "--file-version", file_version,
        "--company-name", company_name,
        "--copyright", copyright_notice,
        "--bundle-id", bundle_identifier,
        main_file_to_compile,
    ],
    encoding="utf-8",
    shell=True
)

# Дополнительные операции по очистке, если необходимо
if use_additional_cleanup:
    # Ожидание завершения генерации
    time.sleep(5)

    # Удаление сгенерированных иконок
    icon_files = current_directory.glob("generated-*.ico")
    for file in icon_files:
        print(f"Deleting temp file: {file.as_posix()}")
        file.unlink(missing_ok=True)

    # Удаление spec-файлов
    specification_files = current_directory.glob("*.spec")
    for file in specification_files:
        print(f"Deleting file: {file.as_posix()}")
        file.unlink(missing_ok=True)

    # Удаление папки с промежуточными файлами
    build_directory = current_directory / 'build'
    if build_directory.is_dir():
        print(f"Deleting directory: {build_directory.as_posix()}")
        shutil.rmtree(build_directory, ignore_errors=True)

# Создание символических ссылок
os.system('chcp 65001')
local_logs = logs_path if logs_path else current_directory / 'logs'
if local_logs.is_dir():
    output_logs = output_directory / 'logs'
    os.system(f'mklink /J "{output_logs}" "{local_logs}"')

local_userdata = cs_userdata_path if cs_userdata_path else current_directory / 'userdata'
if local_userdata.is_dir():
    output_userdata = output_directory / 'userdata'
    os.system(f'mklink /J "{output_userdata}" "{local_userdata}"')

# local_userdata = current_directory / 'create_session'
# if local_userdata.is_dir():
#     output_userdata = output_directory / 'create_session'
#     os.system(f'mklink /J "{output_userdata}" "{local_userdata}"')

local_settings_db = settings_db_path if settings_db_path else current_directory / 'settings.db'
if local_settings_db.is_file():
    output_settings_db = output_directory / 'settings.db'
    os.system(f'mklink "{output_settings_db}" "{local_settings_db}"')

dev_start_bat = output_directory / 'dev_start.bat'
if not dev_start_bat.is_file():
    with open(dev_start_bat, 'w') as file:
        file.write(f'cd "%~dp0"\n{compiled_name}.exe --updated 1\n@pause')
        print(f'create dev start {dev_start_bat}')