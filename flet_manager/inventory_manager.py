import datetime
import re
import threading
import time

from flet_manager import common, MarketAllHistory, InventoryAllHistory
import flet as ft

from flet_manager.shared_data import InventoryItem, MarketItem, InventoryHistoryItem
from sql_manager.config import setting
from logger_utility.logger_config import logger
from steam_utility.manager_steam_session import InventoryManager

def create_row(*texts):
    return ft.Row(
        expand=True,
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=0,
        controls=texts,
    )
def create_text(value, size=14, expand=True, text_align=ft.TextAlign.CENTER):
    return ft.Text(
        value=value,
        text_align=text_align,
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
        expand=expand,
        size=size,
    )


class DialogSell(ft.AlertDialog):
    def __init__(self, item_data: list[InventoryItem] = None):
        super().__init__()
        self.isolated = True
        self.expand = True
        self.item_id = None

        self.last_updated = datetime.datetime.now()
        self.item_data: InventoryItem = next((item for item in item_data if item.market_hash_name()), None)
        self.market_hash_name = next((item.market_hash_name() for item in item_data if item.market_hash_name()), None)
        self.all_item_in_inventary = item_data
        self.itemordershistogram = {}
        self.item_count = sum([item_data.get_amount() for item_data in item_data], start=0)

        self.on_dismiss = self.__on_dismiss
        self.__updated_time = ft.Text(value=f' ')
        self.create_title()

        self.item_info_column = ft.Column(alignment=ft.MainAxisAlignment.START, expand=True)
        self.sell_info_column = ft.Column(scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.START)
        self.buy_info_column = ft.Column(scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.START)
        self.content = ft.Row(
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

        self.button_price_sell = ft.TextField(label='Покупатель заплатит', dense=True, content_padding=10, expand=True, max_lines=1, text_align=ft.TextAlign.RIGHT,
                                              prefix_text=common.prefix_currency, suffix_text=common.suffix_currency, on_change=self.on_change_button_price_sell)
        self.button_price_get = ft.TextField(label='Вы получите', dense=True, content_padding=10, expand=True, max_lines=1, text_align=ft.TextAlign.RIGHT,
                                             prefix_text=common.prefix_currency, suffix_text=common.suffix_currency, on_change=self.on_change_button_price_get)
        self.item_info_column.controls.append(ft.Row(controls=[self.button_price_sell, self.button_price_get]))


        self.count_item_sell = ft.TextField(label='Количество к продаже', dense=True, content_padding=10, expand=True, max_lines=1, text_align=ft.TextAlign.RIGHT,
                                            suffix_text=f"из {self.item_count}", value='1', on_change=self.set_count_sell,
                                            input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9]", replacement_string="0"))
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

        self.item_info_column.controls.append(ft.Row(controls=[self.button_total_price_sell, self.button_total_price_get]))

        self.button_start_sell = ft.FilledButton('Продать', on_click=self.start_sell, expand=True, disabled=True)
        self.item_info_column.controls.append(ft.Row(controls=[self.button_start_sell]))

        self.log_column = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.item_info_column.controls.append(ft.Row(controls=[self.log_column], expand=True))

    def start_sell(self, *args):
        button_price_get = int(float(self.button_price_get.value if self.button_price_get.value else 0) * 100)
        if not button_price_get: return
        count_item_sell = int(self.count_item_sell.value if self.count_item_sell.value else 0)
        if not count_item_sell: return
        for item in self.all_item_in_inventary:
            if count_item_sell <= 0: break
            item_id = item.id
            amount = item.get_amount()
            if amount <= 0: continue
            item.amount = item.get_amount() - count_item_sell
            if amount > count_item_sell:
                amount = count_item_sell
            count_item_sell -= amount

            status = common.session.fetch_sellitem(appid=int(common.app_id), assetid=int(item_id), amount=int(amount), price=button_price_get, contextid=common.get_contextid_appid())
            self.log_column.controls.insert(0, ft.Text(f'{status}'))
            time.sleep(0.1)
        self.log_column.controls.insert(0, ft.Text(f'Готово, выставил {int(self.count_item_sell.value if self.count_item_sell.value else 0)}'))

        self.set_count_sell(count=1)
        self.create_title()
        self.update()

    def update_total(self, *args):
        button_price_sell = float(self.button_price_sell.value if self.button_price_sell.value else 0)
        button_price_get = float(self.button_price_get.value if self.button_price_get.value else 0)
        count_item_sell = int(self.count_item_sell.value if self.count_item_sell.value else 0)

        self.button_total_price_sell.value = f'{round(button_price_sell * count_item_sell, 2)}'
        self.button_total_price_sell.update()

        self.button_total_price_get.value = f'{round(button_price_get * count_item_sell, 2)}'
        self.button_total_price_get.update()

        self.button_start_sell.text = f'Продать {count_item_sell} {self.item_data.name()} за {round(button_price_get * count_item_sell, 2)}'
        self.button_start_sell.disabled = button_price_get == 0 or count_item_sell == 0
        self.button_start_sell.update()

    def set_count_sell(self, *args, count=None):
        if count:
            self.count_item_sell.value = int(count)

        self.item_count = sum([item_data.get_amount() for item_data in self.all_item_in_inventary], start=0)
        self.count_item_sell.suffix_text = f"из {self.item_count}"

        if int(self.count_item_sell.value) > self.item_count:
            self.count_item_sell.value = self.item_count
        if int(self.count_item_sell.value) < 1:
            self.count_item_sell.value = '1'
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
        if not self.item_id:
            self.item_id = self.load_item_nameid()
        if not self.item_id: return

        return common.session.fetch_market_itemordershistogram(currency=common.default_currency, item_nameid=self.item_id)

    def create_title(self):
        item_name = next((item.name() for item in self.all_item_in_inventary if item.name()), 'No Name')
        name_color = next((item.color() for item in self.all_item_in_inventary if item.color()), None)
        icon_url = next((item.icon_url() for item in self.all_item_in_inventary if item.icon_url()), None)
        count = sum((item.get_amount() for item in self.all_item_in_inventary), start=0)
        self.title = ft.Row(expand=True, alignment=ft.MainAxisAlignment.CENTER)
        item_img_widget = ft.Container(width=50 * 1.2, height=29 * 1.2)
        if icon_url:
            item_img_widget.content = ft.Image(src=icon_url, width=50 * 1.2, height=29 * 1.2)
        widget_name = ft.Text(size=29, value=f'{count} шт.  {item_name}', color=name_color)
        self.title.controls = [item_img_widget, widget_name, self.__updated_time]

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
                self.update()
            except:
                pass
            time.sleep(1)


class ItemData:
    def __init__(self, market_hash_name: str):
        self.__page: ft.Page = None
        self.market_hash_name = market_hash_name
        self.item_list: list[InventoryItem] = []
        self.item_history_hour = InventoryHistoryItem()
        self.item_history_day = InventoryHistoryItem()
        self.market_info = MarketItem({})

        self.name = market_hash_name
        self.single_price_now = 0
        self.price_now = 0
        self.count_now = 0
        self.price_hours = 0
        self.count_hours = 0
        self.price_day = 0
        self.count_day = 0

        # Инициализация текстовых элементов
        self.name_text = create_text(market_hash_name, text_align=ft.TextAlign.LEFT)
        self.image = ft.Image(width=29, height=29)
        self.item_title_container = ft.Container(url='', ink=True, margin=0, padding=0, width=200,
                                                 content=ft.Row(spacing=1, expand=True, controls=[
                                                     self.image,
                                                     self.name_text
                                                 ]))
        self.single_price_now_text = create_text(' ', text_align=ft.TextAlign.RIGHT)
        self.price_now_text = create_text(' ', text_align=ft.TextAlign.RIGHT)
        self.count_now_text = create_text('0шт.', text_align=ft.TextAlign.RIGHT)
        self.price_hours_text = create_text(' ', text_align=ft.TextAlign.RIGHT)
        self.count_hours_text = create_text(' ', text_align=ft.TextAlign.RIGHT)
        self.price_day_text = create_text(' ', text_align=ft.TextAlign.RIGHT)
        self.count_day_text = create_text(' ', text_align=ft.TextAlign.RIGHT)
        self.icon_sell = ft.IconButton(ft.icons.ATTACH_MONEY, icon_color=ft.colors.GREEN, on_click=self.__sell_item, height=29,
                                       style=ft.ButtonStyle(padding=ft.padding.all(0)))
        self.item_main_row = self.__create_widget()

    def set_page(self, page: ft.Page):
        self.__page = page

    def safe_update(self, widget=None):
        try:
            self.item_main_row.update() if widget is None else widget.update()
        except:
            logger.exception('Exception while updating widget')

    def __create_widget(self):
        # Создание строки "Сейчас"
        now_item_row = create_row(self.single_price_now_text, self.price_now_text, self.count_now_text)

        # Создание строки "Изменения за час"
        hour_item_row = create_row(self.price_hours_text, self.count_hours_text)

        # Создание строки "Изменения за день"
        day_item_row = create_row(self.price_day_text, self.count_day_text)

        # Создание строки "Продать предмет"
        sell_item_row = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[ft.Container(width=150, content=self.icon_sell)],
        )

        return ft.Container(
            content=ft.Row(controls=[self.item_title_container, now_item_row, hour_item_row, day_item_row, sell_item_row]),
            on_click=lambda e: ...,
            ink=True
        )

    def update_widget_item(self, is_update: bool = False):
        all_market_url = (
                [i.market_url() for i in self.item_list] +
                [self.item_history_hour.market_url()] +
                [self.item_history_day.market_url()] +
                [self.market_info.market_url()]
        )
        market_url = next((i for i in all_market_url if i), None)
        all_image_url = (
                [i.icon_url() for i in self.item_list] +
                [self.item_history_hour.get_icon_url()] +
                [self.item_history_day.get_icon_url()] +
                [self.market_info.icon_url()]
        )
        image_url = next((i for i in all_image_url if i), None)
        all_name = (
                [i.name() for i in self.item_list] +
                [self.item_history_hour.name] +
                [self.item_history_day.name] +
                [self.market_info.name]
        )
        name = next((i for i in all_name if i), None)
        all_color = (
                [i.color() for i in self.item_list] +
                [self.item_history_hour.get_color()] +
                [self.item_history_day.get_color()] +
                [self.market_info.color()]
        )
        color = next((i for i in all_color if i), None)

        self.item_title_container.url = market_url if market_url else self.item_title_container.url
        self.image.src = image_url if image_url else self.image.src
        self.name_text.value = name if name else self.name_text.value
        self.name_text.color = color if color else self.name_text.color

        self.single_price_now_text.value = self.market_info.sell_price_text if self.market_info else ' '

        count_now = sum(i.get_amount() for i in self.item_list)
        self.price_now_text.value = self.market_info.multiply_price_in_currency(count_now) if self.market_info else ' '
        self.count_now_text.value = f'{count_now}шт.'

        hour_change = count_now - self.item_history_hour.count
        hour_change_color = ft.colors.GREEN if hour_change > 0 else ft.colors.RED
        self.price_hours_text.value = self.market_info.multiply_price_in_currency(hour_change) if self.market_info and hour_change != 0 else ' '
        self.price_hours_text.color = hour_change_color
        self.count_hours_text.value = f'{hour_change}шт.' if hour_change != 0 else ' '
        self.count_hours_text.color = hour_change_color

        day_change = count_now - self.item_history_day.count
        day_change_color = ft.colors.GREEN if day_change > 0 else ft.colors.RED
        self.price_day_text.value = self.market_info.multiply_price_in_currency(day_change) if self.market_info and day_change != 0 else ' '
        self.price_day_text.color = day_change_color
        self.count_day_text.value = f'{day_change}шт.' if day_change != 0 else ' '
        self.count_day_text.color = day_change_color

        self.name = self.name_text.value
        self.single_price_now = self.market_info.sell_price if self.market_info else 0
        self.price_now = self.market_info.sell_price * count_now if self.market_info else 0
        self.count_now = count_now
        self.price_hours = self.market_info.sell_price * hour_change if self.market_info else 0
        self.count_hours = hour_change
        self.price_day = self.market_info.sell_price * day_change if self.market_info else 0
        self.count_day = day_change

        is_any_marketable = any([i.is_marketable() for i in self.item_list])
        if not is_any_marketable and not self.icon_sell.disabled:
            self.icon_sell.disabled = True
            self.icon_sell.tooltip = 'Нет доступных предметов для продажи'
            self.icon_sell.icon_color = ft.colors.RED
        if is_any_marketable and self.icon_sell.disabled:
            self.icon_sell.disabled = False
            self.icon_sell.tooltip = ''
            self.icon_sell.icon_color = ft.colors.GREEN

        if is_update:
            self.safe_update()

    def add_item(self, items: list[InventoryItem]):
        self.item_list = [i for i in items if i.market_hash_name() == self.market_hash_name]
        self.update_widget_item()
    def add_market_info(self, market: MarketItem):
        if not market: return
        if market.market_hash_name() != self.market_hash_name: return
        self.market_info = market
        self.update_widget_item()
    def update_history(self, item_history_hour: InventoryHistoryItem, item_history_day: InventoryHistoryItem):
        if item_history_hour:
            self.item_history_hour = item_history_hour
        if item_history_day:
            self.item_history_day = item_history_day
        self.update_widget_item()

    def clear_widget(self, is_update: bool = False):
        self.item_list = []
        self.item_history_hour = 0
        self.item_history_day = 0

    def __sell_item(self, *args):
        if not self.item_list or not self.__page: return
        dialog = DialogSell(self.item_list)
        self.__page.dialog = dialog
        dialog.open = True
        self.safe_update(self.__page)


class InventoryItemListTable(ft.Column):
    def __init__(self):
        super().__init__()
        self.alignment = ft.MainAxisAlignment.START
        self.expand = True
        self.spacing = 0

        self.sort_type = 'count_now'
        self.sort_descending = True
        self.name_filter = ''
        self.item_widgets: dict[str, ItemData] = {}

        # Инициализация текстовых элементов
        self.single_price_now_text = create_text('0.0', text_align=ft.TextAlign.RIGHT)
        self.price_now_text = create_text('0.0', text_align=ft.TextAlign.RIGHT)
        self.count_now_text = create_text('0шт.', text_align=ft.TextAlign.RIGHT)
        self.price_hours_text = create_text('0.0', text_align=ft.TextAlign.RIGHT)
        self.count_hours_text = create_text('0шт.', text_align=ft.TextAlign.RIGHT)
        self.price_day_text = create_text('0.0', text_align=ft.TextAlign.RIGHT)
        self.count_day_text = create_text('0шт.', text_align=ft.TextAlign.RIGHT)

        self.controls.append(self.__create_title_row())
        self.controls.append(self.__account_info())

        self.items_column = ft.Column(spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)
        self.controls.append(ft.Row(controls=[self.items_column], expand=True))

    def update_clear(self):
        self.single_price_now_text.value = '0.0'
        self.price_now_text.value = '0.0'
        self.count_now_text.value = '0шт.'
        self.price_hours_text.value = '0.0'
        self.count_hours_text.value = '0шт.'
        self.price_day_text.value = '0.0'
        self.count_day_text.value = '0шт.'

        self.sort_type = 'count_now'
        self.sort_descending = True
        self.name_filter = ''

        self.item_widgets: dict[str, ItemData] = {}

        self.items_column.controls = []
    def safe_update(self, widget=None):
        try:
            self.update() if widget is None else widget.update()
        except:
            logger.exception('Exception while updating widget')


    def __create_button(self, label, sort_key, expand=True):
        return ft.FilledButton(
            label,
            on_click=lambda e: self.__on_change_sort(sort_key),
            expand=expand,
            height=24,
            style=ft.ButtonStyle(padding=ft.padding.all(0)),
        )
    def __account_info(self):
        # Создание строки "Название"
        item_row = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=200,
                    content=ft.Row(
                        expand=True,
                        controls=[create_text('Всего:', text_align=ft.TextAlign.RIGHT)],
                    ),
                ),
            ],
        )

        # Создание строки "Сейчас"
        now_item_row = create_row(self.single_price_now_text, self.price_now_text, self.count_now_text)

        # Создание строки "Изменения за час"
        hour_item_row = create_row(self.price_hours_text, self.count_hours_text)

        # Создание строки "Изменения за день"
        day_item_row = create_row(self.price_day_text, self.count_day_text)

        # Создание строки "Продать предмет"
        sell_item_row = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[ft.Container(width=150)],
        )

        # Возврат всей строки заголовка
        return ft.Row(controls=[item_row, now_item_row, hour_item_row, day_item_row, sell_item_row])
    def __create_title_row(self):
        # Создание строки "Название"
        item_title_text = create_text('Название')
        item_title_sort_textfield = ft.TextField(
            label='Name Filter',
            dense=True,
            content_padding=5,
            text_align=ft.TextAlign.LEFT,
            max_lines=1,
            expand=True,
        )
        item_title_sort_textfield.on_change = lambda e: self.__on_change_name_filter(item_title_sort_textfield.value)
        item_row = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=200,
                    content=ft.Row(
                        expand=True,
                        controls=[
                            ft.Row(spacing=0, expand=True, controls=[item_title_text]),
                            ft.Row(spacing=0, expand=True, controls=[item_title_sort_textfield]),
                        ],
                    ),
                ),
            ],
        )

        # Создание строки "Сейчас"
        now_item_row = ft.Row(
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    expand=True,
                    spacing=0,
                    controls=[
                        ft.Row(spacing=0, controls=[create_text('Сейчас')]),
                        ft.Row(
                            spacing=0,
                            controls=[
                                self.__create_button('Цена за шт', 'single_price_now'),
                                self.__create_button('Цена', 'price_now'),
                                self.__create_button('Кол-во', 'count_now'),
                            ],
                        ),
                    ],
                ),
            ],
        )

        # Создание строки "Изменения за час"
        hour_item_row = ft.Row(
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    expand=True,
                    spacing=0,
                    controls=[
                        ft.Row(spacing=0, controls=[create_text('Изменения за час')]),
                        ft.Row(
                            spacing=0,
                            controls=[
                                self.__create_button('Цена', 'price_hours'),
                                self.__create_button('Кол-во', 'count_hours'),
                            ],
                        ),
                    ],
                ),
            ],
        )

        # Создание строки "Изменения за день"
        day_item_row = ft.Row(
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Column(
                    expand=True,
                    spacing=0,
                    controls=[
                        ft.Row(spacing=0, controls=[create_text('Изменения за день')]),
                        ft.Row(
                            spacing=0,
                            controls=[
                                self.__create_button('Цена', 'price_day'),
                                self.__create_button('Кол-во', 'count_day'),
                            ],
                        ),
                    ],
                ),
            ],
        )

        # Создание строки "Продать предмет"
        sell_item_row = ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=150,
                    content=ft.Row(
                        expand=True,
                        controls=[ft.Row(spacing=0, expand=True, controls=[create_text('Продать предмет')])],
                    ),
                ),
            ],
        )

        # Возврат всей строки заголовка
        return ft.Row(controls=[item_row, now_item_row, hour_item_row, day_item_row, sell_item_row])

    def __update_inventory(self, inventory: InventoryManager):
        if not inventory: return
        all_history = InventoryAllHistory()
        hour_history = all_history.get_history_hours_ago(hours_ago=1)
        day_history = all_history.get_history_hours_ago(hours_ago=24)

        now_list_inventory = [InventoryItem(item) for item in inventory.inventory]
        now_list_market_hash_name = {item.market_hash_name() for item in now_list_inventory}
        list_market_hash_name = (now_list_market_hash_name | hour_history.get_list_market_hash_name() | day_history.get_list_market_hash_name())

        market_items = [MarketItem(item) for item in common.market_list]

        for market_hash_name, item in self.item_widgets.items(): item.clear_widget(is_update=False)
        for market_hash_name in list_market_hash_name:
            if market_hash_name not in self.item_widgets:
                self.item_widgets[market_hash_name] = ItemData(market_hash_name)
            item_widgets = self.item_widgets[market_hash_name]

            item_widgets.add_item([item for item in now_list_inventory if item and item.market_hash_name() == market_hash_name])
            item_widgets.update_history(
                hour_history.get_item_from_market_hash_name(market_hash_name),
                day_history.get_item_from_market_hash_name(market_hash_name),
            )
            market_item = next((item for item in market_items if item.market_hash_name() == market_hash_name), None)
            item_widgets.add_market_info(market_item)
            item_widgets.set_page(self.page)

        self.__on_change_sort(self.sort_type, update_sort=True)
    def __update_market(self, market: list):
        if not market: return
        market_items = [MarketItem(item) for item in market]

        for market_hash_name, item in self.item_widgets.items():
            market_item = next((item for item in market_items if item.market_hash_name() == market_hash_name), None)
            item.add_market_info(market_item)

        self.__on_change_sort(self.sort_type, update_sort=True)

    def update_inventory_items(self, button: ft.FilledButton, text: str = 'Обновить инвентарь'):
        button.disabled = True
        button.text = f"{text} [Загружаю...]"
        self.safe_update(button)

        now_inventory = common.update_inventory()
        self.__update_inventory(now_inventory)

        time_now = datetime.datetime.now().strftime('%H:%M:%S')
        button.text = f"{text} [Инвентарь обновлен {time_now}]" if now_inventory else f"{text} [Инвентарь не обновлен]"
        self.safe_update(button)

        time.sleep(5)
        button.disabled = False
        self.safe_update(button)
    def update_market_items(self, button: ft.FilledButton, text: str = 'Обновить цены'):
        button.disabled = True
        button.text = f"{text} [Загружаю...]"
        self.safe_update(button)

        now_market = common.update_market_list()
        self.__update_market(now_market)

        time_now = datetime.datetime.now().strftime('%H:%M:%S')
        button.text = f"{text} [Цены обновлены {time_now}]" if now_market else f"{text} [Цены не обновлены]"
        self.safe_update(button)

        time.sleep(5)
        button.disabled = False
        self.safe_update(button)


    def __on_change_name_filter(self, name_filter: str = ''):
        self.name_filter = name_filter
        self.__on_change_sort(self.sort_type, update_sort=True)
    def __on_change_sort(self, sort_type: str = '', update_sort: bool = False):
        if not update_sort:
            self.sort_descending = True if self.sort_type != sort_type else not self.sort_descending
            self.sort_type = sort_type
        
        items_list: list[ItemData] = [item for market_hash_name, item in self.item_widgets.items()
                                      if self.name_filter.lower() in item.name.lower()]
        if self.sort_type == 'price_now':
            items_list.sort(key=lambda item: item.price_now, reverse=self.sort_descending)
        elif self.sort_type == 'single_price_now':
            items_list.sort(key=lambda item: item.single_price_now, reverse=self.sort_descending)
        elif self.sort_type == 'count_now':
            items_list.sort(key=lambda item: item.count_now, reverse=self.sort_descending)

        elif self.sort_type == 'price_hours':
            items_list.sort(key=lambda item: item.price_hours, reverse=self.sort_descending)
        elif self.sort_type == 'count_hours':
            items_list.sort(key=lambda item: item.price_hours, reverse=self.sort_descending)

        elif self.sort_type == 'price_day':
            items_list.sort(key=lambda item: item.price_day, reverse=self.sort_descending)
        elif self.sort_type == 'count_day':
            items_list.sort(key=lambda item: item.count_day, reverse=self.sort_descending)

        ready_market_example: MarketItem = next((item.market_info for item in items_list if item.market_info and item.market_info.sell_price_text), None)

        sum_single_price_now = sum([item.single_price_now for item in items_list], start=0)
        sum_price_now = sum([item.price_now for item in items_list], start=0)
        self.single_price_now_text.value = ready_market_example.generate_number_in_currency(sum_single_price_now) if ready_market_example else ' '
        self.price_now_text.value = ready_market_example.generate_number_in_currency(sum_price_now) if ready_market_example else ' '
        self.count_now_text.value = f'{sum([item.count_now for item in items_list], start=0)}шт.'

        sum_price_hours = sum([item.price_hours for item in items_list], start=0)
        self.price_hours_text.value = ready_market_example.generate_number_in_currency(sum_price_hours) if ready_market_example else ' '
        self.count_hours_text.value = f'{sum([item.count_hours for item in items_list], start=0)}шт.'

        sum_price_day = sum([item.price_day for item in items_list], start=0)
        self.price_day_text.value = ready_market_example.generate_number_in_currency(sum_price_day) if ready_market_example else ' '
        self.count_day_text.value = f'{sum([item.count_day for item in items_list], start=0)}шт.'

        self.items_column.controls = [item.item_main_row for item in items_list]
        self.safe_update()


class InventoryWidget(ft.Column):
    def __init__(self):
        super().__init__()
        self.is_run = False
        self.isolated = True
        self.expand = True
        self.alignment = ft.MainAxisAlignment.START
        self.spacing = 0
        self.__last_app_id = 0
        self.__next_update_inventory = datetime.datetime.min
        self.__next_update_market = datetime.datetime.min

        self.title_widget_text = ft.Text('Ваш инвентарь:', size=24, color=ft.colors.BLUE, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, expand=True)
        body_title_widget_row = ft.Row(controls=[self.title_widget_text], alignment=ft.MainAxisAlignment.CENTER, run_spacing=0)

        self.table_widget = InventoryItemListTable()
        self.is_not_loaded = ft.Row(alignment=ft.MainAxisAlignment.CENTER, visible=False,
                                    controls=[ft.FilledButton("Инвентарь не загружен", disabled=True, expand=True)])
        self.body_widget_column = ft.Column(expand=True, spacing=0, alignment=ft.MainAxisAlignment.CENTER)
        self.body_widget_column.controls = [self.is_not_loaded, self.table_widget]


        self.update_widget_button = ft.FilledButton(
            'Обновить инвентарь', expand=True,
            height=30, style=ft.ButtonStyle(padding=ft.padding.all(0))
        )
        self.update_widget_button.on_click = lambda e: self.table_widget.update_inventory_items(button=self.update_widget_button)

        self.update_price_widget_button = ft.FilledButton(
            'Обновить цены', expand=True,
            height=30, style=ft.ButtonStyle(padding=ft.padding.all(0))
        )
        self.update_price_widget_button.on_click = lambda e: self.table_widget.update_market_items(button=self.update_price_widget_button)

        self.auto_update_inventory_checkbox = ft.Checkbox(label='Автообновление инвентаря', value=bool(setting.auto_update_inventory))
        self.auto_update_inventory_checkbox.on_change = lambda e: self.__on_change_auto_update_inventory(self.auto_update_inventory_checkbox.value)

        buttons_widget_row = ft.Row(spacing=0, controls=[
            self.update_widget_button,
            self.update_price_widget_button,
            self.auto_update_inventory_checkbox,
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
        self.safe_update(self)
        self.update_clear()
        threading.Thread(target=self.__update).start()

    def will_unmount(self):
        self.is_run = False
    def safe_update(self, widget=None):
        try:
            if not self.is_run: return
            if not widget: widget = self
            widget.update()
        except:
            logger.exception('Exception while updating widget')
    def update_clear(self):
        if self.__last_app_id == common.app_id: return
        self.__last_app_id = common.app_id
        self.table_widget.update_clear()
        # self.__next_update_inventory = datetime.datetime.min
        # self.__next_update_market = datetime.datetime.min
        self.safe_update(self)

    @staticmethod
    def __on_change_auto_update_inventory(value):
        setting.auto_update_inventory = bool(value)
    def __update(self):
        while self.is_run:
            try:
                if setting.auto_update_inventory:
                    datetime_now = datetime.datetime.now()
                    if self.__next_update_inventory <= datetime_now:
                        threading.Thread(target=lambda _=None: self.table_widget.update_inventory_items(button=self.update_widget_button)).start()
                        # self.table_widget.update_inventory_items(button=self.update_widget_button)
                        self.__next_update_inventory = datetime_now + datetime.timedelta(minutes=2)
                    if self.__next_update_market <= datetime_now:
                        threading.Thread(target=lambda _=None: self.table_widget.update_market_items(button=self.update_price_widget_button)).start()
                        # self.table_widget.update_market_items(button=self.update_price_widget_button)
                        self.__next_update_market = datetime_now + datetime.timedelta(minutes=2)

                title = (f'Inventory Manager -> {self.table_widget.count_now_text.value} [{self.table_widget.price_now_text.value}] | '
                         f'Изменения за час: {self.table_widget.count_hours_text.value} [{self.table_widget.price_hours_text.value}] | '
                         f'Изменения за день: {self.table_widget.count_day_text.value} [{self.table_widget.price_day_text.value}]')
                if self.page.title != title:
                    self.page.title = title
                    self.safe_update(self.page)
            except:
                pass
            time.sleep(1)


