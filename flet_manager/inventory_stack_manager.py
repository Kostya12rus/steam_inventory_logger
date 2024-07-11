import datetime
import re
import threading
import time

from flet_manager import common
import flet as ft

from sql_manager.config import setting
from logger_utility.logger_config import logger
from steam_utility.manager_steam_session import InventoryManager

class ItemDescription:
    def __init__(self, description_dict: dict = None):
        if not description_dict: description_dict = {}
        self.type = description_dict.get('type', '')
        self.value = description_dict.get('value', '')
class ItemTag:
    def __init__(self, tag_dict: dict = None):
        if not tag_dict: tag_dict = {}
        self.category = tag_dict.get('category', '')
        self.internal_name = tag_dict.get('internal_name', '')
        self.category_name = tag_dict.get('category_name', '')
        self.name = tag_dict.get('name', '')
class ItemRgDescriptions:
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
        self.descriptions = [ItemDescription(d) for d in rg_dict.get('descriptions', [])]
        self.owner_descriptions = [ItemDescription(d) for d in rg_dict.get('owner_descriptions', [])]
        self.tags = [ItemTag(t) for t in rg_dict.get('tags', [])]
class Item:
    def __init__(self, item_dict: dict = None):
        if not item_dict: item_dict = {}
        self.id = item_dict.get('id', '')
        self.classid = item_dict.get('classid', '')
        self.instanceid = item_dict.get('instanceid', '')
        self.amount = item_dict.get('amount', '0')
        self.hide_in_china = item_dict.get('hide_in_china', 0)
        self.pos = item_dict.get('pos', 0)
        self.rg_descriptions = ItemRgDescriptions(item_dict.get('rgDescriptions', {}))

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
        return self.rg_descriptions.name_color
    def get_amount(self):
        return int(self.amount)
    def market_url(self) -> str:
        return f'https://steamcommunity.com/market/listings/{self.rg_descriptions.appid}/{self.rg_descriptions.market_hash_name}'
    def icon_url(self) -> str:
        return f'https://community.akamai.steamstatic.com/economy/image/{self.rg_descriptions.icon_url}/330x192?allow_animated=1'
    def end_ban_marketable(self):
        return self.__extract_date_from_owner_descriptions()

    def __repr__(self):
        return f'<{self.id}, classid: {self.classid}, instanceid: {self.instanceid}, name: {self.name()}, market_hash_name: {self.market_hash_name()}>'
    def __str__(self):
        return f'<{self.id}, classid: {self.classid}, instanceid: {self.instanceid}, name: {self.name()}, market_hash_name: {self.market_hash_name()}>'

class InventoryStackWidget(ft.Column):
    def __init__(self):
        super().__init__()
        self.is_run = False
        self.isolated = True
        self.expand = True
        self.alignment = ft.MainAxisAlignment.START
        self.inventory: list[Item] = []
        self.__steam_token = None
        self.__items_button_stack = {}
        self.spacing = 0

        self.title_widget_text = ft.Text('Инвентарь для объединения', size=24, color=ft.colors.BLUE, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, expand=True)
        body_title_widget_row = ft.Row(controls=[self.title_widget_text], alignment=ft.MainAxisAlignment.CENTER, run_spacing=0)


        self.item_name_widget_datacolumn = ft.Text('Предмет', size=18)
        self.total_count_widget_datacolumn = ft.Text('Общее кол-во', size=18)
        self.item_count_widget_datacolumn = ft.Text('В предметах', size=18)
        self.marketable_widget_datacolumn = ft.Text('Нельзя продать', size=18)
        self.stack_widget_datacolumn = ft.Text('Объединить', size=18)

        self.inventory_table_widget = ft.DataTable(visible=False, columns=[], heading_row_height=30, data_row_min_height=25, data_row_max_height=25, expand=True)
        self.inventory_table_widget.columns = [ft.DataColumn(self.item_name_widget_datacolumn),
                                               ft.DataColumn(self.total_count_widget_datacolumn, numeric=True),
                                               ft.DataColumn(self.item_count_widget_datacolumn, numeric=True),
                                               ft.DataColumn(self.marketable_widget_datacolumn),
                                               ft.DataColumn(self.stack_widget_datacolumn)]
        self.inventory_is_not_loaded = ft.Row(alignment=ft.MainAxisAlignment.CENTER, visible=False,
                                              controls=[ft.FilledButton("Инвентарь не загружен", disabled=True, expand=True)])
        self.body_widget_column = ft.Column(expand=True, spacing=0, scroll=ft.ScrollMode.AUTO, alignment=ft.MainAxisAlignment.CENTER)
        self.body_widget_column.controls = [self.inventory_is_not_loaded, ft.Row(controls=[self.inventory_table_widget])]

        self.update_inventory_widget_button = ft.FilledButton('Обновить инвентарь', on_click=self.__load_inventory)
        self.start_all_stack_widget_button = ft.FilledButton('Объединить все предметы', expand=True, on_click=self.__stack_inventory)
        self.api_loaded_widget_button = ft.FilledButton('Токен загружается', disabled=True)
        buttons_widget_row = ft.Row(spacing=0, controls=[
            self.update_inventory_widget_button,
            self.start_all_stack_widget_button,
            self.api_loaded_widget_button
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
        self.update()

    def will_unmount(self):
        self.is_run = False

    def update_widget(self):
        pass
    def __update(self):
        while self.is_run:
            try:
                if not self.__steam_token:
                    self.__steam_token = common.session.get_steam_token()
                    if self.__steam_token:
                        self.api_loaded_widget_button.text = "Токен загружен"
                        self.api_loaded_widget_button.update()
                if not self.inventory and (not self.inventory_is_not_loaded.visible or self.inventory_table_widget.visible):
                    self.inventory_is_not_loaded.visible = True
                    self.inventory_is_not_loaded.update()
                    self.inventory_table_widget.visible = False
                    self.inventory_table_widget.update()

                    self.start_all_stack_widget_button.disabled = True
                    self.start_all_stack_widget_button.expand = False
                    self.start_all_stack_widget_button.update()
                    self.update_inventory_widget_button.expand = True
                    self.update_inventory_widget_button.update()

                if self.inventory and (self.inventory_is_not_loaded.visible or not self.inventory_table_widget.visible):
                    self.inventory_is_not_loaded.visible = False
                    self.inventory_is_not_loaded.update()
                    self.inventory_table_widget.visible = True
                    self.inventory_table_widget.update()

                    self.start_all_stack_widget_button.disabled = False
                    self.start_all_stack_widget_button.expand = True
                    self.start_all_stack_widget_button.update()
                    self.update_inventory_widget_button.expand = False
                    self.update_inventory_widget_button.update()

                if self.inventory and not self.inventory_table_widget.rows:
                    self.__create_items_table()

                text_title = 'InventoryStack'
                if self.inventory:
                    amount = sum([_item.get_amount() for _item in self.inventory])
                    text_title = f'[{text_title}] Предметов: {amount}шт. Занимаю слотов: {len(self.inventory)}шт.'
                if self.page.title != text_title:
                    self.page.title = text_title
                    self.page.update()

            except:
                logger.exception('Eroor')
            finally:
                time.sleep(1)

    def __create_item_row(self, items: list[Item]):
        item = items[0]

        item_widget_datarow = ft.DataRow([])
        __row_item_info = ft.Row(spacing=1, expand=True)
        item_name_widget_container = ft.Container(url=item.market_url(), ink=True, content=__row_item_info, margin=0, padding=0)
        item_img_widget_image = ft.Image(src=item.icon_url(), width=50, height=29)
        __item_img_widget = ft.Container(width=50, height=29, content=item_img_widget_image)
        __row_item_info.controls.append(__item_img_widget)
        item_name_widget_text = ft.Text(value=item.name(), color=item.color(), size=15, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
        __item_name_widget_container = ft.Container(width=250, content=item_name_widget_text)
        __row_item_info.controls.append(__item_name_widget_container)
        item_widget_datarow.cells.append(ft.DataCell(item_name_widget_container))

        amount = sum([_item.get_amount() for _item in items])
        amount = ft.Text(f'{amount} шт.', color=item.color(), size=15, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.RIGHT)
        item_widget_datarow.cells.append(ft.DataCell(amount))

        amount_items = ft.Text(f'{len(items)} шт.', color='', size=15, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.RIGHT)
        item_widget_datarow.cells.append(ft.DataCell(amount_items))

        end_ban_marketable = item.end_ban_marketable()
        end_ban_marketable_text = end_ban_marketable if end_ban_marketable else " "
        ban_items = ft.Text(f'{end_ban_marketable_text}', color=ft.colors.RED, size=15, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True, text_align=ft.TextAlign.RIGHT)
        item_widget_datarow.cells.append(ft.DataCell(ban_items))

        stack_items = ft.FilledButton("Объединить", disabled=len(items) <= 1, on_click=lambda e, _items=items: self.__stack_items(_items))
        self.__items_button_stack[f'{item.classid}_{item.instanceid}'] = stack_items
        item_widget_datarow.cells.append(ft.DataCell(stack_items))
        return item_widget_datarow

    def __create_items_table(self):
        if not self.inventory: return
        self.inventory.sort(key=lambda x: (x.classid, x.instanceid))
        self.inventory_table_widget.rows = []

        items_classid = {}

        for item in self.inventory:
            if item.classid not in items_classid:
                items_classid[item.classid] = {}
            if item.instanceid not in items_classid[item.classid]:
                items_classid[item.classid][item.instanceid] = []
            items_classid[item.classid][item.instanceid].append(item)

        for _, dict_items in items_classid.items():
            for _, items in dict_items.items():
                item_row = self.__create_item_row(items)
                self.inventory_table_widget.rows.append(item_row)
        self.inventory_table_widget.update()

    def __load_inventory(self, *args):
        try:
            self.update_inventory_widget_button.text = 'Инвентарь обновляется'
            self.update_inventory_widget_button.disabled = True
            self.update_inventory_widget_button.update()
            inventory = common.session.get_inventory_items(appid=common.app_id, context_id=common.get_contextid_appid())
            if inventory:
                new_inventory = []
                for item in inventory.inventory:
                    new_inventory.append(Item(item))
                self.inventory = new_inventory

                self.__items_button_stack = {}
                self.inventory_table_widget.rows = []
                self.inventory_table_widget.update()
        except:
            logger.exception('InventoryStackWidget')
        finally:
            time.sleep(5)
            self.update_inventory_widget_button.text = 'Обновить инвентарь'
            self.update_inventory_widget_button.disabled = False
            if self.is_run:
                self.update_inventory_widget_button.update()

    def __stack_items(self, items: list[Item]):
        if not items: return
        if len(items) <= 0: return
        start_item = items[0]
        stack_item_button: ft.FilledButton = self.__items_button_stack[f'{start_item.classid}_{start_item.instanceid}']
        if stack_item_button and not stack_item_button.disabled:
            stack_item_button.disabled = True
            stack_item_button.color = ft.colors.GREEN
            stack_item_button.update()
        if len(items) <= 1: return

        end_ban_marketable = start_item.end_ban_marketable()
        if end_ban_marketable:
            items.sort(key=lambda x: x.pos, reverse=True)
        else:
            items.sort(key=lambda x: x.pos)
        top_item = items[0]

        for item in items:
            if not self.is_run: return
            if item.id == top_item.id: continue
            t = threading.Thread(target=common.session.stack_items, args=(
                item.rg_descriptions.appid, item.id, top_item.id, item.amount, self.__steam_token
            ))
            t.start()
            time.sleep(0.05)

        if stack_item_button and not stack_item_button.color == ft.colors.GREEN:
            stack_item_button.color = None
            stack_item_button.update()

    def __stack_inventory(self, *args):
        try:
            self.update_inventory_widget_button.disabled = True
            self.update_inventory_widget_button.update()
            self.start_all_stack_widget_button.text = "Начинаю объединять все предметы"
            self.start_all_stack_widget_button.disabled = True
            self.start_all_stack_widget_button.update()
            if not self.inventory: return
            self.inventory.sort(key=lambda x: (x.classid, x.instanceid))

            items_classid = {}

            for item in self.inventory:
                if item.classid not in items_classid:
                    items_classid[item.classid] = {}
                if item.instanceid not in items_classid[item.classid]:
                    items_classid[item.classid][item.instanceid] = []
                items_classid[item.classid][item.instanceid].append(item)

            total_items = len(self.inventory)
            iter_items = 0
            self.start_all_stack_widget_button.text = f"Найдено {total_items}шт. предметов"
            self.start_all_stack_widget_button.update()

            for _, dict_items in items_classid.items():
                if not self.is_run: return
                for _, items in dict_items.items():
                    if not self.is_run: return
                    percent = round(iter_items / total_items * 100, 2)
                    top_item: Item = items[0]
                    self.start_all_stack_widget_button.text = f"Прогресс {iter_items}/{total_items} [{percent}%] предмет {top_item.name()}"
                    self.start_all_stack_widget_button.update()

                    self.__stack_items(items)
                    iter_items += len(items)
        except:
            logger.exception('InventoryStackWidget')
        finally:
            self.start_all_stack_widget_button.text = f"Объединение предметов завершено"
            if self.page:
                self.start_all_stack_widget_button.update()
            time.sleep(5)
            self.start_all_stack_widget_button.text = f"Ожидайте загружаю инвентарь."
            if self.is_run:
                self.start_all_stack_widget_button.update()
                self.__load_inventory()
            self.start_all_stack_widget_button.text = "Объединить все предметы"
            self.start_all_stack_widget_button.disabled = False
            if self.is_run:
                self.start_all_stack_widget_button.update()

