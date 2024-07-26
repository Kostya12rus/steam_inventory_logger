import flet as ft

from . import InventoryWidget
from sql_manager import config
from .shared_data import common
from .market_manager import MarketWidget
from .craft_manager import CraftManagerWidget
from .inventory_stack_manager import InventoryStackWidget

class ThemeToggleButton(ft.IconButton):
    def __init__(self):
        super().__init__()
        self.icon = ft.icons.LIGHT_MODE if config.is_dark_mode else ft.icons.DARK_MODE
        self.tooltip = "Сменить тему"
        self.on_click = self.toggle_theme
        self.height = 30
        self.style = ft.ButtonStyle(padding=ft.padding.all(0))

    def toggle_theme(self, *args):
        self.page.theme_mode = ft.ThemeMode.DARK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        is_dark_mode = self.page.theme_mode == ft.ThemeMode.DARK
        self.icon = ft.icons.LIGHT_MODE if is_dark_mode else ft.icons.DARK_MODE
        config.is_dark_mode = is_dark_mode
        self.page.update()


class BodyManager(ft.Column):
    def __init__(self):
        super().__init__()
        self.__is_run = False
        self.isolated = True
        self.expand = True
        self.alignment = ft.MainAxisAlignment.CENTER

        self.inventory_page = InventoryWidget()
        self.market_page = MarketWidget()
        self.inventory_stack_page = InventoryStackWidget()
        self.craft_manager_page = CraftManagerWidget()

        self.body_widget = ft.Column(expand=True)
        self.setting_widget = ft.Row(alignment=ft.MainAxisAlignment.SPACE_AROUND)
        self.body_widget.controls = [self.inventory_page]

        self.button_inventory = ft.FilledButton(
            'Inventory', expand=True, on_click=lambda e: self.set_body_widget(self.inventory_page),
            height=30, style=ft.ButtonStyle(padding=ft.padding.all(0))
        )
        self.button_market = ft.FilledButton(
            'Market', expand=True, on_click=lambda e: self.set_body_widget(self.market_page),
            height=30, style=ft.ButtonStyle(padding=ft.padding.all(0))
        )
        self.button_inventory_stack = ft.FilledButton(
            'InventoryStack', expand=True, on_click=lambda e: self.set_body_widget(self.inventory_stack_page),
            height=30, style=ft.ButtonStyle(padding=ft.padding.all(0))
        )
        self.button_craft_manager = ft.FilledButton(
            'CraftManager', expand=True, on_click=lambda e: self.set_body_widget(self.craft_manager_page),
            height=30, style=ft.ButtonStyle(padding=ft.padding.all(0))
        )

        self.drop_down_game = ft.Dropdown(
            on_change=self.__on_change_game,
            options=[ft.dropdown.Option(game_name) for game_name, app_id in common.games.items()],
            height=30,
            width=300,
            text_size=14,
            dense=True,
            label='Игра',
            content_padding=10,
            value=common.get_current_appid_name(),
            padding=ft.padding.all(0)
        )

        self.change_theme = ThemeToggleButton()

        self.setting_widget.controls = [
            self.button_inventory,
            self.button_inventory_stack,
            self.button_market,
            self.button_craft_manager,
            self.drop_down_game,
            self.change_theme,
        ]
        self.controls = [self.setting_widget, self.body_widget]

    def __on_change_game(self, *args):
        common.set_appid(self.drop_down_game.value)
        self.inventory_page.update_clear()
        self.market_page.update_clear()
        self.inventory_stack_page.update_clear()
        self.craft_manager_page.update_clear()

    def set_body_widget(self, widget):
        self.body_widget.controls = [widget]
        self.body_widget.update()
