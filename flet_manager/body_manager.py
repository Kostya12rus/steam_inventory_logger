from . import InventoryWidget
from .market_manager import MarketWidget
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

        self.body_widget = ft.Column(expand=True)
        self.setting_widget = ft.Row(alignment=ft.MainAxisAlignment.SPACE_AROUND)

        self.button_inventory = ft.FilledButton('Inventory', expand=True, on_click=self.on_go_inventory)
        self.button_market = ft.FilledButton('Market', expand=True, on_click=self.on_go_market)

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

        self.setting_widget.controls = [self.button_inventory, self.button_market, self.drop_down_game]
        self.controls = [self.setting_widget, self.body_widget]

    def __on_change_game(self, *args):
        common.set_appid(self.drop_down_game.value)

    def on_go_inventory(self, *args):
        self.body_widget.controls = [self.inventory_page]
        self.body_widget.update()

    def on_go_market(self, *args):
        self.body_widget.controls = [self.market_page]
        self.body_widget.update()
