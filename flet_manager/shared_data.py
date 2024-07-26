import re
import io
import os
import json
import shutil
import pathlib
import zipfile
import requests
import datetime

import flet as ft
from enum import Enum

from dateutil.parser import parse
from sql_manager import sqlite_manager
from sql_manager.config import setting
from logger_utility.logger_config import logger
from steam_utility.manager_steam_session import InventoryManager, SteamWebSession


class Games(Enum):
    EggSurprise = 3017120
    Banana = 2923300
    Monsters = 3062260

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

        self.inventory_interval_update = 10

        self.__event_update_appid = []

        self.update_market_interval = 10
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

    def get_current_appid_name(self, find_appid: int = None) -> str:
        if not find_appid: find_appid = common.app_id
        return next((game_name for game_name, app_id in self.games.items() if app_id == find_appid), Games.EggSurprise.name)

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
        price_match = re.search(r"([^\d.,]*)(\d{1,3}(?:[\s.,]\d{3})*(?:[\.,]\d*)?)\s*([^\d.,]*)", lowest_price)

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
            price_str = price_str.replace(',', '.').replace(' ', '')

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
        now_inventory = inventory.get_count_items()
        sqlite_manager.save_history(datetime_now, now_inventory, app_id=self.app_id)
        return self.inventory

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
        self.next_updated_market_list = datetime_now + datetime.timedelta(seconds=self.update_market_interval)
        if not market_list: return
        self.market_list = market_list
        sqlite_manager.save_market_history(datetime_now, market_list, app_id=self.app_id)
        return self.market_list

    def get_history_market_list(self):
        _all_history: list[dict[str, datetime.datetime | dict | int | str]] = sqlite_manager.get_recent_market_history()
        return [data for data in _all_history if str(data.get('app_id')) == str(self.app_id)]

common = SharedClass()


class InventoryItemDescription:
    def __init__(self, description_dict: dict = None):
        if not description_dict: description_dict = {}
        self.type = description_dict.get('type', '')
        self.value = description_dict.get('value', '')
class InventoryItemTag:
    def __init__(self, tag_dict: dict = None):
        if not tag_dict: tag_dict = {}
        self.category = tag_dict.get('category', '')
        self.internal_name = tag_dict.get('internal_name', '')
        self.category_name = tag_dict.get('category_name', '')
        self.name = tag_dict.get('name', '')
class InventoryItemRgDescriptions:
    def __init__(self, rg_dict: dict = None):
        if not rg_dict: rg_dict = {}
        self.appid = rg_dict.get('appid', '')
        self.classid = rg_dict.get('classid', '')
        self.instanceid = rg_dict.get('instanceid', '')
        self.icon_url = rg_dict.get('icon_url', '')
        self.icon_url_large = rg_dict.get('icon_url_large', '')
        self.icon_drag_url = rg_dict.get('icon_drag_url', '')
        self.name = rg_dict.get('name', '')
        self.market_hash_name = rg_dict.get('market_hash_name', '')
        self.market_name = rg_dict.get('market_name', '')
        self.name_color = rg_dict.get('name_color', '')
        self.background_color = rg_dict.get('background_color', '')
        self.type = rg_dict.get('type', '')
        self.tradable = rg_dict.get('tradable', 0)
        self.marketable = rg_dict.get('marketable', 0)
        self.commodity = rg_dict.get('commodity', 0)
        self.market_tradable_restriction = rg_dict.get('market_tradable_restriction', '')
        self.market_marketable_restriction = rg_dict.get('market_marketable_restriction', '')
        self.cache_expiration = rg_dict.get('cache_expiration', '')
        self.descriptions = [InventoryItemDescription(d) for d in rg_dict.get('descriptions', [])]
        self.owner_descriptions = [InventoryItemDescription(d) for d in rg_dict.get('owner_descriptions', [])]
        self.tags = [InventoryItemTag(t) for t in rg_dict.get('tags', [])]
class InventoryItem:
    def __init__(self, item_dict: dict = None):
        if not item_dict: item_dict = {}
        self.id = item_dict.get('id', '')
        self.classid = item_dict.get('classid', '')
        self.instanceid = item_dict.get('instanceid', '')
        self.amount = item_dict.get('amount', '0')
        self.hide_in_china = item_dict.get('hide_in_china', 0)
        self.pos = item_dict.get('pos', 0)
        self.rg_descriptions = InventoryItemRgDescriptions(item_dict.get('rgDescriptions', {}))

    def __extract_date_from_owner_descriptions(self):
        if not self.rg_descriptions.owner_descriptions: return None
        date_pattern = re.compile(r'\[date\](\d+)\[/date\]')
        for desc in self.rg_descriptions.owner_descriptions:
            match = date_pattern.search(desc.value)
            if match:
                timestamp = int(match.group(1))
                return datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
        return None
    def name(self):
        return self.rg_descriptions.name
    def market_hash_name(self):
        return self.rg_descriptions.market_hash_name
    def color(self):
        return f'#{self.rg_descriptions.name_color}' if self.rg_descriptions.name_color else ''
    def get_amount(self):
        amount = int(self.amount)
        return amount if amount > 0 else 0
    def market_url(self) -> str:
        if not self.rg_descriptions.market_hash_name: return
        return f'https://steamcommunity.com/market/listings/{self.rg_descriptions.appid}/{self.rg_descriptions.market_hash_name}'
    def icon_url(self) -> str:
        if not self.rg_descriptions.icon_url: return None
        return f'https://community.akamai.steamstatic.com/economy/image/{self.rg_descriptions.icon_url}/330x192?allow_animated=1'
    def end_ban_marketable(self):
        return self.__extract_date_from_owner_descriptions()
    def is_tradable(self):
        return bool(self.rg_descriptions.tradable)
    def is_marketable(self):
        return bool(self.rg_descriptions.marketable)

    def __repr__(self):
        return f'<{self.id}, classid: {self.classid}, instanceid: {self.instanceid}, name: {self.name()}, market_hash_name: {self.market_hash_name()}>'
    def __str__(self):
        return f'<{self.id}, classid: {self.classid}, instanceid: {self.instanceid}, name: {self.name()}, market_hash_name: {self.market_hash_name()}>'

class InventoryHistoryItem:
    def __init__(self, item_dict: dict = None, app_id: int = 0):
        if not item_dict: item_dict = {}
        self.app_id = app_id
        self.count = item_dict.get('count', 0)
        self.icon_url = item_dict.get('icon_url', None)
        self.name = item_dict.get('name', None)
        self.market_hash_name = item_dict.get('market_hash_name', None)
        self.name_color = item_dict.get('name_color', None)
    def get_color(self):
        if not self.name_color: return
        return f'#{self.name_color}' if self.name_color else None
    def market_url(self) -> str:
        if not self.market_hash_name: return
        return f'https://steamcommunity.com/market/listings/{self.app_id}/{self.market_hash_name}'
    def get_icon_url(self) -> str:
        if not self.icon_url: return None
        return f'https://community.akamai.steamstatic.com/economy/image/{self.icon_url}/330x192?allow_animated=1'
class InventoryHistory:
    def __init__(self, history_dict: dict = None):
        if not history_dict: history_dict = {}
        self.time_update = history_dict.get('time_update', datetime.datetime.min)
        self.app_id = history_dict.get('app_id', 0)
        self.items = [InventoryHistoryItem(i, self.app_id) for i in history_dict.get('items', [])]
    def get_list_market_hash_name(self, app_id: int | str = None) -> set:
        if not app_id: app_id = common.app_id
        if str(self.app_id) != str(app_id): return set()
        return {item.market_hash_name for item in self.items if item.market_hash_name}
    def get_item_from_market_hash_name(self, market_hash_name: str, app_id: int | str = None):
        if not app_id: app_id = common.app_id
        if str(self.app_id) != str(app_id): return InventoryHistoryItem({}, self.app_id)
        return next((i for i in self.items if i.market_hash_name == market_hash_name), InventoryHistoryItem({}, self.app_id))
    def get_item_count_from_market_hash_name(self, market_hash_name: str, app_id: int | str = None):
        if not app_id: app_id = common.app_id
        if str(self.app_id) != str(app_id): return 0
        return next((i.count for i in self.items if i.market_hash_name == market_hash_name), 0)
class InventoryAllHistory:
    def __init__(self):
        _all_history = common.get_history_inventory()
        self.list_history = [InventoryHistory(entry) for entry in _all_history]
    def get_latest_history(self):
        if not self.list_history: return InventoryHistory({})
        return max(self.list_history, key=lambda entry: entry.time_update)
    def get_previous_history(self):
        latest_history = self.get_latest_history()
        if not latest_history or not self.list_history: return InventoryHistory({})
        previous_histories = [entry for entry in self.list_history if entry.time_update != latest_history.time_update]
        if not previous_histories: return InventoryHistory({})
        return max(previous_histories, key=lambda entry: entry.time_update)
    def get_history_hours_ago(self, hours_ago: int = 1):
        time_threshold = datetime.datetime.now() - datetime.timedelta(hours=hours_ago)
        recent_history_entries = [entry for entry in self.list_history if entry.time_update >= time_threshold]
        if not recent_history_entries: return InventoryHistory({})
        return min(recent_history_entries, key=lambda entry: entry.time_update)


class MarketItemDelta:
    def __init__(self, now_item: 'MarketItem', old_item: 'MarketItem'):
        self.now_item = now_item
        self.old_item = old_item

        self.sell_listings = self.now_item.sell_listings - self.old_item.sell_listings
        self.sell_price = self.now_item.sell_price - self.old_item.sell_price
        self.sell_price_text = self.__generate_sell_price_text()

        self.sell_price_percent = self.__generate_sell_price_percent()
        self.sell_listings_percent = self.__generate_sell_listings_percent()

    def replace_number_in_currency(self, new_number):
        original_str = self.now_item.sell_price_text if self.now_item.sell_price_text else self.old_item.sell_price_text
        if not original_str: return str(new_number)
        return re.sub(r'\d{1,3}(?:\s?\d{3})*(?:[,.]\d+)?', new_number, str(original_str))
    def generate_number_in_currency(self, new_number):
        return self.replace_number_in_currency(f"{round(new_number / 100, 2):.2f}")
    def __generate_sell_price_text(self):
        return self.replace_number_in_currency(f"{round((self.now_item.sell_price - self.old_item.sell_price) / 100, 2):.2f}")
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
class MarketDescription:
    def __init__(self, description_dict: dict):
        self.type = description_dict.get('type')
        self.value = description_dict.get('value')
class MarketAssetDescription:
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
        self.descriptions = [MarketDescription(d) for d in asset_description_dict.get('descriptions', [])]
        self.type = asset_description_dict.get('type', "")
        self.background_color = asset_description_dict.get('background_color', "")
class MarketItem:
    def __init__(self, item_dict: dict = None):
        if not item_dict: item_dict = {}
        self.name = item_dict.get('name', ' ')
        self.hash_name = item_dict.get('hash_name', '')

        self.sell_listings = item_dict.get('sell_listings', 0)
        self.sell_price = item_dict.get('sell_price', 0)
        self.sell_price_text = item_dict.get('sell_price_text', '')
        self.sale_price_text = item_dict.get('sale_price_text', '')

        self.asset_description = MarketAssetDescription(item_dict.get('asset_description', {}))

        self.app_name = item_dict.get('app_name')
        self.app_icon = item_dict.get('app_icon')
    def __repr__(self):
        return f'<{self.__class__.__name__}> name: {self.name}, price: {self.sell_price_text}, listings: {self.sell_price}'

    def is_bug_item(self) -> bool:
        return self.hash_name != self.asset_description.market_hash_name
    def is_empty(self) -> bool:
        return self.hash_name == ''
    def icon_url(self) -> str:
        if not self.asset_description.icon_url: return
        return f'https://community.akamai.steamstatic.com/economy/image/{self.asset_description.icon_url}/330x192?allow_animated=1'
    def market_url(self) -> str:
        if not self.asset_description.appid or not self.asset_description.market_hash_name: return
        return f'https://steamcommunity.com/market/listings/{self.asset_description.appid}/{self.asset_description.market_hash_name}'
    def market_hash_name(self) -> str:
        return self.asset_description.market_hash_name
    def get_delta(self, old_item: 'MarketItem') -> 'MarketItemDelta':
        return MarketItemDelta(self, old_item)
    def color(self) -> str:
        return f'#{self.asset_description.name_color}' if self.asset_description.name_color else ''
    def is_current_game(self, app_id: int) -> bool:
        return str(self.asset_description.appid) == str(app_id)
    def replace_number_in_currency(self, new_number):
        return re.sub(r'\d{1,3}(?:\s?\d{3})*(?:[,.]\d+)?', new_number, self.sell_price_text)
    def generate_number_in_currency(self, new_number):
        return self.replace_number_in_currency(f"{round(new_number / 100, 2):.2f}")
    def multiply_price_in_currency(self, count: int):
        return self.generate_number_in_currency(self.sell_price * count)
    def calcutate_commision(self, price: int = None) -> str:
        if not price: price = self.sell_price
        commission = abs(price - (price / 115 * 100))
        price_after_commission = price - commission
        return self.generate_number_in_currency(price_after_commission)


class MarketHistory:
    def __init__(self, history_dict: dict):
        self.time_update = history_dict.get('time_update', datetime.datetime.min)
        self.items = [MarketItem(i) for i in history_dict.get('items', [])]

    def get_list_market_hash_name(self) -> set:
        return {item.market_hash_name() for item in self.items if not item.is_bug_item() and item.is_current_game(common.app_id)}
    def get_item_from_market_hash_name(self, market_hash_name: str) -> MarketItem:
        return next((i for i in self.items if not i.is_bug_item() and i.market_hash_name() == market_hash_name and i.is_current_game(common.app_id)), MarketItem())
class MarketAllHistory:
    def __init__(self):
        _all_history = common.get_history_market_list()
        self.list_history = [MarketHistory(entry) for entry in _all_history]
    def get_latest_history(self):
        if not self.list_history: return MarketHistory({})
        return max(self.list_history, key=lambda entry: entry.time_update)
    def get_previous_history(self):
        latest_history = self.get_latest_history()
        if not latest_history or not self.list_history: return MarketHistory({})
        previous_histories = [entry for entry in self.list_history if entry.time_update != latest_history.time_update]
        if not previous_histories: return MarketHistory({})
        return max(previous_histories, key=lambda entry: entry.time_update)
    def get_history_hours_ago(self, hours_ago: int = 1):
        time_threshold = datetime.datetime.now() - datetime.timedelta(hours=hours_ago)
        recent_history_entries = [entry for entry in self.list_history if entry.time_update >= time_threshold]
        if not recent_history_entries: return MarketHistory({})
        return min(recent_history_entries, key=lambda entry: entry.time_update)


class UpdateManager:
    def __init__(self):
        self.last_check_version = datetime.datetime.min
        self.ignore_update = False

        self.installed_version = setting.installed_version
        self.accept_update = bool(setting.accept_update)

        self.url_server = "https://raw.githubusercontent.com/Kostya12rus/steam_inventory_logger/main/version.json"
        self.server_version = None
        self.server_url_download = None
        self.server_changes = None

        self.file_version = None
        self.file_url_download = None
        self.file_changes = None

    def change_accept_update(self, accept_update: bool):
        if accept_update is None: return
        setting.accept_update = accept_update
        self.accept_update = accept_update
    def change_installed_version(self, installed_version: float = None):
        if installed_version is None: return
        setting.installed_version = installed_version
        self.installed_version = installed_version

    def is_first_run(self):
        if not self.accept_update: return False
        return self.installed_version == 0
    def is_installed_latest_version(self):
        if not self.accept_update: return True
        if not self.server_version: return True
        return self.installed_version == self.server_version or self.file_version == self.server_version

    def load_server_version(self):
        response = requests.get(self.url_server, timeout=10)
        if not response.ok: return
        json_response: dict = response.json()
        if not json_response: return
        self.server_version = json_response.get('version', None)
        self.server_url_download = json_response.get('url_download', None)
        self.server_changes = json_response.get('changes', None)
        return True
    def load_file_version(self):
        version_path = pathlib.Path('version.json')
        if not version_path.is_file(): return
        with open(version_path) as file:
            json_file: dict = json.load(file)
        if not json_file: return
        self.file_version = json_file.get('version', None)
        self.file_url_download = json_file.get('url_download', None)
        self.file_changes = json_file.get('changes', None)
        return True

    def download_and_extract_github_zip(self, extract_to='.'):
        print(self.server_url_download)
        if not self.server_url_download:
            return False

        response = requests.get(self.server_url_download, timeout=10)
        print(response)
        print(response.ok)
        if not response.ok:
            return False

        with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
            temp_dir = os.path.join(extract_to, 'temp_extraction')
            zip_ref.extractall(temp_dir)

        project_folder = zip_ref.namelist()[0].split('/')[0]
        print(f'{project_folder=}')
        project_path = os.path.join(temp_dir, project_folder)
        print(f'{project_path=}')

        for item in os.listdir(project_path):
            src = os.path.join(project_path, item)
            dst = os.path.join(extract_to, item)
            if os.path.exists(dst):
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                else:
                    os.remove(dst)
            shutil.move(src, extract_to)

        shutil.rmtree(temp_dir)
        return True
