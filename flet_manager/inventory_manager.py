import datetime
import re
import threading
import time

from flet_manager import common
import flet as ft

from sql_manager.config import setting


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
        self.count_item_sell_center = ft.FilledButton('50%', on_click=lambda e, _count=self.item_count: self.set_count_sell(count=_count * 0.5))
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
            status = common.session.fetch_sellitem(appid=int(common.app_id), assetid=int(item_id), amount=int(amount), price=button_price_get, contextid=common.get_contextid_appid())
            self.log_column.controls.insert(0, ft.Text(f'{status}'))
            time.sleep(0.1)
        self.log_column.controls.insert(0, ft.Text(f'Готово, выставил {int(self.count_item_sell.value if self.count_item_sell.value else 0)}'))

    def update_total(self, *args):
        button_price_sell = float(self.button_price_sell.value if self.button_price_sell.value else 0)
        button_price_get = float(self.button_price_get.value if self.button_price_get.value else 0)
        count_item_sell = int(self.count_item_sell.value if self.count_item_sell.value else 0)

        self.button_total_price_sell.value = f'{round(button_price_sell * count_item_sell, 2)}'
        self.button_total_price_sell.update()

        self.button_total_price_get.value = f'{round(button_price_get * count_item_sell, 2)}'
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
            item_img_widget = ft.Container(width=50 * 1.2, height=29 * 1.2, content=ft.Image(src=item_img_url, width=50 * 1.2, height=29 * 1.2))
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


class InventoryWidget(ft.Row):
    def __init__(self):
        super().__init__()
        self.__is_run = False
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

        self.drop_down_currencies = ft.Dropdown(
            on_change=self.__on_change_currencies,
            options=[ft.dropdown.Option(currency) for currency, currency_id in common.currencies.items()],
            height=30,
            width=100,
            text_size=14,
            dense=True,
            label='Валюта',
            content_padding=10,
            value=common.get_current_currency_name()
        )

        self.test_button = ft.FilledButton('test', on_click=self.test)

        self.price_column.controls.append(ft.Row([
            self.price_column_title, self.drop_down_currencies,
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
        market = common.session.get_game_market_list(appid=common.app_id)
        print()
        # inventory = common.session.get_inventory_items(appid=common.app_id, context_id=common.get_context_id())
        # print()
        # if not inventory:
        #     print("inventory не загружен")
        #     return
        # tradable_inventory = inventory.get_tradable_inventory()
        # if not tradable_inventory:
        #     print("tradable_inventory не загружен")
        #     return
        # # tradable_url = 'https://steamcommunity.com/tradeoffer/new/?partner=341988637&token=GLFg2wq2'
        # tradable_url = None
        # if not tradable_url:
        #     print("tradable_url не загружен")
        #     return
        # status = False
        # # status = common.session.trade_send(trade_url=tradable_url, items=tradable_inventory)
        # print(status)

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

    def open_sell_item(self, *args, item_data=None):
        if not item_data: return
        dialog = DialogSell(item_data)
        self.page.dialog = dialog
        dialog.open = True
        common.dialog_is_open = True
        self.page.update()


    @staticmethod
    def calculate_count_change(old_item: dict, new_item: dict) -> int:
        old_count = old_item.get('count', 0)
        new_count = new_item.get('count', 0)
        return new_count - old_count

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

    def update_history(self):
        all_history = common.get_history_inventory()

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

                item_price_info = common.get_inventory_price_item(item.get('market_hash_name', ''))
                item_price_total_int, item_price_total_str = common.calculate_total_price_item(item_price_info, item_change_count)
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
        all_history = common.get_history_inventory()

        current_time = datetime.datetime.now()
        day_datetime = current_time - datetime.timedelta(days=1)
        hour_datetime = current_time - datetime.timedelta(hours=1)

        day_history = [history for history in all_history if history.get('time_update', datetime.datetime.min) > day_datetime]
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

            total_item_info = common.get_inventory_price_item(item.get('market_hash_name', ''))
            total_item_total_int, total_item_total_str = common.calculate_total_price_item(total_item_info, total_item_count)
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

            day_change_item_total_int, day_change_item_total_str = common.calculate_total_price_item(total_item_info, day_change_count)
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

            hour_change_item_total_int, hour_change_item_total_str = common.calculate_total_price_item(total_item_info, hour_change_count)
            hour_price += hour_change_item_total_int
            hour_change_item_text = (f'+{hour_change_item_total_str}' if hour_change_count > 0 else f'{hour_change_item_total_str}') if hour_change_count != 0 else ' '
            hour_change_item_color = ft.colors.GREEN if hour_change_item_total_int >= 0 else ft.colors.RED
            hour_change_item_widget = ft.Text(hour_change_item_text, color=hour_change_item_color, size=15, max_lines=1,
                                              overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER)
            hour_change_item_widget_container = ft.Container(width=100, content=hour_change_item_widget)

            price_item_total_int, price_item_total_str = common.calculate_total_price_item(total_item_info, 1)
            old_price_item_total_int, old_price_item_total_str = common.calculate_total_price_item(common.items_price_old.get(item.get('market_hash_name', ''), {}), 1)
            price_str = f'{price_item_total_str}'
            price_color = ft.colors.GREEN
            price_tooltip = ''
            if old_price_item_total_int != 0:
                price_change = round(price_item_total_int - old_price_item_total_int, 2)
                price_str = f'{price_item_total_str}[{price_change}]'
                price_color = ft.colors.GREEN if price_change > 0 else ft.colors.RED if price_change < 0 else ft.colors.BLUE
                price_tooltip = f'{price_item_total_str} текущая цена\n{old_price_item_total_str} прошлая цена\n{price_change} изменение цены'
            price_item_widget = ft.Text(price_str, size=15, max_lines=1, color=price_color,
                                        overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.CENTER, tooltip=price_tooltip)
            price_item_widget_container = ft.Container(width=200, content=price_item_widget)

            sell_item_widget = ft.FilledButton('Продать', expand=True, height=20, disabled=not common.is_item_marketable(item.get('market_hash_name', '')))
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
            common.update_inventory()
            common.update_items_price()
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
