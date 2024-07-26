import os
import time
import datetime
import subprocess
import threading

import flet as ft

from sql_manager.config import setting
from sql_manager import sqlite_manager, config
from logger_utility.logger_config import logger
from flet_manager.shared_data import UpdateManager
from steam_utility.manager_steam_session import SteamWebSession
from flet_manager import LoginWidget, common, InventoryWidget, BodyManager

class UpdateNotification:
    def __init__(self):
        self.update_manager = UpdateManager()
        self.first_start_button_sheet: ft.CupertinoBottomSheet = self.__create_first_start()
        self.new_update_button_sheet: ft.CupertinoBottomSheet = self.__create_new_update()

    def __first_start_callback(self, *args, status: bool, button_sheet: ft.CupertinoBottomSheet = None):
        control: ft.ControlEvent = args[0]
        if not control or not button_sheet: return
        page: ft.Page = control.page
        page.close(button_sheet)
        self.update_manager.change_accept_update(status)
        self.update_manager.change_installed_version(0.1)
        self.update_manager.last_check_version = datetime.datetime.now()
    def __create_first_start(self) -> ft.CupertinoBottomSheet:
        title_text = ft.Text(value="Настройка уведомлений об обновлениях")
        message_text = ft.Text(value="Похоже, вы запустили программу впервые. Хотите получать уведомления об обновлениях программы?")
        button_yes = ft.CupertinoActionSheetAction(content=ft.Text("Да"), is_default_action=True,
                                                   tooltip='Вы будете получать уведомления об обновлениях.')
        button_no = ft.CupertinoActionSheetAction(content=ft.Text("Нет"), is_destructive_action=True,
                                                  tooltip='Вы не будете получать уведомления об обновлениях. Обновления будут выполняться только вручную.')
        action_sheet = ft.CupertinoActionSheet(
            title=ft.Row([title_text], alignment=ft.MainAxisAlignment.CENTER),
            message=ft.Row([message_text], alignment=ft.MainAxisAlignment.CENTER),
            actions=[button_yes, button_no]
        )
        button_sheet = ft.CupertinoBottomSheet(action_sheet, modal=True)
        button_yes.on_click = lambda e: self.__first_start_callback(e, status=True, button_sheet=button_sheet)
        button_no.on_click = lambda e: self.__first_start_callback(e, status=False, button_sheet=button_sheet)
        return button_sheet

    def __ignore_update(self, *args, button_sheet: ft.CupertinoBottomSheet = None):
        control: ft.ControlEvent = args[0]
        if not control or not button_sheet: return
        page: ft.Page = control.page
        page.close(button_sheet)
        self.update_manager.ignore_update = True
    def __start_download(self, *args, button_sheet: ft.CupertinoBottomSheet = None):
        control: ft.ControlEvent = args[0]
        if not control or not button_sheet: return
        page: ft.Page = control.page
        page.close(button_sheet)
        status_update = self.update_manager.download_and_extract_github_zip()
        text_widget = ft.Text(f" ")
        snack_bar_widget = ft.SnackBar(text_widget)
        if status_update:
            text_widget.value = f"Обновление успешно скачано, перезапустите программу или я сделаю это сам"
        else:
            text_widget.value = f"Обновление не удалось установить, попробуйте позже или установить вручную"
        page.open(snack_bar_widget)
        time.sleep(3)
        page.window.destroy()
        page.update()
        subprocess.Popen(['start.bat'])
        os.abort()

    def __close_button_sheet(self, *args, button_sheet: ft.CupertinoBottomSheet = None):
        control: ft.ControlEvent = args[0]
        if not control or not button_sheet: return
        page: ft.Page = control.page
        page.close(button_sheet)
    def __create_new_update(self) -> ft.CupertinoBottomSheet:
        title_text = ft.Text(value="Появилось новое обновление программы.")
        message_text = ft.Text(value="Ваша версия программы устарела. Хотите обновить программу?")
        button_yes = ft.CupertinoActionSheetAction(content=ft.Text("Обновить прямо сейчас"), is_default_action=True,
                                                   tooltip='Скачать и установить последнюю версию программы.')
        button_no = ft.CupertinoActionSheetAction(content=ft.Text("Игнорировать"), is_destructive_action=True,
                                                  tooltip='Вас больше не будут беспокоить до следующего запуска программы.')
        button_close = ft.CupertinoActionSheetAction(content=ft.Text("Закрыть"), is_destructive_action=True,
                                                     tooltip='Закрыть уведомление об обновлении.')
        action_sheet = ft.CupertinoActionSheet(
            title=ft.Row([title_text], alignment=ft.MainAxisAlignment.CENTER),
            message=ft.Row([message_text], alignment=ft.MainAxisAlignment.CENTER),
            actions=[button_yes, button_no, button_close]
        )
        button_sheet = ft.CupertinoBottomSheet(action_sheet, modal=True)
        button_yes.on_click = lambda e: self.__start_download(e, button_sheet=button_sheet)
        button_no.on_click = lambda e: self.__ignore_update(e, button_sheet=button_sheet)
        button_close.on_click = lambda e: self.__close_button_sheet(e, button_sheet=button_sheet)
        return button_sheet



class MainPage:
    def __init__(self):
        self.__first_start = True
        self.page: ft.Page = None
        self.login_page = LoginWidget()
        self.inventory_page = InventoryWidget()
        self.body_page = BodyManager()
        self.update_notification = UpdateNotification()

    def create_login_page(self, *args):
        self.page.clean()
        self.page.add(self.login_page)
        self.login_page.login.value = str(setting.login)
        self.login_page.password.value = str(setting.password)
        self.login_page.enter_button.on_click = self.on_login

    def create_inventory(self, *args):
        self.page.clean()
        self.page.add(self.body_page)

    def on_login(self, *args):
        saved_session = setting.session
        if saved_session:
            try:
                session: SteamWebSession = sqlite_manager.decrypt_data(saved_session)
                if session.is_session_alive():
                    common.session = session
                    logger.info('Ваша предыдущая сессия все еще активна. Продолжаем с ней.')
                    self.login_page.warning_text.value = 'Ваша предыдущая сессия все еще активна. Продолжаем с ней.'
                    self.create_inventory()
                    self.__first_start = False
                    return
            except:
                pass
        if self.__first_start:
            self.__first_start = False
            return

        login = str(self.login_page.login.value)
        password = str(self.login_page.password.value)
        guard_code = str(self.login_page.guard_2fa.value).upper()
        if login and password and guard_code:
            session = SteamWebSession(login=login, password=password)
            status = session.login_steam(guard_code)
            if not status:
                logger.info('Вход в аккаунт Steam не удался. Пожалуйста, попробуйте снова позже.')
                self.login_page.warning_text.value = 'Вход в аккаунт Steam не удался. Пожалуйста, попробуйте снова позже.'
            else:
                common.session = session
                setting.session = sqlite_manager.encrypt_data(session)
                setting.login = login
                setting.password = password
                logger.info('Вы успешно вошли в аккаунт Steam. Загрузка данных началась, ожидайте, пожалуйста.')
                self.login_page.warning_text.value = 'Вы успешно вошли в аккаунт Steam. Загрузка данных началась, ожидайте, пожалуйста.'
                self.create_inventory()
                return
        else:
            logger.info('Не все необходимые данные для входа указаны. Пожалуйста, проверьте введённые данные и попробуйте снова.')
            self.login_page.warning_text.value = 'Не все необходимые данные для входа указаны. Пожалуйста, проверьте введённые данные и попробуйте снова.'

    def build(self, page: ft.Page):
        self.page: ft.Page = page
        self.page.title = 'Inventory Logger'
        self.page.theme_mode = ft.ThemeMode.DARK if config.is_dark_mode else ft.ThemeMode.LIGHT
        self.page.window.width = 1500
        self.create_login_page()
        self.on_login()
        threading.Thread(target=self.__loop_update_checker).start()


    def __update_checker(self):
        if self.update_notification.update_manager.ignore_update: return
        if not self.update_notification.update_manager.accept_update: return

        if self.update_notification.update_manager.is_first_run():
            self.page.open(self.update_notification.first_start_button_sheet)
            return
        status_load_file = self.update_notification.update_manager.load_file_version()
        if status_load_file:
            installed_version = self.update_notification.update_manager.installed_version
            file_version = self.update_notification.update_manager.file_version
            if installed_version != file_version and isinstance(file_version, float):
                self.update_notification.update_manager.change_installed_version(self.update_notification.update_manager.file_version)
        status_load_server = self.update_notification.update_manager.load_server_version()
        if not status_load_server: return
        installed_version = self.update_notification.update_manager.installed_version
        server_version = self.update_notification.update_manager.server_version
        if installed_version != server_version and isinstance(server_version, float):
            self.page.open(self.update_notification.new_update_button_sheet)
    def __loop_update_checker(self):
        while True:
            try:
                if self.update_notification.update_manager.last_check_version <= datetime.datetime.now():
                    self.update_notification.update_manager.last_check_version = datetime.datetime.now() + datetime.timedelta(hours=1)
                    self.__update_checker()
            except:
                logger.exception('Проблема при обновлении данных.')
            time.sleep(60)

main_page = MainPage()
ft.app(target=main_page.build)
os.abort()
