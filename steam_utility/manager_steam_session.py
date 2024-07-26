import json, re, time
import urllib.parse

from requests import Session
from steam_utility import WebSteam
from logger_utility.logger_config import logger


def token_parse(url):
    partner, partner_token = None, None
    if not url:
        return partner, partner_token
    temp = re.findall("partner=[0-9]+", url)
    if len(temp) > 0:
        partner = int(str(temp[0]).replace("partner=", "")) + 76561197960265728
    temp = re.findall("token=.*", url)
    if len(temp) > 0:
        partner_token = str(temp[0]).replace("token=", "")
    return partner, partner_token

class InventoryManager:
    def __init__(self, items: dict, context_id=2):
        self.data_json = items
        self.rgDescriptions: dict = items.get('rgDescriptions', {})
        if not isinstance(self.rgDescriptions, dict):
            self.rgDescriptions: dict = {}
        self.rgInventory: dict = items.get('rgInventory', {})
        if not isinstance(self.rgInventory, dict):
            self.rgInventory: dict = {}
        self.success: bool = items.get('success', False)
        self.inventory: list = []
        self.context_id = context_id
        self.parse_inventory()

    def parse_inventory(self):
        self.inventory: list = []
        for key, item in self.rgInventory.items():
            self.inventory.append(item)
        for item in self.inventory:
            classid = item.get('classid', 0)
            if classid == 0: continue
            instanceid = item.get('instanceid', 0)
            for key, item_d in self.rgDescriptions.items():
                classid_d = item_d.get('classid', 0)
                if classid != classid_d: continue
                instanceid_d = item_d.get('instanceid', 0)
                if instanceid != instanceid_d: continue
                item['rgDescriptions'] = item_d
                break

    def is_has_rare(self):
        for item in self.inventory:
            tags = item.get('rgDescriptions', {}).get('tags', [])
            for tag in tags:
                if tag.get('category_name', '') == 'Rarity' and tag.get('name', '') != 'Common':
                    return True

    def is_has_common(self):
        for item in self.inventory:
            tags = item.get('rgDescriptions', {}).get('tags', [])
            for tag in tags:
                if tag.get('category_name', '') == 'Rarity' and tag.get('name', '') == 'Common':
                    return True

    def is_has_rare_and_common(self):
        for item in self.inventory:
            tags = item.get('rgDescriptions', {}).get('tradable', [])
            for tag in tags:
                if tag.get('category_name', '') == 'Rarity' and tag.get('name', '') == 'Rare':
                    return True

    def is_can_trade(self):
        for item in self.inventory:
            tradable = item.get('rgDescriptions', {}).get('tradable', 0)
            if tradable:
                return True

    def get_tradable_inventory(self) -> list:
        if not self.success: return []
        return_data = []
        for item in self.inventory:
            tradable = item.get('rgDescriptions', {}).get('tradable', 0)
            if not tradable: continue
            appid = item.get('rgDescriptions', {}).get('appid', 0)
            assetid = item.get('id', 0)
            amount = item.get('amount', 1)
            return_data.append({'appid': appid, 'contextid': f'{self.context_id}', 'assetid': assetid, 'amount': amount})
        return return_data

    def add_next_invent(self, next_invent: 'InventoryManager'):
        if not isinstance(next_invent, InventoryManager): return
        for key, value in next_invent.rgInventory.items():
            self.rgInventory[key] = value
        for key, value in next_invent.rgDescriptions.items():
            self.rgDescriptions[key] = value
        self.parse_inventory()

    def get_count_items(self):
        items = {}
        if not self.inventory:
            self.parse_inventory()

        for item in self.inventory:
            classid = item.get('classid', '0')
            if classid not in items:
                items[classid] = {'count': 0, 'icon_url': '', 'name': '', 'market_hash_name': '', 'name_color': ''}

            items[classid]['count'] += int(item.get('amount', 1))
            rgDescriptions = item.get('rgDescriptions', {})

            # Обновляем информацию о товаре, если она еще не была записана
            if not items[classid]['icon_url']:
                items[classid]['icon_url'] = rgDescriptions.get('icon_url', '')
            if not items[classid]['name']:
                items[classid]['name'] = rgDescriptions.get('name', '')
            if not items[classid]['market_hash_name']:
                items[classid]['market_hash_name'] = rgDescriptions.get('market_hash_name', '')
            if not items[classid]['name_color']:
                items[classid]['name_color'] = rgDescriptions.get('name_color', '')

        # Создаем список из словарей и сортируем его по ключу 'count' в убывающем порядке
        sorted_items = sorted(items.values(), key=lambda x: x['count'], reverse=True)
        return sorted_items

class SteamWebSession:
    def __init__(self, login: str, password: str):
        self.login = login
        self.password = password
        self.steam_web = WebSteam(login, password)
        self.steam_session: Session = None
        self.marker_info = []

        self.full_inventory_data = {}
        self.profile_data = {}
        self.session_id = None

    def __is_session_alive(self, session: Session) -> bool:
        main_page_response = session.get('https://steamcommunity.com')
        return self.login.lower() in main_page_response.text.lower()

    def is_session_alive(self):
        if not self.steam_session: return False
        return self.__is_session_alive(self.steam_session)

    def login_steam(self, guard_code: str):
        logger.info(f"{self.login}: создаю сессию в Web Steam")
        self.steam_web = WebSteam(self.login, self.password)

        try:
            temp_session = self.steam_web.login(guard_code)
            is_session_alive = self.__is_session_alive(temp_session)
            if is_session_alive:
                logger.info(f"{self.login}: успешный вход в Web Steam")
                self.steam_session = temp_session
                return True
        except:
            logger.exception(f"{self.login}: ошибка входа в Web Steam")

    def get_inventory_items(self, appid=3017120, start=0, context_id=2):
        def_url = f'http://steamcommunity.com/profiles/{self.steam_web.steam_id}/inventory/json/{appid}/{context_id}/?start={start}'
        try:
            req = self.steam_session.get(url=def_url, timeout=10)
            if req.ok:
                req_json = req.json()
                if not req_json.get('success', False):
                    return None  # Если не удалось получить данные, возвращаем None

                inventory = InventoryManager(req_json, context_id=context_id)
                if req_json.get('more', False):
                    more_start = req_json.get('more_start', 0)
                    if isinstance(more_start, int) and more_start > 0:
                        next_inventory = self.get_inventory_items(appid=appid, start=more_start, context_id=context_id)
                        if next_inventory:
                            inventory.add_next_invent(next_inventory)
                self.full_inventory_data = inventory
                return inventory
        except Exception as e:
            logger.exception("Ошибка проверки инвентаря: %s", str(e))
        time.sleep(5)
        return None  # Возвращаем None, если произошла ошибка

    def fetch_market_price(self, market_hash_name: str, appid: int = 3017120, currency: int = 5) -> dict | None:
        url = f"https://steamcommunity.com/market/priceoverview/"
        params = {'country': 'RU', 'appid': appid, 'currency': currency, 'market_hash_name': market_hash_name}
        market_info = self.steam_session.get(f"{url}?{urllib.parse.urlencode(params)}", timeout=10)
        return market_info.json() if market_info.ok else None

    def fetch_market_itemordershistogram(self, country='KZ', language='russian', currency=37, item_nameid=None) -> dict | None:
        if not item_nameid: return {}
        url = f"https://steamcommunity.com/market/itemordershistogram"
        params = {'country': country, 'language': language, 'currency': currency, 'item_nameid': item_nameid}
        market_info = self.steam_session.get(f"{url}?{urllib.parse.urlencode(params)}", timeout=10)
        return market_info.json() if market_info.ok else None

    def get_session_id(self):
        if self.session_id: return self.session_id

        # Формирование корректного URL
        url = "https://steamcommunity.com/market/"

        try:
            # Используем requests для выполнения GET-запроса
            response = self.steam_session.get(url, timeout=10)
            if response.ok:
                # Использование регулярных выражений для поиска sessionID
                match = re.search(r'g_sessionID\s*=\s*"([^"]+)"', response.text)
                if match:
                    # Сохранение найденного sessionID
                    self.session_id = match.group(1)
                    return self.session_id
            return None
        except Exception as e:
            print(f"Error fetching session ID: {e}")
            return None

    def fetch_sellitem(self, appid: int = 3017120, contextid=2, assetid=0, amount=1, price=0) -> dict | None:
        sessionid = self.get_session_id()
        if not assetid or not sessionid: return None
        url = 'https://steamcommunity.com/market/sellitem/'
        params = {'sessionid': sessionid, 'appid': appid, 'contextid': contextid, 'assetid': assetid, 'amount': amount, 'price': price}
        headers = {
            "accept": "*/*",
            "accept-language": "ru,en;q=0.9",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "Referer": f"https://steamcommunity.com/profiles/{self.steam_web.steam_id}/inventory",  # Добавлено
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36"
        }
        market_info = self.steam_session.post(url=url, timeout=10, headers=headers, data=params)
        return market_info.json() if market_info.ok else None

    def fetch_item_nameid(self, market_hash_name: str, appid: int = 3017120) -> int | None:
        if not market_hash_name or not appid: return None

        # Кодирование market_hash_name для безопасной передачи в URL
        encoded_market_hash_name = urllib.parse.quote(market_hash_name)

        # Формирование корректного URL
        url = f"https://steamcommunity.com/market/listings/{appid}/{encoded_market_hash_name}"

        try:
            # Используем requests для выполнения GET-запроса
            response = self.steam_session.get(url, timeout=10)
            if response.ok:
                # Использование регулярных выражений для поиска числа
                _match = re.search(r'\bMarket_LoadOrderSpread\(\s*(\d+)\s*\);', response.text)
                if not _match:
                    match = re.search(r'\bItemActivityTicker\.Start\(\s*(\d+)\s*\);', response.text)
                if _match:
                    item_nameid = int(_match.group(1))
                    return item_nameid
            return None
        except Exception as e:
            print(f"Error fetching market item ID: {e}")
            return None

    @staticmethod
    def get_assets_list(items_data: list):
        items_data = items_data or []
        if len(items_data) > 0:
            return {
                'newversion': True,
                'version': 4,
                'me': {
                    'assets': items_data,
                    'currency': [],
                    'ready': False
                },
                'them': {
                    'assets': [],
                    'currency': [],
                    'ready': False
                }
            }

    def trade_send(self, trade_url: str, items: list):
        if not self.steam_session: return
        partner, partner_token = token_parse(trade_url)
        if not partner or not partner_token: return False
        # self.load_send_trade()
        text_steam_send = ""
        session_id = self.steam_session.cookies.get('sessionid', domain='steamcommunity.com')
        for i in range(2):
            try:
                if not items:
                    logger.info(f"Обмен не отправлен, не найдены идентификаторы вещей")
                    return
                url = 'https://steamcommunity.com/tradeoffer/new/send'
                headers = {'Referer': "https://steamcommunity.com/tradeoffer/new",
                           'Origin': "https://steamcommunity.com"}
                params = {
                    'sessionid': session_id,
                    'serverid': 1,
                    'partner': partner,
                    'tradeoffermessage': '',
                    'json_tradeoffer': json.dumps(self.get_assets_list(items)),
                    'captcha': '',
                    'trade_offer_create_params': json.dumps({'trade_offer_access_token': partner_token})
                }
                respons = self.steam_session.post(url, data=params, headers=headers, timeout=10)
                if respons.ok:
                    text_json: dict = json.loads(respons.text)
                    print(text_json)
                    return True
                else:
                    text_steam_send = f"{respons.status_code}\n{respons.text}\n"
            except Exception:
                logger.exception("trade_send ERROR")
            time.sleep(5)
        if len(text_steam_send) > 1:
            logger.info(f"Обмен не отправлен, Steam ответил: {text_steam_send}")
            return

    def get_game_market_list(self, appid: int = 3017120, start: int = 0, count: int = 100) -> list:
        """
        Получает список товаров на игровом рынке Steam.

        :param appid: ID приложения в Steam.
        :param start: Начальный индекс списка товаров.
        :param count: Количество возвращаемых товаров.
        :return: Список товаров на рынке.
        """
        search_params = {
            'start': start,
            'count': count,
            'search_descriptions': 0,
            'sort_column': 'popular',
            'sort_dir': 'desc',
            'appid': appid,
            'norender': 1,
        }
        search_url = "https://steamcommunity.com/market/search/render/"
        market_items = []
        max_attempts = 2

        for attempt in range(max_attempts):
            try:
                market_response = self.steam_session.get(search_url, params=search_params, timeout=10)
                if market_response.ok:
                    response_data = market_response.json()
                    if response_data.get('success', False):
                        market_items.extend(response_data.get('results', []))
                        total_items_available = response_data.get('total_count', 0)
                        if total_items_available > start + count:
                            start += count
                            market_items.extend(self.get_game_market_list(appid, start, count))
                        return market_items
            except Exception as e:
                pass
            time.sleep(5)

        return market_items

    def get_steam_token(self):
        try:
            response = self.steam_session.get('https://steamcommunity.com/my/', timeout=10)

            token_pattern = re.compile(r'loyalty_webapi_token\s*=\s*"([^"]+)"')
            match = token_pattern.search(response.text)

            if match:
                token = match.group(1).replace('&quot;', '')
                return token
            else:
                return None

        except:
            return None

    def stack_items(self, appid, fromitemid, destitemid, quantity, access_token):
        try:
            url = 'https://api.steampowered.com/IInventoryService/CombineItemStacks/v1/'
            data = {
                'access_token': access_token,
                'appid': appid,
                'fromitemid': fromitemid,
                'destitemid': destitemid,
                'quantity': quantity,
                'steamid': self.steam_web.steam_id,
            }
            response = self.steam_session.post(url, data=data, timeout=10)
            return response
        except:
            return None
