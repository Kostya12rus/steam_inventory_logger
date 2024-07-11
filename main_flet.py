import os
import flet as ft

from flet_manager import LoginWidget, common, InventoryWidget, BodyManager
from sql_manager import sqlite_manager
from sql_manager.config import setting
from steam_utility.manager_steam_session import SteamWebSession
from logger_utility.logger_config import logger


class MainPage:
    def __init__(self):
        self.page: ft.Page = None
        self.login_page = LoginWidget()
        self.inventory_page = InventoryWidget()
        self.body_page = BodyManager()

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
                    return
            except:
                pass

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

    def __on_window_event(self, e):
        if e.data == "close":
            try:
                common.update_current_inventory()
            except:
                logger.exception('ERROR update_current_inventory()')
            try:
                self.page.window.destroy()
            except:
                logger.exception('ERROR update_current_inventory()')

    def build(self, page: ft.Page):
        self.page: ft.Page = page
        self.page.title = 'Привет'
        self.page.window.width = 1500
        self.page.window.prevent_close = True
        self.page.window.on_window_event = self.__on_window_event
        self.page.window.on_event = self.__on_window_event
        self.create_login_page()
        self.on_login()


main_page = MainPage()
ft.app(target=main_page.build)

os.abort()
