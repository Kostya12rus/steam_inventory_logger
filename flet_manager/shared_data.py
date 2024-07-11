import datetime
import re
import time
from enum import Enum

from sql_manager import sqlite_manager
from sql_manager.config import setting
from steam_utility.manager_steam_session import InventoryManager, SteamWebSession
from dateutil.parser import parse
from logger_utility.logger_config import logger


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
    Meh = 3065090
    Duck = 3057940
    Raspberry = 3048820
    Monkey = 3057390
    Poop = 1506810
    Honey_Peach_Clicker = 3056370

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
        self.session: SteamWebSession = None

        self.next_updated_inventory = datetime.datetime.min
        self.next_updated_item_price = datetime.datetime.min
        self.items_price = []
        self.items_price_old = {}

        self.dialog_is_open = False
        self.prefix_currency = setting.prefix_currency
        self.suffix_currency = setting.suffix_currency

        self.current_items_price = {}
        self.current_items_price_old = {}
        self.items_nameid: dict = setting.items_nameid.copy()
        self.load_prices_inventory()

        self.inventory_interval_update = 2

        self.__event_update_appid = []

        self.update_market_interval = 1
        self.next_updated_market_list = datetime.datetime.min
        self.market_list = []

    def update_current_inventory(self):
        __currency = str(self.default_currency)
        self.current_items_price[__currency] = self.items_price.copy()
        self.current_items_price_old[__currency] = self.items_price_old.copy()
        self.__save_prices()

    def set_current_inventory(self):
        __currency = str(self.default_currency)
        self.items_price = self.current_items_price.get(__currency, [])
        self.items_price_old = self.current_items_price_old.get(__currency, {})

    def get_current_appid_name(self) -> list:
        return next((game_name for game_name, app_id in self.games.items() if app_id == common.app_id), Games.EggSurprise.name)

    def get_current_currency_name(self) -> list:
        return next((currency for currency, currency_id in self.currencies.items() if currency_id == self.default_currency), Currency.USD.name)

    def set_appid(self, app_name: str):
        app_id = self.games.get(app_name, None)
        if app_id is None: return
        if self.app_id == app_id: return
        setting.app_id = app_id
        self.app_id = app_id
        self.next_updated_inventory = datetime.datetime.min
        for event in self.__event_update_appid:
            try:
                event()
            except:
                logger.exception('Exception while updating app id')

    def set_currencie(self, currencie: str):
        currencie_id = self.currencies.get(currencie, None)
        if currencie_id is None: return
        self.update_current_inventory()
        if self.currencies == currencie_id: return
        setting.default_currency = currencie_id
        self.default_currency = currencie_id
        self.set_current_inventory()

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

    def load_prices_inventory(self):
        self.current_items_price = self.__deserialize_dates(setting.current_items_price)
        self.current_items_price_old = self.__deserialize_dates(setting.current_items_price_old)
        self.set_current_inventory()

    def get_contextid_appid(self) -> int:
        for game_name, app_id in self.games.items():
            if app_id == self.app_id:
                return self.context_ids.get(game_name, 2)
        return 2

    def get_history_inventory(self):
        _all_history: list[dict[str, datetime.datetime | dict | int | str]] = sqlite_manager.get_recent_history()
        return [data for data in _all_history if str(data.get('app_id')) == str(self.app_id)]

    def calculate_total_price_item(self, data: dict, count: int) -> tuple:
        if not data or not count: return 0.00, f"{self.prefix_currency}0.00 {self.suffix_currency}"
        # Получаем строку с минимальной ценой
        lowest_price = data.get('lowest_price', f"{self.prefix_currency}0.00 {self.suffix_currency}")

        # Регулярное выражение для извлечения числовой части и символов валюты
        price_match = re.search(r"([^\d.,]*)(\d+[\.,]?\d*)\s*([^\d.,]*)", lowest_price)

        total_price = 0.00
        formatted_price = f"{self.prefix_currency}0.00 {self.suffix_currency}"
        if price_match:
            # Извлекаем префикс валюты, число и суффикс валюты
            prefix_currency = price_match.group(1).strip()
            if self.prefix_currency != prefix_currency:
                self.prefix_currency = prefix_currency
                setting.price_currency = prefix_currency
            price_str = price_match.group(2)
            suffix_currency = price_match.group(3).strip()
            if self.suffix_currency != suffix_currency:
                self.suffix_currency = suffix_currency
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
        return total_price, formatted_price.strip()

    def get_inventory_price_item(self, market_hash_name: str):
        return next((item for item in self.items_price if item.get('market_hash_name') == market_hash_name), {}).get('price', {})
        # {'lowest_price': '0,13 pуб.', 'median_price': '0,35 pуб.', 'success': True, 'volume': '1,434,817'}

    def update_inventory(self):
        datetime_now = datetime.datetime.now()
        if self.next_updated_inventory > datetime_now: return
        inventory = self.session.get_inventory_items(appid=self.app_id, context_id=self.get_contextid_appid())
        self.next_updated_inventory = datetime_now + datetime.timedelta(seconds=30)
        if not inventory: return
        self.inventory = inventory
        self.next_updated_inventory = datetime_now + datetime.timedelta(minutes=self.inventory_interval_update)
        now_inventory = inventory.get_count_items()
        sqlite_manager.save_history(datetime_now, now_inventory, app_id=self.app_id)
        return now_inventory

    def update_items_price(self):
        datetime_now = datetime.datetime.now()
        if self.next_updated_item_price > datetime_now: return

        all_history = self.get_history_inventory()

        # Собираем уникальные market_hash_name из всех элементов в истории
        all_market_hash_name = {item.get('market_hash_name') for history in all_history for item in history.get('items', []) if item.get('market_hash_name')}

        existing_names = {item['market_hash_name'] for item in self.items_price}
        # Добавляем новые элементы, только если они отсутствуют в existing_names
        for name in all_market_hash_name:
            if name not in existing_names:
                self.items_price.append({'time': datetime.datetime.min, 'price': {}, 'market_hash_name': name})
        self.items_price.sort(key=lambda item: item['time'])

        if not self.items_price: return

        first_item = next((item for item in self.items_price if item['time'] < datetime_now and
                           item.get('market_hash_name', '') in all_market_hash_name and self.is_item_marketable(item.get('market_hash_name', ''))), None)
        if not first_item: return

        market_hash_name = first_item.get('market_hash_name', '')
        current_price = first_item.get('price', {})

        new_price = self.session.fetch_market_price(market_hash_name, appid=self.app_id, currency=self.default_currency)
        self.next_updated_item_price = datetime_now + (datetime.timedelta(seconds=10) if new_price else datetime.timedelta(seconds=30))
        logger.info(f"Загрузил цену для {market_hash_name}: {new_price}" if new_price else f"Неудалось загрузить цену для {market_hash_name}: {new_price}")
        if new_price:
            current_price_str = current_price.get('lowest_price', '')
            new_price_str = new_price.get('lowest_price', '')
            if current_price_str != new_price_str:
                self.items_price_old[market_hash_name] = current_price.copy()
            first_item['price'] = new_price
        first_item['time'] = datetime_now + datetime.timedelta(minutes=2)

    def is_item_tradable(self, market_hash_name: str):
        if not self.inventory or not self.inventory.inventory: return False
        items = self.inventory.inventory
        return any(
            bool(item.get('rgDescriptions', {}).get('tradable', False)) and
            item.get('rgDescriptions', {}).get('market_hash_name', '') == market_hash_name
            for item in items
        )

    def is_item_marketable(self, market_hash_name: str):
        if not self.inventory or not self.inventory.inventory: return False
        items = self.inventory.inventory
        return any(
            bool(item.get('rgDescriptions', {}).get('marketable', False)) and
            item.get('rgDescriptions', {}).get('market_hash_name', '') == market_hash_name
            for item in items
        )

    def update_market_list(self):
        datetime_now = datetime.datetime.now()
        if self.next_updated_market_list > datetime_now: return
        market_list = self.session.get_game_market_list(appid=self.app_id)
        # print(market_list)
        if not market_list: return
        self.market_list = market_list
        self.next_updated_market_list = datetime_now + datetime.timedelta(minutes=self.update_market_interval)
        sqlite_manager.save_market_history(datetime_now, market_list, app_id=self.app_id)
        return self.market_list

    def get_history_market_list(self):
        _all_history: list[dict[str, datetime.datetime | dict | int | str]] = sqlite_manager.get_recent_market_history()
        return [data for data in _all_history if str(data.get('app_id')) == str(self.app_id)]



common = SharedClass()
