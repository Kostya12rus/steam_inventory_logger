import threading
import time

from flet_manager import common
import flet as ft

from sql_manager.config import setting
from logger_utility.logger_config import logger

class Description:
    def __init__(self, description_dict: dict = None):
        if not description_dict: description_dict = {}
        self.type = description_dict.get('type')
        self.value = description_dict.get('value')
class AssetDescription:
    def __init__(self, asset_description_dict: dict = None):
        if not asset_description_dict: asset_description_dict = {}
        self.appid = asset_description_dict.get('appid')
        self.classid = asset_description_dict.get('classid')
        self.instanceid = asset_description_dict.get('instanceid')
        self.name = asset_description_dict.get('name')
        self.name_color = asset_description_dict.get('name_color', '')
        self.market_name = asset_description_dict.get('market_name')
        self.market_hash_name = asset_description_dict.get('market_hash_name')

        self.tradable = bool(asset_description_dict.get('tradable', False))
        self.marketable = bool(asset_description_dict.get('marketable', False))
        self.commodity = bool(asset_description_dict.get('commodity', False))

        self.market_tradable_restriction = asset_description_dict.get('market_tradable_restriction', -1)
        self.market_marketable_restriction = asset_description_dict.get('market_marketable_restriction', -1)

        self.icon_url = asset_description_dict.get('icon_url')
        self.icon_url_large = asset_description_dict.get('icon_url_large')

        self.currency = asset_description_dict.get('currency')
        self.descriptions = [Description(d) for d in asset_description_dict.get('descriptions', [])]
        self.type = asset_description_dict.get('type', "")
        self.background_color = asset_description_dict.get('background_color', "")
class Item:
    def __init__(self, item_dict: dict = None):
        if not item_dict: item_dict = {}
        self.name = item_dict.get('name', ' ')
        self.hash_name = item_dict.get('hash_name', '')

        self.sell_listings = item_dict.get('sell_listings', 0)
        self.sell_price = item_dict.get('sell_price', 0)
        self.sell_price_text = item_dict.get('sell_price_text', '')
        self.sale_price_text = item_dict.get('sale_price_text', '')

        self.asset_description = AssetDescription(item_dict.get('asset_description', {}))

        self.app_name = item_dict.get('app_name')
        self.app_icon = item_dict.get('app_icon')
    def __repr__(self):
        return f'<{self.__class__.__name__}> name: {self.name}, price: {self.sell_price_text}, listings: {self.sell_price}'
    def is_bug_item(self) -> bool:
        return self.hash_name != self.asset_description.market_hash_name
    def is_empty(self) -> bool:
        return self.hash_name == ''
    def icon_url(self) -> str:
       return f'https://community.akamai.steamstatic.com/economy/image/{self.asset_description.icon_url}/330x192?allow_animated=1'
    def market_url(self) -> str:
        return f'https://steamcommunity.com/market/listings/{self.asset_description.appid}/{self.asset_description.market_hash_name}'
    def market_hash_name(self) -> str:
        return self.asset_description.market_hash_name
    def color(self):
        return f'#{self.asset_description.name_color}' if self.asset_description.name_color else ''
    def is_current_game(self, app_id: int):
        return str(self.asset_description.appid) == str(app_id)

class CraftManagerWidget(ft.Column):
    def __init__(self):
        super().__init__()
        self.is_run = False
        self.isolated = True
        self.expand = True
        self.alignment = ft.MainAxisAlignment.START
        self.__items: list[Item] = []
        self.__crafts = {}
        self.__craft_widgets = {}
        self.__is_loading = False
        self.__app_id = 3017120
        self.spacing = 0

        self.title_widget_text = ft.Text(f'Система крафтов {common.get_current_appid_name(self.__app_id)}', size=24, color=ft.colors.BLUE, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, expand=True)
        body_title_widget_row = ft.Row(controls=[self.title_widget_text], alignment=ft.MainAxisAlignment.CENTER, run_spacing=0)


        self.widget_datacolumn_1 = ft.Text('Используются в крафте', size=18)
        self.widget_datacolumn_2 = ft.Text('Получаются в крафте', size=18)
        self.widget_datacolumn_3 = ft.Text('Прибыль', size=18)
        self.widget_datacolumn_4 = ft.Text('Управление', size=18)
        self.table_widget = ft.DataTable(columns=[], heading_row_height=30, expand=True) #TODO , visible=False,
        self.table_widget.columns = [ft.DataColumn(self.widget_datacolumn_1),
                                     ft.DataColumn(self.widget_datacolumn_2),
                                     ft.DataColumn(self.widget_datacolumn_3),
                                     ft.DataColumn(self.widget_datacolumn_4)]
        self.is_not_loaded_widget = ft.Row(alignment=ft.MainAxisAlignment.CENTER, visible=False,
                                           controls=[
                                               ft.FilledButton("Предметы не загружены", disabled=True, expand=True)
                                           ])
        self.dont_has_access_widget = ft.Row(alignment=ft.MainAxisAlignment.CENTER, visible=False,
                                             controls=[
                                                 ft.FilledButton("На данный момент работает только с игрой Egg Surprise", disabled=True, expand=True)
                                             ])
        self.body_widget_column = ft.Column(expand=True, spacing=0, scroll=ft.ScrollMode.AUTO, alignment=ft.MainAxisAlignment.CENTER)
        self.body_widget_column.controls = [self.is_not_loaded_widget, self.dont_has_access_widget, ft.Row(controls=[self.table_widget])]

        self.update_items_widget_button = ft.FilledButton('Обновить предметы и цены', expand=True, disabled=False, on_click=self.__load_items)
        self.create_widget_button = ft.FilledButton('Создать крафт', expand=False, on_click=self.create_craft) #TODO , disabled=True
        buttons_widget_row = ft.Row(spacing=0, controls=[
            self.update_items_widget_button,
            self.create_widget_button
        ])

        self.controls = [
            body_title_widget_row,
            ft.Divider(),
            self.body_widget_column,
            ft.Divider(),
            buttons_widget_row,
        ]

    def did_mount(self):
        self.is_run = True
        threading.Thread(target=self.__update).start()
        self.safe_update(self)
        self.__load_crafts()
    def will_unmount(self):
        self.is_run = False
    def safe_update(self, widget):
        try:
            if not widget: return
            if not self.is_run: return
            widget.update()
        except:
            logger.exception('Exception while updating widget')
    def update_clear(self):
        self.__app_id = 3017120
        self.title_widget_text.value = f'Система крафтов {common.get_current_appid_name(self.__app_id)}'
        self.safe_update(self.title_widget_text)
        if self.__app_id != common.app_id:
            self.dont_has_access_widget.visible = True
            self.safe_update(self.dont_has_access_widget)
            self.is_not_loaded_widget.visible = False
            self.safe_update(self.is_not_loaded_widget)
            self.table_widget.visible = False
            self.safe_update(self.table_widget)
            return
    def __update(self):
        while self.is_run:
            try:
                text_title = 'CraftManager: '

                if self.page.title != text_title:
                    self.page.title = text_title
                    self.safe_update(self.page)
            except:
                logger.exception('ERROR UPDATE InventoryStack')
            finally:
                time.sleep(1)

    def create_craft(self, *args, craft_index: str = None, craft_dict: dict = None):
        if not craft_dict:
            craft_dict = {}
        print(f'{craft_dict=}')
        if not craft_index:
            max_value = max([int(key) for key in self.__crafts.keys()], default=-1)
            craft_index = str(max_value+1)
        print(f'{craft_index=}')
        self.__crafts[craft_index] = {}
        print(f'{self.__craft_widgets=}')

        items_input_widget = ft.GridView(controls=[])
        self.__crafts[craft_index]['input_item'] = items_input_widget
        button_add_input_items = ft.FilledButton("Добавить предмет", expand=True, height=25)
        button_add_input_items.on_click = lambda e, _craft_index=craft_index: (
            self.__add_item(_craft_index, True))
        __item_input_column_widgets = ft.Column(controls=[ft.Row(controls=[items_input_widget]), ft.Row(controls=[button_add_input_items])],
                                                expand=True, alignment=ft.MainAxisAlignment.CENTER)

        items_output_widget = ft.GridView(controls=[], expand=True)
        self.__crafts[craft_index]['output_item'] = items_output_widget
        button_add_output_items = ft.FilledButton("Добавить предмет", expand=True, height=25)
        button_add_output_items.on_click = lambda e, _craft_index=craft_index: (
            self.__add_item(_craft_index, False))
        __item_output_column_widgets = ft.Column(controls=[ft.Row(controls=[items_output_widget]), ft.Row(controls=[button_add_output_items])],
                                                 expand=True, alignment=ft.MainAxisAlignment.CENTER)

        __item_total_widget = ft.Column(controls=[], expand=True, alignment=ft.MainAxisAlignment.CENTER)
        self.__crafts[craft_index]['total_item'] = __item_total_widget

        button_del_craft = ft.FilledButton("Удалить крафт", expand=True, height=25)
        __item_control_column_widgets = ft.Column(controls=[ft.Row(controls=[button_del_craft])],
                                                  expand=True, alignment=ft.MainAxisAlignment.CENTER)

        item_widget_datarow = ft.DataRow([ft.DataCell(__item_input_column_widgets),
                                          ft.DataCell(__item_output_column_widgets),
                                          ft.DataCell(__item_total_widget),
                                          ft.DataCell(__item_control_column_widgets)])

        self.table_widget.rows.append(item_widget_datarow)
        self.safe_update(self.table_widget)

    def __create_item(self, widget: ft.GridView, item_dict: dict):
        pass

    def __add_item(self, craft_index: str, is_input: bool):
        item_dict = 'input_item' if is_input else 'output_item'
        if item_dict not in self.__crafts[craft_index]:
            self.__crafts[craft_index][item_dict] = {}
        print(f'{craft_index=}')
        print(f'{self.__crafts[craft_index]=}')
        print(f'{is_input=}')

        def __select_item(item: Item):
            self.__crafts[craft_index][item_dict][item.market_hash_name()] = {
                'item_name': item.name,
                'market_hash_name': item.market_hash_name(),
                'count': 1,
                'percent': 100,
                'color': item.color(),
            }
            self.__save_crafts()
            print(f'{craft_index=}')
            print(f'{self.__crafts[craft_index]=}')
            print(f'{is_input=}')
            print(f'{item=}')


        def __create_list_items(control_column: ft.Column, find_string: str = ''):
            if not control_column:
                control_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
            ready_items = [_item for _item in self.__items if find_string.lower() in _item.name.lower()]
            control_column.controls = []
            for _item in ready_items:
                __row = ft.Row()
                __container = ft.Container(content=__row, width=300, height=25)
                __container.on_click = lambda e, __item=_item: __select_item(__item)
                __icon = ft.Image(src=_item.icon_url(), width=50, height=29)
                item_name_widget_text = ft.Text(value=_item.name, color=_item.color(), size=15, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True)
                __row.controls = [__icon, item_name_widget_text]
                control_column.controls.append(__container)
            try:
                control_column.update()
            except:
                pass

        item_content = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        __create_list_items(item_content, find_string='')
        text_find = ft.TextField(label='Name filter', dense=True, content_padding=10, text_align=ft.TextAlign.LEFT, expand=True, max_lines=1)
        text_find.on_change = lambda e: __create_list_items(item_content, find_string=text_find.value)
        column_widget = ft.Column(controls=[ft.Row(controls=[text_find]), item_content])

        dlg = ft.AlertDialog(title=ft.Text("Выберите предмет"))
        dlg.content = column_widget
        self.page.open(dlg)


    def __load_crafts(self):
        craft_system: dict = setting.craft_system
        self.__crafts = craft_system.get(str(self.__app_id), {})

    def __save_crafts(self):
        craft_system: dict = setting.craft_system
        craft_system[str(self.__app_id)] = self.__crafts
        setting.craft_system = craft_system

    def __load_items(self, *args):
        if self.__app_id != common.app_id:
            self.dont_has_access_widget.visible = True
            self.safe_update(self.dont_has_access_widget)
            self.is_not_loaded_widget.visible = False
            self.safe_update(self.is_not_loaded_widget)
            self.table_widget.visible = False
            self.safe_update(self.table_widget)
            return

        self.update_items_widget_button.disabled = True
        self.update_items_widget_button.text = 'Ожидайте я обновляю предметы и цены'
        self.safe_update(self.update_items_widget_button)
        market_list = common.session.get_game_market_list(appid=self.__app_id)
        build_items = [Item(item) for item in market_list]
        self.__items = [item for item in build_items if not item.is_bug_item() and item.is_current_game(self.__app_id)]
        self.__items.sort(key=lambda item: item.name)

        time.sleep(5)
        if self.__items:
            self.create_widget_button.disabled = False
            self.create_widget_button.expand = True
            self.safe_update(self.create_widget_button)
            self.update_items_widget_button.expand = False
        self.update_items_widget_button.disabled = False
        self.update_items_widget_button.text = 'Обновить предметы и цены'
        self.safe_update(self.update_items_widget_button)

