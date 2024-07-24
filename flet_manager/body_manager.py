import datetime

from . import InventoryWidget
from .market_manager import MarketWidget
from .inventory_stack_manager import InventoryStackWidget
from .craft_manager import CraftManagerWidget
from .shared_data import common
import flet as ft

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
            value=common.get_current_appid_name()
        )

        self.setting_widget.controls = [
            self.button_inventory,
            self.button_inventory_stack,
            self.button_market,
            self.button_craft_manager,
            self.drop_down_game
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
