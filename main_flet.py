import datetime
import os
import pathlib, threading, time, json
import random
import re
from dateutil.parser import parse

import flet as ft

from sql_manager import sqlite_manager
from sql_manager.config import setting
from temp_steam_session import SteamWebSession, InventoryManager
from logger_utility.logger_config import logger
from enum import Enum

class Currency(Enum):
    USD = 1
    GBP = 2
    EUR = 3
    CHF = 4
    RUB = 5
    PLN = 6
    BRL = 7
    JPY = 8
    NOK = 9
    IDR = 10
    MYR = 11
    PHP = 12
    SGD = 13
    THB = 14
    VND = 15
    KRW = 16
    TRY = 17
    UAH = 18
    MXN = 19
    CAD = 20
    AUD = 21
    NZD = 22
    CNY = 23
    INR = 24
    CLP = 25
    PEN = 26
    COP = 27
    ZAR = 28
    HKD = 29
    TWD = 30
    SAR = 31
    AED = 32
    ARS = 34
    ILS = 35
    BYN = 36
    KZT = 37
    KWD = 38
    QAR = 39
    CRC = 40
    UYU = 41
    RMB = 9000
    NXP = 9001

class Games(Enum):
    Banana = 2923300
    Cats = 2977660
    CS2 = 730
    EGG = 2784840
    EggSurprise = 3017120
    Steam = 753
    Tapple = 3047030

class CustomContextID(Enum):
    Steam = 6

class SharedClass:
    def __init__(self):
        self.debug_test = False

        self.app_id = setting.app_id
        self.games = {game.name: game.value for game in Games}
        self.currencies = {currency.name: currency.value for currency in Currency}
        self.context_ids = {context_id.name: context_id.value for context_id in CustomContextID}
        self.default_currency = setting.default_currency

        self.inventory: InventoryManager = None
        self.next_updated_inventory = datetime.datetime.min
        self.next_updated_market = datetime.datetime.min
        self.session: SteamWebSession = None
        self.items_price = []
        self.items_price_old = {}

        self.dialog_is_open = False
        self.prefix_currency = setting.prefix_currency
        self.suffix_currency = setting.suffix_currency

        self.current_items_price = {}
        self.current_items_price_old = {}
        self.items_nameid: dict = setting.items_nameid.copy()
        self.load_prices()

    def update_current_inventory(self):
        __currency = str(self.default_currency)
        self.current_items_price[__currency] = self.items_price.copy()
        self.current_items_price_old[__currency] = self.items_price_old.copy()
        self.__save_prices()

    def set_current_inventory(self):
        __currency = str(self.default_currency)
        self.items_price = self.current_items_price.get(__currency, [])
        self.items_price_old = self.current_items_price_old.get(__currency, {})

    def __serialize_dates(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self.__serialize_dates(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self.__serialize_dates(item) for item in obj]
        else:
            return obj

    def __deserialize_dates(self, obj):
        if isinstance(obj, str):
            try:
                return parse(obj)
            except ValueError:
                return obj
        elif isinstance(obj, dict):
            return {key: self.__deserialize_dates(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self.__deserialize_dates(item) for item in obj]
        else:
            return obj

    def __save_prices(self):
        setting.current_items_price = self.__serialize_dates(self.current_items_price.copy())
        setting.current_items_price_old = self.__serialize_dates(self.current_items_price_old.copy())

    def load_prices(self):
        self.current_items_price = self.__deserialize_dates(setting.current_items_price)
        self.current_items_price_old = self.__deserialize_dates(setting.current_items_price_old)
        self.set_current_inventory()

    def get_context_id(self) -> int:
        for game_name, app_id in self.games.items():
            if app_id == self.app_id:
                return self.context_ids.get(game_name, 2)
        return 2
common = SharedClass()


class DialogSell(ft.AlertDialog):
    def __init__(self, item_data: dict = None):
        super().__init__()
        self.isolated = True
        self.expand = True

        self.last_updated = datetime.datetime.now()
        self.item_data = item_data
        self.market_hash_name = self.item_data.get('market_hash_name')
        self.all_item_in_inventary = [item for item in common.inventory.inventory
                                      if item.get('rgDescriptions', {}).get('market_hash_name', "") == self.market_hash_name]
        self.item_id = self.load_item_nameid()
        self.itemordershistogram = {}
        self.item_count = int(item_data.get('count', 1))

        self.on_dismiss = self.__on_dismiss
        self.__updated_time = ft.Text(value=f' ')
        self.create_title()

        self.item_info_column = ft.Column(alignment=ft.MainAxisAlignment.START, expand=True)
        self.sell_info_column = ft.Column(scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.START)
        self.buy_info_column = ft.Column(scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.START)
        self.content = ft.Column(
            expand=True,
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Row(
                    expand=True,
                    controls=[
                        self.item_info_column,
                        ft.VerticalDivider(),
                        self.sell_info_column,
                        ft.VerticalDivider(),
                        self.buy_info_column
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    width=1000
                )
            ]
        )

        self.button_price_sell = ft.TextField(label='Покупатель заплатит', dense=True, content_padding=10, expand=True, max_lines=1, text_align=ft.TextAlign.RIGHT,
                                              prefix_text=common.prefix_currency, suffix_text=common.suffix_currency, on_change=self.on_change_button_price_sell)
        self.button_price_get = ft.TextField(label='Вы получите', dense=True, content_padding=10, expand=True, max_lines=1, text_align=ft.TextAlign.RIGHT,
                                             prefix_text=common.prefix_currency, suffix_text=common.suffix_currency, on_change=self.on_change_button_price_get)
        price_row = ft.Row(controls=[self.button_price_sell, self.button_price_get])
        self.item_info_column.controls.append(price_row)


        self.count_item_sell = ft.TextField(label='Количество к продаже', dense=True, content_padding=10, expand=True, max_lines=1, text_align=ft.TextAlign.RIGHT,
                                            suffix_text=f"из {self.item_count}", value='1',
                                            input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9]", replacement_string=""))
        self.count_item_sell_one = ft.FilledButton('1', on_click=lambda e: self.set_count_sell(count=1))
        self.count_item_sell_center = ft.FilledButton('50%', on_click=lambda e, _count=self.item_count: self.set_count_sell(count=_count*0.5))
        self.count_item_sell_all = ft.FilledButton('Все', on_click=lambda e, _count=self.item_count: self.set_count_sell(count=_count))
        count_row = ft.Row(controls=[self.count_item_sell, self.count_item_sell_one, self.count_item_sell_center, self.count_item_sell_all])
        self.item_info_column.controls.append(count_row)

        self.button_total_price_sell = ft.TextField(label='Всего покупатель заплатит', dense=True, content_padding=10, expand=True, max_lines=1,
                                                    text_align=ft.TextAlign.RIGHT, prefix_text=common.prefix_currency, disabled=True,
                                                    suffix_text=common.suffix_currency)
        self.button_total_price_get = ft.TextField(label='Всего вы получите', dense=True, content_padding=10, expand=True, max_lines=1,
                                                   text_align=ft.TextAlign.RIGHT, prefix_text=common.prefix_currency, disabled=True,
                                                   suffix_text=common.suffix_currency)
        total_price_row = ft.Row(controls=[self.button_total_price_sell, self.button_total_price_get])
        self.item_info_column.controls.append(total_price_row)

        self.button_start_sell = ft.FilledButton('Продать', on_click=self.start_sell, expand=True, disabled=True)
        start_sell_row = ft.Row(controls=[self.button_start_sell])
        self.item_info_column.controls.append(start_sell_row)

        self.log_column = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.item_info_column.controls.append(ft.Row(controls=[self.log_column], expand=True))

    def start_sell(self, *args):
        button_price_get = int(float(self.button_price_get.value if self.button_price_get.value else 0) * 100)
        if not button_price_get: return
        count_item_sell = int(self.count_item_sell.value if self.count_item_sell.value else 0)
        if not count_item_sell: return
        for item in self.all_item_in_inventary:
            if count_item_sell <= 0: break
            item_id = item.get('id', None)
            amount = int(item.get('amount', 1))
            if amount > count_item_sell:
                amount = count_item_sell
            count_item_sell -= amount
            status = common.session.fetch_sellitem(appid=int(common.app_id), assetid=int(item_id), amount=int(amount), price=button_price_get, contextid=common.get_context_id())
            self.log_column.controls.insert(0, ft.Text(f'{status}'))
            time.sleep(3)
        self.log_column.controls.insert(0, ft.Text(f'Готово, выставил {int(self.count_item_sell.value if self.count_item_sell.value else 0)}'))

    def update_total(self, *args):
        button_price_sell = float(self.button_price_sell.value if self.button_price_sell.value else 0)
        button_price_get = float(self.button_price_get.value if self.button_price_get.value else 0)
        count_item_sell = int(self.count_item_sell.value if self.count_item_sell.value else 0)
        
        self.button_total_price_sell.value = f'{round(button_price_sell*count_item_sell, 2)}'
        self.button_total_price_sell.update()

        self.button_total_price_get.value = f'{round(button_price_get*count_item_sell, 2)}'
        self.button_total_price_get.update()

        self.button_start_sell.text = f'Продать {count_item_sell} {self.item_data.get("name")} за {round(button_price_get * count_item_sell, 2)}'
        self.button_start_sell.disabled = button_price_get == 0 or count_item_sell == 0
        self.button_start_sell.update()

    def set_count_sell(self, *args, count=None):
        if count:
            self.count_item_sell.value = int(count)
        if int(self.count_item_sell.value) > self.item_count:
            self.count_item_sell.value = self.item_count
        self.count_item_sell.update()
        self.update_total()

    def calculate_total(self, price_get: float = None, price_sell: float = None):
        min_commission = 0.02  # Минимальная комиссия

        if price_sell is not None:
            price_get_value = price_sell / 115 * 100
            price_sell_value = price_sell
            if price_sell_value - price_get_value < min_commission:
                price_get_value = price_sell_value - min_commission
        elif price_get is not None:
            price_get_value = price_get
            price_sell_value = price_get / 100 * 115
            if price_sell_value - price_get_value < min_commission:
                price_sell_value = price_get_value + min_commission
        else:
            return  # Ничего не делаем, если оба значения отсутствуют

        self.button_price_get.value = f'{round(price_get_value, 2):.2f}'
        self.button_price_get.update()
        self.button_price_sell.value = f'{round(price_sell_value, 2):.2f}'
        self.button_price_sell.update()

        self.update_total()

    def on_change_button_price_sell(self, e):
        # Сначала заменяем запятые на точки для унификации десятичного разделителя
        unified_value = e.control.value.replace(',', '.')

        # Ищем соответствие числу с максимум двумя цифрами после десятичной точки
        match = re.search(r'\d+(\.\d{0,2})?', unified_value)

        if match:
            try:
                self.calculate_total(price_sell=float(match.group(0)))
            except:
                pass
        else:
            # Если соответствие не найдено, устанавливаем пустую строку
            e.control.value = ''

    def on_change_button_price_get(self, e):
        # Сначала заменяем запятые на точки для унификации десятичного разделителя
        unified_value = e.control.value.replace(',', '.')

        # Ищем соответствие числу с максимум двумя цифрами после десятичной точки
        match = re.search(r'\d+(\.\d{0,2})?', unified_value)

        if match:
            try:
                self.calculate_total(price_get=float(match.group(0)))
            except:
                pass
        else:
            # Если соответствие не найдено, устанавливаем пустую строку
            e.control.value = ''


    def load_item_nameid(self):
        if self.market_hash_name in common.items_nameid:
            return common.items_nameid[self.market_hash_name]
        item_nameid = common.session.fetch_item_nameid(self.market_hash_name, common.app_id)
        if item_nameid:
            common.items_nameid[self.market_hash_name] = item_nameid
            setting.items_nameid = common.items_nameid.copy()
            return item_nameid

    def load_itemordershistogram(self):
        return common.session.fetch_market_itemordershistogram(currency=common.default_currency, item_nameid=self.item_id)

    def create_title(self):
        item_name = self.item_data.get('name', 'No Name')
        name_color = self.item_data.get('name_color', None)
        icon_url = self.item_data.get('icon_url', None)
        count = self.item_data.get('count', 0)
        self.title = ft.Row(expand=True, alignment=ft.MainAxisAlignment.CENTER)
        if icon_url:
            item_img_url = f'https://community.akamai.steamstatic.com/economy/image/{icon_url}/330x192?allow_animated=1'
            item_img_widget = ft.Container(width=50*1.2, height=29*1.2, content=ft.Image(src=item_img_url, width=50*1.2, height=29*1.2))
            self.title.controls.append(item_img_widget)
        widget_name = ft.Text(size=29, value=f'{count} шт.  {item_name}', color=f'#{name_color}' if name_color else '')
        self.title.controls.append(widget_name)
        self.title.controls.append(self.__updated_time)

    def __on_dismiss(self, *args):
        common.dialog_is_open = False

    def did_mount(self):
        threading.Thread(target=self.__update).start()

    @staticmethod
    def __get_clear_text(html_content: str):
        content_with_newlines = re.sub(r'<br\s*/?>', '\n', html_content)
        return re.sub(r'<[^>]+>', '', content_with_newlines)

    def update_sell_buy_info(self):
        self.itemordershistogram = self.load_itemordershistogram()
        if not self.itemordershistogram: return
        self.buy_info_column.controls = []
        buy_order_summary = self.__get_clear_text(self.itemordershistogram.get('buy_order_summary', ''))
        buy_order_summary_content = ft.Text(value=buy_order_summary)
        self.buy_info_column.controls.append(buy_order_summary_content)
        buy_order_graph = self.itemordershistogram.get('buy_order_graph', [list[int, int, str]])
        for item in buy_order_graph[:15]:
            price, count, text = item
            item_conrtol = ft.Container(ink=True, on_click=lambda e, _price=price: self.calculate_total(price_sell=_price))
            self.buy_info_column.controls.append(item_conrtol)
            item_row = ft.Row()
            item_price_conrtol = ft.Container(width=60, content=ft.Text(value=f'{common.prefix_currency}{round(price, 2)} {common.suffix_currency}',
                                                                        expand=True, text_align=ft.TextAlign.RIGHT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS))
            item_count_conrtol = ft.Container(width=80, content=ft.Text(value=f'{count} шт.',
                                                                        expand=True, text_align=ft.TextAlign.RIGHT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS))
            item_row.controls = [item_price_conrtol, item_count_conrtol]
            item_conrtol.content = item_row


        self.sell_info_column.controls = []
        sell_order_summary = self.__get_clear_text(self.itemordershistogram.get('sell_order_summary', ''))
        sell_order_summary_content = ft.Text(value=sell_order_summary)
        self.sell_info_column.controls.append(sell_order_summary_content)
        sell_order_graph = self.itemordershistogram.get('sell_order_graph', [list[int, int, str]])
        for item in sell_order_graph[:15]:
            price, count, text = item
            item_conrtol = ft.Container(ink=True, on_click=lambda e, _price=price: self.calculate_total(price_sell=_price))
            self.sell_info_column.controls.append(item_conrtol)
            item_row = ft.Row()
            item_price_conrtol = ft.Container(width=60, content=ft.Text(value=f'{common.prefix_currency}{round(price, 2)} {common.suffix_currency}',
                                                                        expand=True, text_align=ft.TextAlign.RIGHT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS))
            item_count_conrtol = ft.Container(width=80, content=ft.Text(value=f'{count} шт.',
                                                                        expand=True, text_align=ft.TextAlign.RIGHT, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS))
            item_row.controls = [item_price_conrtol, item_count_conrtol]
            item_conrtol.content = item_row

    def update_widget(self):
        datetime_now = datetime.datetime.now()
        self.__updated_time.value = f'Обновление цен через {int((self.last_updated - datetime_now).total_seconds())} сек.'
        if self.last_updated > datetime_now: return
        self.last_updated = datetime_now + datetime.timedelta(seconds=15)
        self.update_sell_buy_info()

    def __update(self):
        while self.open:
            try:
                self.update_widget()
            except:
                pass
            self.update()
            time.sleep(1)

class LoginWidget(ft.Column):
    def __init__(self):
        super().__init__()
        self._is_run = False
        self.isolated = True
        self.expand = True
        self.alignment = ft.MainAxisAlignment.CENTER

        self._title = ft.Text(
            'Ваша сессия в Steam истекла. Пожалуйста, выполните вход заново.',
            size=24,
            color=ft.colors.BLUE,
            weight=ft.FontWeight.BOLD
        )
        self._login = ft.TextField(label='Steam Login', dense=True, content_padding=10, text_align=ft.TextAlign.CENTER)
        self._login.value = setting.login
        self._password = ft.TextField(label='Steam Password', dense=True, content_padding=10, password=True, text_align=ft.TextAlign.CENTER)
        self._password.value = setting.password
        self._2fa = ft.TextField(label='Guard Code', dense=True, content_padding=10, password=True, text_align=ft.TextAlign.CENTER)

        self._enter_button = ft.FilledButton(
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
            self._login,
            self._password,
            self._2fa,
            ft.Row([self._enter_button], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([self.warning_text], alignment=ft.MainAxisAlignment.CENTER),
        ]

    def did_mount(self):
        self.__is_run = True
        threading.Thread(target=self.__update).start()

    def will_unmount(self):
        self.__is_run = False

    def update_widget(self):
        pass

    def __update(self):
        while self.__is_run:
            self.update_widget()
            self.update()
            time.sleep(1)

class AccountWidget(ft.Row):
    def __init__(self):
        super().__init__()
        self._is_run = False
        self.isolated = True
        self.expand = True
        self.alignment = ft.MainAxisAlignment.START

        self.now_inventory = {}

        self.price_column = ft.Column(expand=True)
        self.history_column = ft.Column()
        self.controls = [self.price_column, ft.VerticalDivider(), self.history_column]

        self.price_column_title = ft.Text(
            'Инвентарь на текущий момент:',
            size=24,
            color=ft.colors.BLUE,
            weight=ft.FontWeight.BOLD
        )

        self.drop_down_game = ft.Dropdown(
            on_change=self.__on_change_game,
            options=[ft.dropdown.Option(game_name) for game_name, app_id in common.games.items()],
            height=30,
            width=100,
            text_size=14,
            dense=True,
            label='Игра',
            content_padding=10,
            value=next((game_name for game_name, app_id in common.games.items() if app_id == common.app_id), Games.Banana.name)
        )

        self.drop_down_currencies = ft.Dropdown(
            on_change=self.__on_change_currencies,
            options=[ft.dropdown.Option(currency) for currency, currency_id in common.currencies.items()],
            height=30,
            width=100,
            text_size=14,
            dense=True,
            label='Валюта',
            content_padding=10,
            value=next((currency for currency, currency_id in common.currencies.items() if currency_id == common.default_currency), Currency.USD.name)
        )

        self.test_button = ft.FilledButton('test', on_click=self.test)

        self.price_column.controls.append(ft.Row([
            self.price_column_title, self.drop_down_game, self.drop_down_currencies,
            # self.test_button
        ], alignment=ft.MainAxisAlignment.CENTER))

        self.price_column_title = ft.Text(
            'История инвентаря:',
            size=24,
            color=ft.colors.BLUE,
            weight=ft.FontWeight.BOLD
        )
        self.history_column.controls.append(ft.Row([self.price_column_title], alignment=ft.MainAxisAlignment.CENTER))

        self.items_price_column = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=1, expand=True)
        self.price_column.controls.append(self.items_price_column)
        self.items_history_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        self.history_column.controls.append(self.items_history_column)

    def test(self, *args):
        inventory = common.session.get_inventory_items(appid=common.app_id, context_id=common.get_context_id())
        print()
        if not inventory:
            print("inventory не загружен")
            return
        tradable_inventory = inventory.get_tradable_inventory()
        if not tradable_inventory:
            print("tradable_inventory не загружен")
            return
        # tradable_url = 'https://steamcommunity.com/tradeoffer/new/?partner=341988637&token=GLFg2wq2'
        tradable_url = None
        if not tradable_url:
            print("tradable_url не загружен")
            return
        status = False
        # status = common.session.trade_send(trade_url=tradable_url, items=tradable_inventory)
        print(status)

    def __on_change_game(self, e):
        if common.app_id == common.games[self.drop_down_game.value]: return
        setting.app_id = common.games[self.drop_down_game.value]
        common.app_id = common.games[self.drop_down_game.value]
        common.next_updated_inventory = datetime.datetime.min

    def __on_change_currencies(self, e):
        if common.default_currency == common.currencies[self.drop_down_currencies.value]: return
        common.update_current_inventory()
        setting.default_currency = common.currencies[self.drop_down_currencies.value]
        common.default_currency = common.currencies[self.drop_down_currencies.value]
        common.set_current_inventory()


    def did_mount(self):
        self.__is_run = True
        threading.Thread(target=self.__update).start()

    def will_unmount(self):
        self.__is_run = False

    def get_price(self, market_hash_name: str):
        if not self.is_item_marketable(market_hash_name):
            return {'lowest_price': f'{common.prefix_currency}0,00 {common.suffix_currency}',
                    'median_price': f'{common.prefix_currency}0,00 {common.suffix_currency}',
                    'success': True,
                    'volume': '0'}
        # Поиск словаря в списке, где 'market_hash_name' совпадает с заданным
        return next((item for item in common.items_price if item['market_hash_name'] == market_hash_name), {}).get('price', {})
        # {'lowest_price': '0,13 pуб.', 'median_price': '0,35 pуб.', 'success': True, 'volume': '1,434,817'}

    def is_item_tradable(self, market_hash_name: str):
        # Если инвентарь пуст, предмет считается торгуемым по умолчанию
        if not common.inventory or not common.inventory.inventory: return False
        items = common.inventory.inventory
        return any(
            bool(item.get('rgDescriptions', {}).get('tradable', False)) and
            item.get('rgDescriptions', {}).get('market_hash_name', '') == market_hash_name
            for item in items
        )

    def is_item_marketable(self, market_hash_name: str):
        # Если инвентарь пуст, предмет считается торгуемым по умолчанию
        if not common.inventory or not common.inventory.inventory: return False
        items = common.inventory.inventory
        return any(
            bool(item.get('rgDescriptions', {}).get('marketable', False)) and
            item.get('rgDescriptions', {}).get('market_hash_name', '') == market_hash_name
            for item in items
        )

    def create_sell_page(self, asset_id, market_hash_name: str = None):
        pass

    def open_sell_item(self, *args, item_data=None):
        if not item_data: return
        dialog = DialogSell(item_data)
        self.page.dialog = dialog
        dialog.open = True
        common.dialog_is_open = True
        self.page.update()

    @staticmethod
    def calculate_total_price(data: dict, count: int) -> tuple:
        if not data or not count:
            return 0.00, f"{common.prefix_currency}0.00 {common.suffix_currency}"
        # Получаем строку с минимальной ценой
        lowest_price = data.get('lowest_price', f"{common.prefix_currency}0.00 {common.suffix_currency}")

        # Регулярное выражение для извлечения числовой части и символов валюты
        price_match = re.search(r'([^\d.,]*)(\d+[\.,]?\d*)\s*([^\d.,]*)', lowest_price)

        if price_match:
            # Извлекаем префикс валюты, число и суффикс валюты
            prefix_currency = price_match.group(1).strip()
            if common.prefix_currency != prefix_currency:
                common.prefix_currency = prefix_currency
                setting.price_currency = prefix_currency
            price_str = price_match.group(2)
            suffix_currency = price_match.group(3).strip()
            if common.suffix_currency != suffix_currency:
                common.suffix_currency = suffix_currency
                setting.suffix_currency = suffix_currency

            # Заменяем запятую на точку для преобразования в число
            price_str = price_str.replace(',', '.')

            # Преобразуем строку в число типа float
            price = float(price_str)

            # Вычисляем общую стоимость
            total_price = round((price * count), 2)

            # Формируем итоговую строку с учетом позиции символа валюты
            if prefix_currency and suffix_currency:
                formatted_price = f'{prefix_currency}{total_price:.2f} {suffix_currency}'
            elif prefix_currency:
                formatted_price = f'{prefix_currency}{total_price:.2f}'
            elif suffix_currency:
                formatted_price = f'{total_price:.2f} {suffix_currency}'
            else:
                formatted_price = f'{total_price:.2f}'
        else:
            # Если совпадение не найдено, считаем цену равной 0
            total_price = 0.00
            formatted_price = f"{common.prefix_currency}0.00 {common.suffix_currency}"

        return total_price, formatted_price.strip()

    @staticmethod
    def calculate_count_change(old_item: dict, new_item: dict) -> int:
        old_count = old_item.get('count', 0)  # Берем старое значение count, если нет, то считаем его 0
        new_count = new_item.get('count', 0)  # То же для нового значения count
        return new_count - old_count  # Возвращаем разницу, которая может быть как положительной, так и отрицательной

    def compare_item_lists(self, old_list: list, new_list: list) -> list:
        old_items = {item['market_hash_name']: item for item in old_list}
        new_items = {item['market_hash_name']: item for item in new_list}

        changes = []

        all_names = set(old_items.keys()) | set(new_items.keys())
        for market_hash_name in all_names:
            old_item = old_items.get(market_hash_name, {'count': 0})
            new_item = new_items.get(market_hash_name, {'count': 0})

            change = self.calculate_count_change(old_item, new_item)
            if change == 0: continue
            change_item = new_item.copy() if new_item.get('market_hash_name') else old_item.copy()
            change_item['count'] = change
            changes.append(change_item)

        return sorted(changes, key=lambda x: abs(x['count']), reverse=True)

    def update_items(self):
        datatime_now = datetime.datetime.now()
        if common.next_updated_inventory < datatime_now:
            logger.info('Начинаю обновление инвентаря')
            inventory = common.session.get_inventory_items(appid=common.app_id, context_id=common.get_context_id())
            common.next_updated_inventory = datetime.datetime.now() + datetime.timedelta(seconds=30)
            if inventory:
                common.inventory = inventory
                logger.info('Инвентарь обновлен')
                common.next_updated_inventory = datetime.datetime.now() + datetime.timedelta(minutes=2)
                self.now_inventory = inventory.get_count_items()
                while True:
                    if sqlite_manager.save_history(datatime_now, self.now_inventory, app_id=common.app_id):
                        logger.info('Инвентарь cохранен')
                        break
                    time.sleep(1)

    def update_items_price(self):
        _all_history: list[dict[str, datetime.datetime | dict | int | str]] = sqlite_manager.get_recent_history()
        all_history = [data for data in _all_history if str(data.get('app_id')) == str(common.app_id)]

        # Собираем уникальные market_hash_name из всех элементов в истории
        all_market_hash_name = {item.get('market_hash_name') for history in all_history for item in history.get('items', []) if item.get('market_hash_name')}

        existing_names = {item['market_hash_name'] for item in common.items_price}
        # Добавляем новые элементы, только если они отсутствуют в existing_names
        for name in all_market_hash_name:
            if name not in existing_names:
                common.items_price.append({
                    'time': datetime.datetime.min,  # Используем минимально возможное значение времени
                    'price': {},  # Пустой словарь для цен
                    'market_hash_name': name  # Сохраняем название товара
                })
        common.items_price.sort(key=lambda item: item['time'])

        if not common.items_price: return

        datetime_now = datetime.datetime.now()
        if common.next_updated_market > datetime_now: return

        # Находим первый элемент, который требует обновления
        first_item = next((item for item in common.items_price if item['time'] < datetime_now and
                           item.get('market_hash_name', '') in all_market_hash_name and self.is_item_marketable(item.get('market_hash_name', ''))), None)
        if not first_item: return

        # Извлекаем необходимые данные из первого элемента
        market_hash_name = first_item.get('market_hash_name', '')
        current_price = first_item.get('price', {})

        # Получаем новую цену
        new_price = common.session.fetch_market_price(market_hash_name, appid=common.app_id, currency=common.default_currency)
        common.next_updated_market = datetime_now + (datetime.timedelta(seconds=10) if new_price else datetime.timedelta(seconds=30))
        logger.info(f"Загрузил цену для {market_hash_name}: {new_price}" if new_price else f"Неудалось загрузить цену для {market_hash_name}: {new_price}")
        if new_price:
            # old_price_str = common.items_price_old.get(market_hash_name, {}).get('lowest_price', '')
            current_price_str = current_price.get('lowest_price', '')
            new_price_str = new_price.get('lowest_price', '')
            if current_price_str != new_price_str:
                common.items_price_old[market_hash_name] = current_price.copy()
            first_item['price'] = new_price
        first_item['time'] = datetime_now + datetime.timedelta(minutes=2)

    def update_history(self):
        _all_history: list[dict[str, datetime.datetime | dict | int | str]] = sqlite_manager.get_recent_history()
        all_history = [data for data in _all_history if str(data.get('app_id')) == str(common.app_id)]

        self.items_history_column.controls = []

        # Проверка, есть ли хотя бы одна запись в истории
        if not all_history or len(all_history) < 2:
            self.items_history_column.controls.append(ft.Text("История пока недоступна"))
            return

        # Инициализируем new_history первой записью для начала сравнения
        new_history = all_history[0]

        # Итерация по всей истории, начиная со второй записи
        for history in all_history[1:50]:
            new_time_updated = new_history.get('time_update', datetime.datetime.min)
            new_items = new_history.get('items', {})

            old_time_updated = history.get('time_update', datetime.datetime.min)
            old_items = history.get('items', {})

            # Обновление new_history текущей записью для следующего сравнения
            new_history = history.copy()

            change_list = self.compare_item_lists(old_items, new_items)
            if not change_list: continue

            column_item = ft.Column(spacing=1)

            time_widget = ft.Text(f'{new_time_updated}', size=12, text_align=ft.TextAlign.CENTER, expand=True)
            time_widget_container = ft.Container(width=200, content=time_widget)
            column_item.controls.append(time_widget_container)

            self.items_history_column.controls.append(column_item)

            total_price = 0
            total_count = 0
            for item in change_list:
                row_item_info = ft.Row(spacing=1)

                item_img_url = f'https://community.akamai.steamstatic.com/economy/image/{item.get("icon_url", "")}/330x192?allow_animated=1'
                item_img_widget = ft.Container(width=33, height=19, content=ft.Image(src=item_img_url, width=33, height=19))

                item_name = item.get("name", " ")
                item_color = item.get('name_color')
                item_name_widget = ft.Text(f'{item_name}', color=f'#{item_color}' if item_color else '', size=12, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
                item_name_widget_container = ft.Container(width=70, content=item_name_widget)

                item_change_count = item.get('count', 0)
                total_count += item_change_count
                item_change_count_text = f'+{item_change_count} шт.' if item_change_count > 0 else f'{item_change_count} шт.'
                item_change_count_color = ft.colors.GREEN if item_change_count > 0 else ft.colors.RED
                item_change_count_widget = ft.Text(item_change_count_text, color=item_change_count_color, size=12, max_lines=1,
                                                   overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.RIGHT)
                item_change_count_widget_container = ft.Container(width=50, content=item_change_count_widget)

                item_price_info = self.get_price(item.get('market_hash_name', ''))
                item_price_total_int, item_price_total_str = self.calculate_total_price(item_price_info, item_change_count)
                total_price += item_price_total_int
                item_price_text = f'+{item_price_total_str}' if item_price_total_int > 0 else f'{item_price_total_str}'
                item_price_color = ft.colors.GREEN if item_price_total_int > 0 else ft.colors.RED
                item_price_widget = ft.Text(item_price_text, color=item_price_color, size=12, max_lines=1,
                                            overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.RIGHT)
                item_price_widget_container = ft.Container(width=70, content=item_price_widget)

                clear_container = ft.Container(width=20, content=ft.Text(' '))

                row_item_info.controls = [item_img_widget, item_name_widget_container, item_change_count_widget_container, item_price_widget_container, clear_container]
                column_item.controls.append(row_item_info)


            row_total_info = ft.Row(spacing=1)
            total_name_widget = ft.Text("Всего", size=12, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                                        expand=True, text_align=ft.TextAlign.RIGHT)
            total_name_widget_container = ft.Container(width=103, content=total_name_widget)

            total_change_count_text = f'+{total_count} шт.' if total_count > 0 else f'{total_count} шт.'
            total_change_count_color = ft.colors.GREEN if total_count > 0 else ft.colors.RED
            total_change_count_widget = ft.Text(total_change_count_text, color=total_change_count_color, size=12, max_lines=1,
                                                overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.RIGHT)
            total_change_count_widget_container = ft.Container(width=50, content=total_change_count_widget)

            total_price = round(total_price, 2)
            total_price_text = f'+{common.prefix_currency}{total_price} {common.suffix_currency}' if total_price > 0 else f'{common.prefix_currency}{total_price} {common.suffix_currency}'
            total_price_color = ft.colors.GREEN if total_price > 0 else ft.colors.RED
            total_price_widget = ft.Text(total_price_text, color=total_price_color, size=12, max_lines=1,
                                         overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.RIGHT)
            total_price_widget_container = ft.Container(width=70, content=total_price_widget)

            clear_container = ft.Container(width=20, content=ft.Text(' '))

            row_total_info.controls = [total_name_widget_container, total_change_count_widget_container, total_price_widget_container, clear_container]
            column_item.controls.insert(1, row_total_info)

    def update_datagram(self):
        self.items_price_column.controls = []
        _all_history: list[dict[str, datetime | dict]] = sqlite_manager.get_recent_history()
        all_history = [data for data in _all_history if str(data.get('app_id')) == str(common.app_id)]

        current_time = datetime.datetime.now()  # Вычисляем текущее время один раз
        day_datetime = current_time - datetime.timedelta(days=1)
        hour_datetime = current_time - datetime.timedelta(hours=1)

        # Фильтрация истории за последний день
        day_history = [history for history in all_history if history.get('time_update', datetime.datetime.min) > day_datetime]

        # Фильтрация истории за последний час
        hour_history = [history for history in all_history if history.get('time_update', datetime.datetime.min) > hour_datetime]

        now_history = max(all_history, key=lambda x: x['time_update'], default={})
        earliest_day_history = min(day_history, key=lambda x: x['time_update'], default={})
        earliest_hour_history = min(hour_history, key=lambda x: x['time_update'], default={})

        __day_change_history = self.compare_item_lists(earliest_day_history.get('items', {}), now_history.get('items', {}))
        __hour_change_history = self.compare_item_lists(earliest_hour_history.get('items', {}), now_history.get('items', {}))
        day_change_history = {item['market_hash_name']: item for item in __day_change_history}
        hour_change_history = {item['market_hash_name']: item for item in __hour_change_history}

        row_item_info = ft.Row(spacing=1)

        name_widget = ft.Text(f'Предмет', size=18, max_lines=1,
                              overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
        name_widget_container = ft.Container(width=200, content=name_widget)

        total_widget = ft.Text(f'В инвентаре', size=18, max_lines=1,
                               overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
        total_widget_container = ft.Container(width=200, content=total_widget)

        day_change_widget = ft.Text(f'Изменения за день', size=18, max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
        day_change_widget_container = ft.Container(width=200, content=day_change_widget)

        hour_change_widget = ft.Text(f'Изменения за час', size=18, max_lines=1,
                                     overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
        hour_change_widget_container = ft.Container(width=200, content=hour_change_widget)

        price_widget = ft.Text(f'Цена за штуку', size=18, max_lines=1,
                               overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
        price_widget_container = ft.Container(width=200, content=price_widget)

        sell_widget_container = ft.Container(width=50, content=ft.Text(' '))

        clear_container = ft.Container(width=20, content=ft.Text(' '))

        row_item_info.controls = [
            name_widget_container, total_widget_container,
            day_change_widget_container, hour_change_widget_container,
            price_widget_container, sell_widget_container,
            clear_container]
        self.items_price_column.controls.append(row_item_info)

        total_count = 0
        total_price = 0
        day_count = 0
        day_price = 0
        hour_count = 0
        hour_price = 0

        item_time_updated = now_history.get('time_update', datetime.datetime.min)
        item_data = now_history.get('items', {})
        for item in item_data:
            item_info_control = ft.Container(ink=True, url=f'https://steamcommunity.com/market/listings/{common.app_id}/{item.get("market_hash_name", "")}')
            row_item_info = ft.Row(spacing=1, expand=True)
            item_info_control.content = row_item_info
            item_info_control.margin = 0
            item_info_control.padding = 0

            item_img_url = f'https://community.akamai.steamstatic.com/economy/image/{item.get("icon_url", "")}/330x192?allow_animated=1'
            item_img_widget = ft.Container(width=50, height=29, content=ft.Image(src=item_img_url, width=50, height=29))

            item_name = item.get("name", " ")
            item_color = item.get('name_color')
            item_name_widget = ft.Text(f'{item_name}', color=f'#{item_color}' if item_color else '', size=15, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
            item_name_widget_container = ft.Container(width=150, content=item_name_widget)

            total_item_count = item.get('count', 0)
            total_count += total_item_count
            total_item_count_text = f'{total_item_count} шт.'
            total_item_count_color = ft.colors.GREEN if total_item_count >= 0 else ft.colors.RED
            total_item_count_widget = ft.Text(total_item_count_text, color=total_item_count_color, size=15, max_lines=1,
                                              overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
            total_item_count_widget_container = ft.Container(width=100, content=total_item_count_widget)

            total_item_info = self.get_price(item.get('market_hash_name', ''))
            total_item_total_int, total_item_total_str = self.calculate_total_price(total_item_info, total_item_count)
            total_price += total_item_total_int
            total_item_text = f'{total_item_total_str}'
            total_item_color = ft.colors.GREEN if total_item_total_int >= 0 else ft.colors.RED
            total_item_widget = ft.Text(total_item_text, color=total_item_color, size=15, max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
            total_item_widget_container = ft.Container(width=100, content=total_item_widget)


            day_change_item = day_change_history.get(item.get('market_hash_name', ''), {})
            day_change_count = day_change_item.get('count', 0)
            day_count += day_change_count
            day_change_count_text = (f'+{day_change_count} шт.' if day_change_count > 0 else f'{day_change_count} шт.') if day_change_count != 0 else ' '
            day_change_count_color = ft.colors.GREEN if day_change_count >= 0 else ft.colors.RED
            day_change_count_widget = ft.Text(day_change_count_text, color=day_change_count_color, size=15, max_lines=1,
                                              overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
            day_change_count_widget_container = ft.Container(width=100, content=day_change_count_widget)

            day_change_item_total_int, day_change_item_total_str = self.calculate_total_price(total_item_info, day_change_count)
            day_price += day_change_item_total_int
            day_change_item_text = (f'+{day_change_item_total_str}' if day_change_count > 0 else f'{day_change_item_total_str}') if day_change_count != 0 else ' '
            day_change_item_color = ft.colors.GREEN if day_change_item_total_int >= 0 else ft.colors.RED
            day_change_item_widget = ft.Text(day_change_item_text, color=day_change_item_color, size=15, max_lines=1,
                                             overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
            day_change_item_widget_container = ft.Container(width=100, content=day_change_item_widget)

            hour_change_item = hour_change_history.get(item.get('market_hash_name', ''), {})
            hour_change_count = hour_change_item.get('count', 0)
            hour_count += hour_change_count
            hour_change_count_text = (f'+{hour_change_count} шт.' if hour_change_count > 0 else f'{hour_change_count} шт.') if hour_change_count != 0 else ' '
            hour_change_count_color = ft.colors.GREEN if hour_change_count >= 0 else ft.colors.RED
            hour_change_count_widget = ft.Text(hour_change_count_text, color=hour_change_count_color, size=15, max_lines=1,
                                               overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
            hour_change_count_widget_container = ft.Container(width=100, content=hour_change_count_widget)

            hour_change_item_total_int, hour_change_item_total_str = self.calculate_total_price(total_item_info, hour_change_count)
            hour_price += hour_change_item_total_int
            hour_change_item_text = (f'+{hour_change_item_total_str}' if hour_change_count > 0 else f'{hour_change_item_total_str}') if hour_change_count != 0 else ' '
            hour_change_item_color = ft.colors.GREEN if hour_change_item_total_int >= 0 else ft.colors.RED
            hour_change_item_widget = ft.Text(hour_change_item_text, color=hour_change_item_color, size=15, max_lines=1,
                                              overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
            hour_change_item_widget_container = ft.Container(width=100, content=hour_change_item_widget)

            price_item_total_int, price_item_total_str = self.calculate_total_price(total_item_info, 1)
            old_price_item_total_int, old_price_item_total_str = self.calculate_total_price(common.items_price_old.get(item.get('market_hash_name', ''), {}), 1)
            price_str = f'{price_item_total_str}'
            price_color = ft.colors.GREEN
            price_tooltip = ''
            if old_price_item_total_int != 0:
                price_change = round(price_item_total_int-old_price_item_total_int, 2)
                price_str = f'{price_item_total_str}[{price_change}]'
                price_color = ft.colors.GREEN if price_change > 0 else ft.colors.RED if price_change < 0 else ft.colors.BLUE
                price_tooltip = f'{price_item_total_str} текущая цена\n{old_price_item_total_str} прошлая цена\n{price_change} изменение цены'
            price_item_widget = ft.Text(price_str, size=15, max_lines=1, color=price_color,
                                        overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER, tooltip=price_tooltip)
            price_item_widget_container = ft.Container(width=200, content=price_item_widget)

            sell_item_widget = ft.FilledButton('Продать', expand=True, height=20, disabled=not self.is_item_marketable(item.get('market_hash_name', '')))
            sell_item_widget.on_click = lambda e, _item=item: self.open_sell_item(item_data=_item)
            sell_item_widget_container = ft.Container(width=110, content=sell_item_widget)

            clear_container = ft.Container(width=20, content=ft.Text(' '))

            row_item_info.controls = [
                item_img_widget, item_name_widget_container,
                total_item_count_widget_container, total_item_widget_container,
                day_change_count_widget_container, day_change_item_widget_container,
                hour_change_count_widget_container, hour_change_item_widget_container,
                price_item_widget_container, sell_item_widget_container, clear_container
            ]
            self.items_price_column.controls.append(item_info_control)

        row_total_info = ft.Row(spacing=1)

        total_name_widget = ft.Text(f'Всего', size=15, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.RIGHT)
        total_name_widget_container = ft.Container(width=200, content=total_name_widget)

        total_item_count_text = f'{total_count} шт.'
        total_item_count_color = ft.colors.GREEN if total_count > 0 else ft.colors.RED if total_count < 0 else ft.colors.BLUE
        total_item_count_widget = ft.Text(total_item_count_text, color=total_item_count_color, size=15, max_lines=1,
                                          overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
        total_item_count_widget_container = ft.Container(width=100, content=total_item_count_widget)

        total_item_color = ft.colors.GREEN if total_price > 0 else ft.colors.RED if total_price < 0 else ft.colors.BLUE
        total_item_price_str = f'+{common.prefix_currency}{round(total_price, 2)} {common.suffix_currency}' if total_price > 0 else \
            f'{common.prefix_currency}{round(total_price, 2)} {common.suffix_currency}' if total_price == 0 else f'-{common.prefix_currency}{abs(round(total_price, 2))} {common.suffix_currency}'
        total_item_widget = ft.Text(total_item_price_str, color=total_item_color, size=15, max_lines=1,
                                    overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
        total_item_widget_container = ft.Container(width=100, content=total_item_widget)


        day_change_count_text = (f'+{day_count} шт.' if day_count > 0 else f'-{day_count} шт.') if day_count != 0 else ' '
        day_change_count_color = ft.colors.GREEN if day_count > 0 else ft.colors.RED if day_count < 0 else ft.colors.BLUE
        day_change_count_widget = ft.Text(day_change_count_text, color=day_change_count_color, size=15, max_lines=1,
                                          overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
        day_change_count_widget_container = ft.Container(width=100, content=day_change_count_widget)

        day_change_item_text = f'+{common.prefix_currency}{round(day_price, 2)} {common.suffix_currency}' if day_price > 0 else \
            f'{common.prefix_currency}{round(day_price, 2)} {common.suffix_currency}' if day_price == 0 else f'-{common.prefix_currency}{abs(round(day_price, 2))} {common.suffix_currency}'
        day_change_item_color = ft.colors.GREEN if day_price > 0 else ft.colors.RED if day_price < 0 else ft.colors.BLUE
        day_change_item_widget = ft.Text(day_change_item_text, color=day_change_item_color, size=15, max_lines=1,
                                         overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
        day_change_item_widget_container = ft.Container(width=100, content=day_change_item_widget)


        hour_change_count_text = (f'+{hour_count} шт.' if hour_count > 0 else f'-{hour_count} шт.') if hour_count != 0 else ' '
        hour_change_count_color = ft.colors.GREEN if hour_count > 0 else ft.colors.RED if hour_count < 0 else ft.colors.BLUE
        hour_change_count_widget = ft.Text(hour_change_count_text, color=hour_change_count_color, size=15, max_lines=1,
                                           overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
        hour_change_count_widget_container = ft.Container(width=100, content=hour_change_count_widget)

        hour_change_item_text = f'+{common.prefix_currency}{round(hour_price, 2)} {common.suffix_currency}' if hour_price > 0 else \
            f'{common.prefix_currency}{round(hour_price, 2)} {common.suffix_currency}' if hour_price == 0 else f'-{common.prefix_currency}{abs(round(hour_price, 2))} {common.suffix_currency}'

        hour_change_item_color = ft.colors.GREEN if hour_price > 0 else ft.colors.RED if hour_price < 0 else ft.colors.BLUE
        hour_change_item_widget = ft.Text(hour_change_item_text, color=hour_change_item_color, size=15, max_lines=1,
                                          overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
        hour_change_item_widget_container = ft.Container(width=100, content=hour_change_item_widget)


        price_item_widget = ft.Text(' ', size=15, max_lines=1, color=ft.colors.BLUE,
                                    overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
        price_item_widget_container = ft.Container(width=150, content=price_item_widget)

        clear_container = ft.Container(width=20, content=ft.Text(' '))

        self.page.title = f'Предметов: {total_count} шт. на {total_item_price_str}.'
        if day_count != 0:
            self.page.title = f'{self.page.title} За день {day_change_count_text} на {day_change_item_text}.'
        if hour_count != 0:
            self.page.title = f'{self.page.title} За час {hour_change_count_text} на {hour_change_item_text}.'

        row_total_info.controls = [
            total_name_widget_container,
            total_item_count_widget_container, total_item_widget_container,
            day_change_count_widget_container, day_change_item_widget_container,
            hour_change_count_widget_container, hour_change_item_widget_container,
            price_item_widget_container, clear_container
        ]
        self.items_price_column.controls.insert(1, row_total_info)
        self.items_price_column.controls.insert(2, ft.VerticalDivider(2))

    def update_widget(self):
        if common.dialog_is_open: return
        if not common.debug_test:
            self.update_items()
            self.update_items_price()
        self.update_history()
        self.update_datagram()

    def __update(self):
        while self.__is_run:
            try:
                self.update_widget()
                self.page.update()
            except:
                pass
            self.update()
            time.sleep(10)

class MainPage:
    def __init__(self):
        self.page: ft.Page = None
        self.login_page = LoginWidget()
        self.inventory_page = AccountWidget()

    def create_login_page(self, *args):
        self.page.clean()
        self.login_page._enter_button.on_click = self.on_login
        self.page.add(self.login_page)

    def create_inventory(self, *args):
        self.page.clean()
        self.page.add(self.inventory_page)

    def on_login(self, *args):
        saved_session = setting.session
        if saved_session:
            session: SteamWebSession = sqlite_manager.decrypt_data(saved_session)
            if session.is_session_alive():
                common.session = session
                logger.info('Ваша предыдущая сессия все еще активна. Продолжаем с ней.')
                self.login_page.warning_text.value = 'Ваша предыдущая сессия все еще активна. Продолжаем с ней.'
                self.create_inventory()
                return

        login = str(self.login_page._login.value)
        password = str(self.login_page._password.value)
        guard_code = str(self.login_page._2fa.value).upper()
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
            common.update_current_inventory()
            self.page.window_destroy()
            self.page.update()
            os.abort()

    def build(self, page: ft.Page):
        self.page: ft.Page = page
        self.page.title = 'Привет'
        self.page.window_prevent_close = True
        self.page.on_window_event = self.__on_window_event
        # self.page.window_always_on_top = True
        self.create_login_page()
        self.on_login()


main_page = MainPage()
ft.app(target=main_page.build)

os.abort()
