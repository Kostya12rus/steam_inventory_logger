import datetime
import re
import threading
import time

from flet_manager import common
import flet as ft
from logger_utility.logger_config import logger


class MarketWidget(ft.Row):
    def __init__(self):
        super().__init__()
        self.__is_run = False
        self.isolated = True
        self.expand = True
        self.alignment = ft.MainAxisAlignment.START

        self.item_list_column = ft.Column(expand=True)
        self.history_column = ft.Column()
        self.controls = [self.item_list_column, ft.VerticalDivider(), self.history_column]

        self.item_list_column_title = ft.Text('Торговая площадка, список предметов:', size=24, color=ft.colors.BLUE, weight=ft.FontWeight.BOLD)
        self.item_list_column.controls.append(ft.Row([self.item_list_column_title], alignment=ft.MainAxisAlignment.CENTER))

        self.history_column_title = ft.Text('История:', size=24, color=ft.colors.BLUE, weight=ft.FontWeight.BOLD)
        self.history_column.controls.append(ft.Row([self.history_column_title], alignment=ft.MainAxisAlignment.CENTER))

        self.items_column = ft.DataTable(column_spacing=5, vertical_lines=ft.BorderSide(1),
                                         heading_row_height=25, data_row_min_height=25, data_row_max_height=25)
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
        self.update_history()
        self.update_market_list_widget()

    def get_def_widget(self, item_now, history_old):
        asset_description: dict = item_now.get('asset_description', {})
        hash_name = item_now.get('hash_name', '')
        market_hash_name = asset_description.get('market_hash_name', "")
        now_item_count = item_now.get('sell_listings', 0)
        now_item_price = item_now.get('sell_price', 0)

        last_item = next((_last_item_ago for _last_item_ago in history_old.get('items', {})
                          if _last_item_ago.get('asset_description', {}).get('market_hash_name', '') == market_hash_name and
                          _last_item_ago.get('hash_name', '') == hash_name), {})
        last_item_count = last_item.get('sell_listings', 0)
        last_item_count_str = ""
        last_item_price = last_item.get('sell_price', 0)
        last_item_price_str = ""
        price_str = f"{last_item.get('sell_price_text', {})}" or f"{item_now.get('sell_price_text', {})}"
        last_item_color = ft.colors.GREEN
        if last_item_price != now_item_price or last_item_count != now_item_count:
            last_item_count_str = f"{now_item_count - last_item_count} шт."
            if last_item_price - now_item_price != 0:
                last_item_price_str = f"{self.replace_number_in_currency(price_str, f'{round((last_item_price - now_item_price) / 100, 2)}')}"
                last_item_color = ft.colors.GREEN if last_item_price >= now_item_price else ft.colors.RED

        last_item_price_text = ft.Text(last_item_price_str if last_item_price_str else " ",
                                       color=ft.colors.GREEN if last_item_price >= now_item_price else ft.colors.RED, size=15, max_lines=1,
                                       overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.RIGHT)
        last_item_count_text = ft.Text(f"{last_item_count_str}" if last_item_count_str else " ",
                                       color=ft.colors.GREEN if last_item_count <= now_item_count else ft.colors.RED, size=15, max_lines=1,
                                       overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.RIGHT)

        last_item_widget_row = ft.Row(expand=True, spacing=0, controls=[last_item_price_text, last_item_count_text])
        last_item_container = ft.Container(width=200, content=last_item_widget_row)

        percent_change_price = (now_item_price / last_item_price) - 1 if last_item_price != 0 else 0
        percent_change_price_text = self.replace_number_in_currency(last_item.get('sell_price_text', {}), f"{round(percent_change_price*100, 2):.2f}")
        percent_change_count = (now_item_count / last_item_count) - 1 if last_item_count != 0 else 0

        last_item_container.tooltip = (f"{history_old.get('time_update', datetime.datetime.min)}\n"
                                       f"Цена: {last_item.get('sell_price_text', '0')} -> {item_now.get('sell_price_text', '0')} [{percent_change_price_text}%]\n"
                                       f"Кол-во: {last_item_count}шт. -> {now_item_count}шт. [{round(percent_change_count*100, 2):.2f}%]")
        return last_item_container

    def update_market_list_widget(self):
        all_history = common.get_history_market_list()
        if not all_history: return

        current_time = datetime.datetime.now()
        hour_datetime = current_time - datetime.timedelta(hours=1)
        day_datetime = current_time - datetime.timedelta(days=1)

        hour_history = [history for history in all_history if history.get('time_update', datetime.datetime.min) > hour_datetime]
        day_history = [history for history in all_history if history.get('time_update', datetime.datetime.min) > day_datetime]

        now_history: dict = max(all_history, key=lambda x: x['time_update'], default={})
        last_history: dict = max(all_history, key=lambda x: x['time_update'] and now_history['time_update'] != x['time_update'], default={})
        earliest_hour_history: dict = min(hour_history, key=lambda x: x['time_update'], default={})
        earliest_day_history: dict = min(day_history, key=lambda x: x['time_update'], default={})

        title_name_widget = ft.DataColumn(ft.Text('Предмет', size=18), on_sort=lambda e: print(f"{e.column_index}, {e.ascending}"))
        title_now_widget = ft.DataColumn(ft.Text('Цена сейчас', size=18), on_sort=lambda e: print(f"{e.column_index}, {e.ascending}"))
        title_last_widget = ft.DataColumn(ft.Text('Прошлая проверка', size=18), on_sort=lambda e: print(f"{e.column_index}, {e.ascending}"))
        title_hour_widget = ft.DataColumn(ft.Text('Цена за час', size=18), on_sort=lambda e: print(f"{e.column_index}, {e.ascending}"))
        title_day_widget = ft.DataColumn(ft.Text('Цена за день', size=18), on_sort=lambda e: print(f"{e.column_index}, {e.ascending}"))
        self.items_column.columns = [title_name_widget, title_now_widget, title_last_widget, title_hour_widget, title_day_widget]
        self.items_column.rows = []

        item_data = now_history.get('items', {})
        for item in item_data:
            asset_description: dict = item.get('asset_description', {})
            hash_name = item.get('hash_name', '')
            market_hash_name = asset_description.get('market_hash_name', "")
            if hash_name != market_hash_name: continue
            row_item_info = ft.Row(spacing=1, expand=True)
            item_info_control = ft.Container(
                ink=True, content=row_item_info, margin=0, padding=0,
                url=f'https://steamcommunity.com/market/listings/{asset_description.get("appid", common.app_id)}/{market_hash_name}',
            )

            item_img_url = f'https://community.akamai.steamstatic.com/economy/image/{asset_description.get("icon_url", "")}/330x192?allow_animated=1'
            item_img_widget = ft.Container(width=50, height=29, content=ft.Image(src=item_img_url, width=50, height=29))
            row_item_info.controls.append(item_img_widget)

            item_name = asset_description.get('name', ' ')
            item_color = asset_description.get('name_color')
            item_name_widget = ft.Text(f'{item_name}', color=f'#{item_color}' if item_color else '',
                                       size=15, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
            item_name_widget_container = ft.Container(width=250, content=item_name_widget)
            row_item_info.controls.append(item_name_widget_container)

            now_item_count = item.get('sell_listings', 0)
            now_item_count_str = f"{now_item_count}шт."
            now_item_price_str = f"{item.get('sell_price_text', {})}"

            last_item_price_text = ft.Text(now_item_price_str, color=ft.colors.GREEN, size=15, max_lines=1,
                                           overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.RIGHT)
            last_item_count_text = ft.Text(now_item_count_str, color=ft.colors.GREEN, size=15, max_lines=1,
                                           overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.RIGHT)
            last_item_widget_row = ft.Row(expand=True, spacing=0, controls=[last_item_price_text, last_item_count_text])
            last_item_container = ft.Container(width=200, content=last_item_widget_row)

            test = ft.DataRow(
                [
                    ft.DataCell(item_info_control),
                    ft.DataCell(last_item_container),
                    ft.DataCell(self.get_def_widget(item, last_history)),
                    ft.DataCell(self.get_def_widget(item, earliest_hour_history)),
                    ft.DataCell(self.get_def_widget(item, earliest_day_history)),
                ],
                selected=True,
                on_select_changed=lambda e: print(f"row select changed: {e.data}"),
            )
            self.items_column.rows.append(test)
        self.items_column.update()

    @staticmethod
    def replace_number_in_currency(original_str, new_number):
        pattern = r'\d{1,3}(?:\s?\d{3})*(?:[,.]\d+)?'
        return re.sub(pattern, new_number, original_str)

    def find_change_history(self, now_history: dict, old_history: dict):
        if not now_history and not old_history: return None
        now_history_datetime = now_history.get('time_update', datetime.datetime.min)
        old_history_datetime = old_history.get('time_update', datetime.datetime.min)

        column_period_widget = ft.Column(spacing=0)
        column_period_widget.controls.append(ft.Text(f'{now_history_datetime.strftime("%d.%m.%Y %H:%M")}-{old_history_datetime.strftime("%d.%m.%Y %H:%M")}'))

        def extract_hash_names(history):
            items = history.get('items', [])
            return {item.get('hash_name') for item in items if item.get('hash_name') == item.get('asset_description', {}).get('market_hash_name')}
        def get_item_from_market_hash_name(_market_hash_name: str, _history: dict):
            return next((i for i in _history.get('items', []) if i.get('hash_name', '') == market_hash_name and
                         i.get('asset_description', {}).get('market_hash_name', '') == market_hash_name), {})

        common_hash_names = extract_hash_names(now_history) & extract_hash_names(old_history)
        if not common_hash_names: return None

        for market_hash_name in common_hash_names:
            item_column_info = ft.Column(spacing=0)

            now_history_item = get_item_from_market_hash_name(market_hash_name, now_history)
            old_history_item = get_item_from_market_hash_name(market_hash_name, old_history)

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
            if not now_history_item:
                item_new_del_widget = ft.Column(spacing=0)
                item_new_del_widget.controls.append(ft.Text('Предмет ушел с продажи', color=ft.colors.RED))
                item_new_del_widget.controls.append(ft.Text(f'Цена: {old_sell_price_text} [{old_sell_listings} шт.]', color=ft.colors.RED))
                item_column_info.controls.append(item_new_del_widget)
            elif not old_history_item:
                item_new_del_widget = ft.Column(spacing=0)
                item_new_del_widget.controls.append(ft.Text('Новый предмет в продаже', color=ft.colors.GREEN))
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
                    percent_change_price_text = self.replace_number_in_currency(old_sell_price_text, f"{round(def_price / 100, 2):.2f}")
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


