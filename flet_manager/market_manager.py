import datetime
import re
import threading
import time

from flet_manager import common
import flet as ft
from logger_utility.logger_config import logger

class Description:
    def __init__(self, description_dict: dict):
        self.type = description_dict.get('type')
        self.value = description_dict.get('value')
class AssetDescription:
    def __init__(self, asset_description_dict: dict):
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
    def get_delta(self, old_item: 'Item'):
        return ItemDelta(self, old_item)
    def color(self):
        return f'#{self.asset_description.name_color}' if self.asset_description.name_color else ''

class ItemDelta:
    def __init__(self, now_item: Item, old_item: Item):
        self.now_item = now_item
        self.old_item = old_item

        self.sell_listings = self.now_item.sell_listings - self.old_item.sell_listings
        self.sell_price = self.now_item.sell_price - self.old_item.sell_price
        self.sell_price_text = self.__generate_sell_price_text()

        self.sell_price_percent = self.__generate_sell_price_percent()
        self.sell_listings_percent = self.__generate_sell_listings_percent()

    def __replace_number_in_currency(self, new_number):
        original_str = self.now_item.sell_price_text if self.now_item.sell_price_text else self.old_item.sell_price_text
        if not original_str: return str(new_number)
        return re.sub(r'\d{1,3}(?:\s?\d{3})*(?:[,.]\d+)?', new_number, str(original_str))
    def __generate_sell_price_text(self):
        return self.__replace_number_in_currency(f"{round((self.now_item.sell_price - self.old_item.sell_price) / 100, 2):.2f}")
    def __generate_sell_price_percent(self):
        _percent_change = abs((self.now_item.sell_price / self.old_item.sell_price) - 1 if self.old_item.sell_price != 0 else 0)
        return round(_percent_change * 100, 2)
    def __generate_sell_listings_percent(self):
        _percent_change = abs((self.now_item.sell_listings / self.old_item.sell_listings) - 1 if self.old_item.sell_listings != 0 else 0)
        return round(_percent_change * 100, 2)
    def color_sell_price_text(self):
        return ft.colors.GREEN if self.sell_price >= 0 else ft.colors.RED
    def color_sell_listings(self):
        return ft.colors.GREEN if self.sell_listings >= 0 else ft.colors.RED
    def is_draw_sell_price_text(self):
        return self.sell_price != 0
    def is_draw_sell_listings(self):
        return self.sell_listings != 0
    def get_tooltip(self, datetime_now: datetime.datetime, datetime_old: datetime.datetime):
        return (f"{datetime_old.strftime('%d.%m.%Y %H:%M')} -> {datetime_now.strftime('%d.%m.%Y %H:%M')}\n"
                f"Цена: {self.old_item.sell_price_text} -> {self.now_item.sell_price_text} ({self.__generate_sell_price_text()}) [{self.__generate_sell_price_percent():.2f}%]\n"
                f"Кол-во: {self.old_item.sell_listings}шт. -> {self.now_item.sell_listings}шт. ({self.sell_listings}шт.) [{self.__generate_sell_listings_percent():.2f}%]")

class History:
    def __init__(self, history_dict: dict):
        self.time_update = history_dict.get('time_update', datetime.datetime.min)
        self.items = [Item(i) for i in history_dict.get('items', [])]

    def get_list_market_hash_name(self) -> set:
        return {item.market_hash_name() for item in self.items if not item.is_bug_item()}

    def get_item_from_market_hash_name(self, market_hash_name: str) -> Item:
        return next((i for i in self.items if not i.is_bug_item() and i.market_hash_name() == market_hash_name), Item())

class ListHistory:
    def __init__(self):
        _all_history = common.get_history_market_list()
        self.list_history = [History(entry) for entry in _all_history]

    def get_latest_history(self):
        if not self.list_history: return History({})
        return max(self.list_history, key=lambda entry: entry.time_update)

    def get_previous_history(self):
        latest_history = self.get_latest_history()
        if not latest_history or not self.list_history: return History({})
        previous_histories = [entry for entry in self.list_history if entry.time_update != latest_history.time_update]
        if not previous_histories: return History({})
        return max(previous_histories, key=lambda entry: entry.time_update)

    def get_history_hours_ago(self, hours_ago: int = 1):
        time_threshold = datetime.datetime.now() - datetime.timedelta(hours=hours_ago)
        recent_history_entries = [entry for entry in self.list_history if entry.time_update > time_threshold]
        if not recent_history_entries: return History({})
        return min(recent_history_entries, key=lambda entry: entry.time_update)

class ItemData:
    def __init__(self, market_hash_name: str):
        self.market_hash_name = str(market_hash_name)
        self.now_item: Item = None
        self.last_item: Item = None
        self.hour_item: Item = None
        self.day_item: Item = None

        self.now_item_datetime: datetime.datetime = None
        self.last_item_datetime: datetime.datetime = None
        self.hour_item_datetime: datetime.datetime = None
        self.day_item_datetime: datetime.datetime = None

        self.constant_item: Item = None

        self.last_delta: ItemDelta = None
        self.hour_delta: ItemDelta = None
        self.day_delta: ItemDelta = None

        self.name: str = None
        self.name_color: str = None
        self.icon_url: str = None
        self.market_url: str = None

        self.item_widget_datarow = ft.DataRow([], selected=True, on_select_changed=lambda e: print(f"row select changed: {e.data}"))

        __row_item_info = ft.Row(spacing=1, expand=True)
        self.item_name_widget_container = ft.Container(url='', ink=True, content=__row_item_info, margin=0, padding=0)
        self.item_img_widget_image = ft.Image(src='', width=50, height=29)
        __item_img_widget = ft.Container(width=50, height=29, content=self.item_img_widget_image)
        __row_item_info.controls.append(__item_img_widget)
        self.item_name_widget_text = ft.Text(value='', color='', size=15, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
        __item_name_widget_container = ft.Container(width=250, content=self.item_name_widget_text)
        __row_item_info.controls.append(__item_name_widget_container)
        self.item_widget_datarow.cells.append(ft.DataCell(self.item_name_widget_container))

        self.now_item_price_widget_text, self.now_item_count_widget_text, self.now_item_widget_container = self.__create_def_widgets()
        self.item_widget_datarow.cells.append(ft.DataCell(self.now_item_widget_container))

        self.last_item_price_widget_text, self.last_item_count_widget_text, self.last_item_widget_container = self.__create_def_widgets()
        self.item_widget_datarow.cells.append(ft.DataCell(self.last_item_widget_container))

        self.hour_item_price_widget_text, self.hour_item_count_widget_text, self.hour_item_widget_container = self.__create_def_widgets()
        self.item_widget_datarow.cells.append(ft.DataCell(self.hour_item_widget_container))

        self.day_item_price_widget_text, self.day_item_count_widget_text, self.day_item_widget_container = self.__create_def_widgets()
        self.item_widget_datarow.cells.append(ft.DataCell(self.day_item_widget_container))
    def __create_def_widgets(self):
        __text_1 = ft.Text(' ', color='', size=15, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.RIGHT)
        __text_2 = ft.Text(' ', color='', size=15, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.RIGHT)
        __row = ft.Row(expand=True, spacing=0, controls=[__text_1, __text_2])
        return __text_1, __text_2, ft.Container(width=200, content=__row)
    def __get_constant_item_from_items(self, _items_history: list[Item]) -> Item | None:
        for _item in _items_history:
            if _item.is_empty(): continue
            return _item

    def update_data(self, now_history: History, last_history: History, hour_history: History, day_history: History):
        self.now_item = now_history.get_item_from_market_hash_name(self.market_hash_name)
        self.last_item = last_history.get_item_from_market_hash_name(self.market_hash_name)
        self.hour_item = hour_history.get_item_from_market_hash_name(self.market_hash_name)
        self.day_item = day_history.get_item_from_market_hash_name(self.market_hash_name)

        self.now_item_datetime = now_history.time_update
        self.last_item_datetime = last_history.time_update
        self.hour_item_datetime = hour_history.time_update
        self.day_item_datetime = day_history.time_update

        self.constant_item = self.__get_constant_item_from_items([self.now_item, self.last_item, self.hour_item, self.day_item])
        if not self.constant_item: return

        self.last_delta = self.now_item.get_delta(self.last_item)
        self.hour_delta = self.now_item.get_delta(self.hour_item)
        self.day_delta = self.now_item.get_delta(self.day_item)

        self.item_name_widget_container.url = self.constant_item.market_url()
        self.item_img_widget_image.src = self.constant_item.icon_url()
        self.item_name_widget_text.value = self.constant_item.name
        self.item_name_widget_text.color = self.constant_item.color()

        self.now_item_price_widget_text.value = self.now_item.sell_price_text
        self.now_item_count_widget_text.value = f'{self.now_item.sell_listings}шт.'

        self.last_item_price_widget_text.value = self.last_delta.sell_price_text if self.last_delta.is_draw_sell_price_text() else ' '
        self.last_item_price_widget_text.color = self.last_delta.color_sell_price_text()
        # self.last_item_price_widget_text.visible = self.last_delta.is_draw_sell_price_text()
        self.last_item_count_widget_text.value = f'{self.last_delta.sell_listings}шт.' if self.last_delta.is_draw_sell_listings() else ' '
        self.last_item_count_widget_text.color = self.last_delta.color_sell_listings()
        # self.last_item_count_widget_text.visible = self.last_delta.is_draw_sell_listings()
        self.last_item_widget_container.tooltip = self.last_delta.get_tooltip(self.now_item_datetime, self.last_item_datetime)

        self.hour_item_price_widget_text.value = self.hour_delta.sell_price_text if self.hour_delta.is_draw_sell_price_text() else ' '
        self.hour_item_price_widget_text.color = self.hour_delta.color_sell_price_text()
        # self.hour_item_price_widget_text.visible = self.hour_delta.is_draw_sell_price_text()
        self.hour_item_count_widget_text.value = f'{self.hour_delta.sell_listings}шт.' if self.hour_delta.is_draw_sell_listings() else ' '
        self.hour_item_count_widget_text.color = self.hour_delta.color_sell_listings()
        # self.hour_item_count_widget_text.visible = self.hour_delta.is_draw_sell_listings()
        self.hour_item_widget_container.tooltip = self.hour_delta.get_tooltip(self.now_item_datetime, self.hour_item_datetime)

        self.day_item_price_widget_text.value = self.day_delta.sell_price_text if self.day_delta.is_draw_sell_price_text() else ' '
        self.day_item_price_widget_text.color = self.day_delta.color_sell_price_text()
        # self.day_item_price_widget_text.visible = self.day_delta.is_draw_sell_price_text()
        self.day_item_count_widget_text.value = f'{self.day_delta.sell_listings}шт.' if self.day_delta.is_draw_sell_listings() else ' '
        self.day_item_count_widget_text.color = self.day_delta.color_sell_listings()
        # self.day_item_count_widget_text.visible = self.day_delta.is_draw_sell_listings()
        self.day_item_widget_container.tooltip = self.day_delta.get_tooltip(self.now_item_datetime, self.day_item_datetime)


class MarketItemListTable(ft.DataTable):
    def __init__(self):
        super().__init__([])
        self.alignment = ft.MainAxisAlignment.START
        self.column_spacing = 5
        self.vertical_lines = ft.BorderSide(1)
        self.heading_row_height = 50
        self.data_row_min_height = 25
        self.data_row_max_height = 25

        self.sort_type = 'now'
        self.name_filter = ''
        self.items_list: dict[str, ItemData] = {}

        title_column_name_text_widget = ft.Text('Предмет', size=18)
        title_column_name_textfield_widget = ft.TextField(label='Name Filter', dense=True, content_padding=10, text_align=ft.TextAlign.LEFT,
                                                          expand=True, max_lines=1)
        title_column_name_textfield_widget.on_submit = lambda e: self.__on_change_name_filter(title_column_name_textfield_widget.value)
        title_column_name_row_widget = ft.Row(controls=[title_column_name_text_widget, title_column_name_textfield_widget], expand=True)
        title_column_name_container_widget = ft.Container(width=200, height=self.heading_row_height, content=title_column_name_row_widget)
        title_column_name_widget = ft.DataColumn(title_column_name_container_widget)

        t_c_n_widget_container = ft.Container(width=200, content=ft.Text('Цена сейчас', size=18, text_align=ft.TextAlign.CENTER, expand=True))
        t_c_n_widget_row = ft.Row(controls=[ft.FilledButton('Цена', expand=True), ft.FilledButton('Кол-во', expand=True)], expand=True)
        t_c_n_main_widget_container = ft.Container(width=200, height=self.heading_row_height,
                                                   content=ft.Column(spacing=0, controls=[t_c_n_widget_container, t_c_n_widget_row]))
        t_c_n = ft.DataColumn(t_c_n_main_widget_container)

        t_c_l_widget_container = ft.Container(width=200, content=ft.Text('Прошлая проверка', size=18, text_align=ft.TextAlign.CENTER, expand=True))
        t_c_l_widget_row = ft.Row(controls=[ft.FilledButton('Цена', expand=True), ft.FilledButton('Кол-во', expand=True)], expand=True)
        t_c_l_main_widget_container = ft.Container(width=200, height=self.heading_row_height,
                                                   content=ft.Column(spacing=0, controls=[t_c_l_widget_container, t_c_l_widget_row]))
        t_c_l = ft.DataColumn(t_c_l_main_widget_container)

        t_c_h_widget_container = ft.Container(width=200, content=ft.Text('Цена за час', size=18, text_align=ft.TextAlign.CENTER, expand=True))
        t_c_h_widget_row = ft.Row(controls=[ft.FilledButton('Цена', expand=True), ft.FilledButton('Кол-во', expand=True)], expand=True)
        t_c_h_main_widget_container = ft.Container(width=200, height=self.heading_row_height,
                                                   content=ft.Column(spacing=0, controls=[t_c_h_widget_container, t_c_h_widget_row]))
        t_c_h = ft.DataColumn(t_c_h_main_widget_container)

        t_c_d_widget_container = ft.Container(width=200, content=ft.Text('Цена за день', size=18, text_align=ft.TextAlign.CENTER, expand=True))
        t_c_d_widget_row = ft.Row(controls=[ft.FilledButton('Цена', expand=True), ft.FilledButton('Кол-во', expand=True)], expand=True)
        t_c_d_main_widget_container = ft.Container(width=200, height=self.heading_row_height,
                                                   content=ft.Column(spacing=0, controls=[t_c_d_widget_container, t_c_d_widget_row]))
        t_c_d = ft.DataColumn(t_c_d_main_widget_container)

        self.columns = [title_column_name_widget, t_c_n, t_c_l, t_c_h, t_c_d]

    def __on_change_name_filter(self, name_filter: str = ''):
        self.name_filter = name_filter
        print(self.name_filter)

    def __on_change_sort(self, sort_type: str = ''):
        self.sort_type = sort_type

    def create_update_items(self):
        list_history = ListHistory()
        now_history = list_history.get_latest_history()
        last_history = list_history.get_previous_history()
        hour_history = list_history.get_history_hours_ago(hours_ago=1)
        day_history = list_history.get_history_hours_ago(hours_ago=24)

        list_market_hash_name = (now_history.get_list_market_hash_name() | last_history.get_list_market_hash_name()
                                 | hour_history.get_list_market_hash_name() | day_history.get_list_market_hash_name())

        for market_hash_name in list_market_hash_name:
            if market_hash_name not in self.items_list:
                item_data = ItemData(market_hash_name)
                self.items_list[market_hash_name] = item_data
                self.rows.append(item_data.item_widget_datarow)
            self.items_list[market_hash_name].update_data(now_history, last_history, hour_history, day_history)
        self.update()

class MarketWidget(ft.Row):
    def __init__(self):
        super().__init__()
        self.__is_run = False
        self.isolated = True
        self.expand = True
        self.alignment = ft.MainAxisAlignment.START
        self.items_datagram = {}

        self.item_list_column = ft.Column(expand=True)
        self.history_column = ft.Column()
        self.controls = [self.item_list_column, ft.VerticalDivider(), self.history_column]

        self.item_list_column_title = ft.Text('Торговая площадка. Список предметов:', size=24, color=ft.colors.BLUE, weight=ft.FontWeight.BOLD)
        self.item_list_column.controls.append(ft.Row([self.item_list_column_title], alignment=ft.MainAxisAlignment.CENTER))

        self.history_column_title = ft.Text('История:', size=24, color=ft.colors.BLUE, weight=ft.FontWeight.BOLD)
        self.history_column.controls.append(ft.Row([self.history_column_title], alignment=ft.MainAxisAlignment.CENTER))

        self.items_column = MarketItemListTable()
        self.item_list_column.controls.append(ft.Column(scroll=ft.ScrollMode.AUTO, spacing=1, expand=True, controls=[self.items_column]))
        self.items_history_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=1)
        self.history_column.controls.append(self.items_history_column)

    def will_unmount(self):
        self.__is_run = False
    def did_mount(self):
        self.__is_run = True
        threading.Thread(target=self.__update).start()
    def __update(self):
        while self.__is_run:
            try:
                self.update_widget()
                self.update()
                self.page.update()
            except:
                logger.exception('Exception in market update')
            finally:
                time.sleep(10)

    def update_widget(self):
        if not common.debug_test:
            common.update_market_list()
        # self.update_history()
        self.items_column.create_update_items()


    @staticmethod
    def __get_item_from_history(market_hash_name: str, history: dict) -> dict:
        return next((i for i in history.get('items', []) if i.get('hash_name', '') == market_hash_name and
                     i.get('asset_description', {}).get('market_hash_name', '') == market_hash_name), {})
    @staticmethod
    def __get_history_list_name(history: dict) -> set:
        items = history.get('items', [])
        return {item.get('hash_name') for item in items if item.get('hash_name') == item.get('asset_description', {}).get('market_hash_name')}
    @staticmethod
    def __replace_number_in_currency(original_str, new_number):
        pattern = r'\d{1,3}(?:\s?\d{3})*(?:[,.]\d+)?'
        return re.sub(pattern, new_number, original_str)

    def find_change_history(self, now_history: dict, old_history: dict):
        if not now_history and not old_history: return None
        now_history_datetime = now_history.get('time_update', datetime.datetime.min)
        old_history_datetime = old_history.get('time_update', datetime.datetime.min)

        column_period_widget = ft.Column(spacing=0)
        column_period_widget.controls.append(ft.Text(f'{now_history_datetime.strftime("%d.%m.%Y %H:%M")}-{old_history_datetime.strftime("%d.%m.%Y %H:%M")}'))

        common_hash_names = self.__get_history_list_name(now_history) & self.__get_history_list_name(old_history)
        if not common_hash_names: return None

        for market_hash_name in common_hash_names:
            item_column_info = ft.Column(spacing=0)

            now_history_item = self.__get_item_from_history(market_hash_name, now_history)
            old_history_item = self.__get_item_from_history(market_hash_name, old_history)

            old_sell_price_text = old_history_item.get('sell_price_text', '')
            old_sell_price = old_history_item.get('sell_price', 0)
            old_sell_listings = old_history_item.get('sell_listings', 0)

            now_sell_price_text = now_history_item.get('sell_price_text', '')
            now_sell_price = now_history_item.get('sell_price', 0)
            now_sell_listings = now_history_item.get('sell_listings', 0)

            asset_description = now_history_item.get('asset_description', old_history_item.get('asset_description', {}))
            item_column_info.tooltip = f'Цена: {old_sell_price_text} -> {now_sell_price_text}\nКол-во: {old_sell_listings}шт. -> {now_sell_listings}шт.'

            row_item_info = ft.Row(spacing=1, expand=True)
            item_name_widget = ft.Container(
                ink=True, content=row_item_info, margin=0, padding=0,
                url=f'https://steamcommunity.com/market/listings/{asset_description.get("appid", common.app_id)}/{market_hash_name}',
            )
            item_column_info.controls.append(item_name_widget)
            icon_url = f'https://community.akamai.steamstatic.com/economy/image/{asset_description.get("icon_url", "")}/330x192?allow_animated=1'
            row_item_info.controls.append(ft.Container(width=50, height=29, content=ft.Image(src=icon_url, width=50, height=29)))
            item_color = asset_description.get('name_color')
            item_name_widget_container = ft.Container(width=150, content=ft.Text(
                f"{asset_description.get('name', ' ')}", color=f'#{item_color}' if item_color else '', overflow=ft.TextOverflow.ELLIPSIS))
            row_item_info.controls.append(item_name_widget_container)

            item_new_del_widget = None
            item_change_widget = None
            if not now_sell_price_text:
                item_new_del_widget = ft.Column(spacing=0)
                item_new_del_widget.controls.append(ft.Text('Предмет ушел с продажи', color=ft.colors.BLUE))
                item_new_del_widget.controls.append(ft.Text(f'Цена: {old_sell_price_text} [{old_sell_listings} шт.]', color=ft.colors.RED))
                item_column_info.controls.append(item_new_del_widget)
            elif not old_sell_price_text:
                item_new_del_widget = ft.Column(spacing=0)
                item_new_del_widget.controls.append(ft.Text('Новый предмет в продаже', color=ft.colors.BLUE))
                item_new_del_widget.controls.append(ft.Text(f'Цена: {now_sell_price_text} [{now_sell_listings} шт.]', color=ft.colors.GREEN))
                item_column_info.controls.append(item_new_del_widget)
            else:
                def_price = now_sell_price - old_sell_price
                def_count = now_sell_listings - old_sell_listings
                if def_price == 0 and def_count == 0: continue
                percent_change_price = abs((now_sell_price / old_sell_price) - 1 if old_sell_price != 0 else 0)
                percent_change_count = abs((now_sell_listings / old_sell_listings) - 1 if old_sell_listings != 0 else 0)

                item_change_widget = ft.Column(spacing=0)
                if percent_change_price >= 0.1:
                    color = ft.colors.GREEN if def_price >= 0 else ft.colors.RED
                    percent_change_price_text = self.__replace_number_in_currency(old_sell_price_text, f"{round(def_price / 100, 2):.2f}")
                    item_change_widget.controls.append(ft.Text(f'Цена: {percent_change_price_text}[{round(percent_change_price*100, 2):.2f}%]', color=color))

                if percent_change_count >= 0.1:
                    color = ft.colors.GREEN if def_count >= 0 else ft.colors.RED
                    item_change_widget.controls.append(ft.Text(f'Кол-во: {def_count}шт.[{round(percent_change_count*100, 2):.2f}%]', color=color))
                if len(item_change_widget.controls) > 0:
                    item_column_info.controls.append(item_change_widget)
                    item_column_info.controls.append(ft.Divider(height=1))

            is_item_new_del_widget = item_new_del_widget and len(item_new_del_widget.controls) > 0
            is_item_change_widget = item_change_widget and len(item_change_widget.controls) > 0
            if item_name_widget and (is_item_new_del_widget or is_item_change_widget):
                column_period_widget.controls.append(item_column_info)

        return column_period_widget if column_period_widget and len(column_period_widget.controls) > 1 else None

    def update_history(self):
        all_history = common.get_history_market_list()
        if not all_history: return

        start_time = datetime.datetime.now()
        list_history = []

        while True:
            filtered_history = [h for h in all_history if h.get('time_update', datetime.datetime.min) <= start_time]
            if not filtered_history: break
            min_date_history = max(filtered_history, key=lambda x: x['time_update'])
            list_history.append(min_date_history)
            if len(list_history) >= 20: break
            start_time = min_date_history['time_update'] - datetime.timedelta(minutes=60)

        if not list_history: return
        self.items_history_column.controls = []
        now_history = None
        for history in list_history:
            if not now_history:
                now_history = history
                continue
            history_change = self.find_change_history(now_history, history)
            if history_change:
                self.items_history_column.controls.append(history_change)
                self.items_history_column.controls.append(ft.Divider(height=5))

            now_history = history.copy()

        self.items_history_column.update()
