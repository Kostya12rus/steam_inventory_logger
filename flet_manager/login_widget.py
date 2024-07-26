import flet as ft
from sql_manager.config import setting


class LoginWidget(ft.Column):
    def __init__(self):
        super().__init__()
        self.__is_run = False
        self.isolated = True
        self.expand = True
        self.alignment = ft.MainAxisAlignment.CENTER

        self._title = ft.Text(
            'Войдите в аккаунт Steam',
            size=24,
            color=ft.colors.BLUE,
            weight=ft.FontWeight.BOLD
        )
        self.login = ft.TextField(label='Steam Login', dense=True, content_padding=10, text_align=ft.TextAlign.CENTER)
        self.login.value = setting.login
        self.password = ft.TextField(label='Steam Password', dense=True, content_padding=10, password=True, text_align=ft.TextAlign.CENTER)
        self.password.value = setting.password
        self.guard_2fa = ft.TextField(label='Guard Code', dense=True, content_padding=10, password=True, text_align=ft.TextAlign.CENTER)

        self.enter_button = ft.FilledButton(
            'Login Steam Account',
            style=ft.ButtonStyle(
                bgcolor=ft.colors.GREEN,
                color=ft.colors.WHITE,
            ),
            expand=True
        )
        self.warning_text = ft.Text('', color=ft.colors.RED)

        self.controls = [
            ft.Row([self._title], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(20),
            self.login,
            self.password,
            self.guard_2fa,
            ft.Row([self.enter_button], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([self.warning_text], alignment=ft.MainAxisAlignment.CENTER),
        ]
