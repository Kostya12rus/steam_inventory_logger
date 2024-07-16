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

        self.button_inventory = ft.FilledButton('Inventory', expand=True, on_click=self.on_go_inventory)
        self.button_market = ft.FilledButton('Market', expand=True, on_click=self.on_go_market)
        self.button_inventory_stack = ft.FilledButton('InventoryStack', expand=True, on_click=self.on_go_inventory_stack)
        self.button_craft_manager = ft.FilledButton('CraftManager', expand=True, on_click=self.on_go_craft_manager)

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

        self.setting_widget.controls = [self.button_inventory,
                                        self.button_inventory_stack,
                                        self.button_market,
                                        self.button_craft_manager,
                                        self.drop_down_game]
        self.controls = [self.setting_widget, self.body_widget]

    def __on_change_game(self, *args):
        common.set_appid(self.drop_down_game.value)
        if self.inventory_page.is_run:
            self.inventory_page.items_history_column.controls.clear()
            self.inventory_page.items_price_column.controls.clear()
            self.inventory_page.update()
            common.next_updated_inventory = datetime.datetime.min
            self.inventory_page.update_history()
            self.inventory_page.update_datagram()
            self.inventory_page.update()
        if self.market_page.is_run:
            self.market_page.items_column.rows.clear()
            self.market_page.update()
            common.next_updated_market_list = datetime.datetime.min
            self.market_page.update_widget()
            self.market_page.update()
        self.inventory_stack_page.update_clear()
        self.craft_manager_page.update_clear()


    def on_go_craft_manager(self, *args):
        self.body_widget.controls = [self.craft_manager_page]
        self.body_widget.update()

    def on_go_inventory_stack(self, *args):
        self.body_widget.controls = [self.inventory_stack_page]
        self.body_widget.update()

    def on_go_inventory(self, *args):
        self.body_widget.controls = [self.inventory_page]
        self.body_widget.update()

    def on_go_market(self, *args):
        self.body_widget.controls = [self.market_page]
        self.body_widget.update()
