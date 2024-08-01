import time
import threading
import webbrowser

import flet as ft

from flet_manager import common
from sql_manager.config import setting
from flet_manager.shared_data import MarketItem
from logger_utility.logger_config import logger

class CraftManagerWidget(ft.Column):
    def __init__(self):
        super().__init__()
        self.is_run = False
        self.isolated = True
        self.expand = True
        self.alignment = ft.MainAxisAlignment.START
        self.__items: list[MarketItem] = []
        self.__example_item: MarketItem = None
        self.__crafts = {}
        self.__craft_widgets = {}
        self.__is_loading = False
        self.__app_id = 3017120
        self.spacing = 0

        self.title_widget_text = ft.Text(f'Система крафтов {common.get_current_appid_name(self.__app_id)}', size=24, color=ft.colors.BLUE, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, expand=True)
        body_title_widget_row = ft.Row(controls=[self.title_widget_text], alignment=ft.MainAxisAlignment.CENTER, run_spacing=0)

        self.widget_title_1 = ft.Text('Используются в крафте', size=18)
        self.widget_title_2 = ft.Text('Получаются в крафте', size=18)
        self.widget_title_3 = ft.Text('Профит крафта', size=18)
        self.widget_title_4 = ft.Text('Управление', size=18)
        self.table_title_widget = ft.Row(alignment=ft.MainAxisAlignment.CENTER, run_spacing=0,
                            controls=[
                                ft.Row(expand=True, alignment=ft.MainAxisAlignment.CENTER, controls=[self.widget_title_1]),
                                ft.Row(expand=True, alignment=ft.MainAxisAlignment.CENTER, controls=[self.widget_title_2]),
                                ft.Container(width=200, content=ft.Row(expand=True, alignment=ft.MainAxisAlignment.CENTER, controls=[self.widget_title_3])),
                                ft.Container(width=200, content=ft.Row(expand=True, alignment=ft.MainAxisAlignment.CENTER, controls=[self.widget_title_4])),
                                ft.VerticalDivider(),
                            ])


        self.table_widget = ft.Column(expand=True)

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
        self.create_widget_button = ft.FilledButton('Создать крафт', expand=False, on_click=self.create_craft, disabled=True)
        buttons_widget_row = ft.Row(spacing=0, controls=[
            self.update_items_widget_button,
            self.create_widget_button
        ])

        self.controls = [
            body_title_widget_row,
            ft.Divider(),
            self.table_title_widget,
            ft.Divider(),
            self.body_widget_column,
            ft.Divider(),
            buttons_widget_row,
        ]

    def did_mount(self):
        self.is_run = True
        threading.Thread(target=self.__update).start()
        self.safe_update(self)
        self.update_clear()
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
        if self.__app_id == common.app_id:
            self.__load_crafts()
            if not self.__craft_widgets:
                self.update_craft_list()
            self.update_items_widget_button.disabled = False
            self.safe_update(self.update_items_widget_button)
        else:
            self.update_items_widget_button.disabled = True
            self.safe_update(self.update_items_widget_button)

    def __update_widgets(self):
        text_title = 'CraftManager: '
        if self.__app_id != common.app_id:
            text_title += 'На данный момент работает только с игрой Egg Surprise'

            if not self.dont_has_access_widget.visible:
                self.dont_has_access_widget.visible = True
                self.safe_update(self.dont_has_access_widget)
            if self.is_not_loaded_widget.visible:
                self.is_not_loaded_widget.visible = False
                self.safe_update(self.is_not_loaded_widget)
            if self.table_widget.visible:
                self.table_widget.visible = False
                self.safe_update(self.table_widget)
            if not self.create_widget_button.disabled:
                self.create_widget_button.disabled = True
                self.safe_update(self.create_widget_button)
            if self.table_title_widget.visible:
                self.table_title_widget.visible = False
                self.safe_update(self.table_title_widget)
        else:
            if self.dont_has_access_widget.visible:
                self.dont_has_access_widget.visible = False
                self.safe_update(self.dont_has_access_widget)

            if not self.__items:
                text_title += 'Предметы не загружены'
                if not self.is_not_loaded_widget.visible:
                    self.is_not_loaded_widget.visible = True
                    self.safe_update(self.is_not_loaded_widget)
                if self.table_widget.visible:
                    self.table_widget.visible = False
                    self.safe_update(self.table_widget)
                if not self.create_widget_button.disabled:
                    self.create_widget_button.disabled = True
                    self.safe_update(self.create_widget_button)
                if self.table_title_widget.visible:
                    self.table_title_widget.visible = False
                    self.safe_update(self.table_title_widget)
            else:
                if self.is_not_loaded_widget.visible:
                    self.is_not_loaded_widget.visible = False
                    self.safe_update(self.is_not_loaded_widget)
                if not self.table_widget.visible:
                    self.table_widget.visible = True
                    self.safe_update(self.table_widget)
                if self.create_widget_button.disabled:
                    self.create_widget_button.disabled = False
                    self.safe_update(self.create_widget_button)
                if not self.table_title_widget.visible:
                    self.table_title_widget.visible = True
                    self.safe_update(self.table_title_widget)

        if self.page.title != text_title:
            self.page.title = text_title
            self.safe_update(self.page)
    def __update(self):
        while self.is_run:
            try:
                self.__update_widgets()
            except:
                logger.exception('ERROR UPDATE CraftManagerWidget')
            finally:
                time.sleep(1)

    def create_craft(self, *args, craft_index: str = None):
        if not craft_index:
            max_value = max([int(key) for key in self.__crafts.keys()], default=-1)
            craft_index = str(max_value+1)
        if craft_index not in self.__crafts:
            self.__crafts[craft_index] = {}
        if craft_index not in self.__craft_widgets:
            self.__craft_widgets[craft_index] = {}

        items_input_widget = ft.Column(controls=[], expand=True, spacing=3)
        button_add_input_items = ft.FilledButton("Добавить предмет", expand=True, height=25)
        button_add_input_items.on_click = lambda e, _craft_index=craft_index: self.__add_new_item(_craft_index, True)
        __item_input_column_widgets = ft.Column(expand=True, spacing=3,
                                                controls=[ft.Row(controls=[button_add_input_items]), ft.Row(controls=[items_input_widget])])

        items_output_widget = ft.Column(controls=[], expand=True, spacing=3)
        button_add_output_items = ft.FilledButton("Добавить предмет", expand=True, height=25)
        button_add_output_items.on_click = lambda e, _craft_index=craft_index: self.__add_new_item(_craft_index, False)
        __item_output_column_widgets = ft.Column(expand=True, spacing=3,
                                                 controls=[ft.Row(controls=[button_add_output_items]), ft.Row(controls=[items_output_widget])])

        __item_total_title_widget = ft.Text('Профит крафта', text_align=ft.TextAlign.CENTER, expand=True)
        __profit_column = ft.Column(controls=[], expand=True, spacing=0)
        __item_total_widget = ft.Column(expand=True, alignment=ft.MainAxisAlignment.CENTER, spacing=0,
                                        controls=[ft.Row(controls=[__profit_column]), ]) #ft.Row(controls=[__item_total_title_widget]),

        button_del_craft = ft.FilledButton("Удалить крафт", expand=True, height=25)


        craft_row = ft.Row(alignment=ft.MainAxisAlignment.CENTER, run_spacing=0,
                           controls=[
                               ft.Row(expand=True, alignment=ft.MainAxisAlignment.CENTER, controls=[__item_input_column_widgets]),
                               ft.Row(expand=True, alignment=ft.MainAxisAlignment.CENTER, controls=[__item_output_column_widgets]),
                               ft.Container(width=200, content=ft.Row(expand=True, alignment=ft.MainAxisAlignment.CENTER, controls=[__item_total_widget])),
                               ft.Container(width=200, content=ft.Row(expand=True, alignment=ft.MainAxisAlignment.CENTER, controls=[button_del_craft])),
                               ft.VerticalDivider(),
                           ])
        divider = ft.Divider()

        self.__craft_widgets[craft_index]['total_price'] = __profit_column
        self.__craft_widgets[craft_index]['input_item'] = items_input_widget
        self.__craft_widgets[craft_index]['output_item'] = items_output_widget
        self.__craft_widgets[craft_index]['data_cell_input_item'] = __item_input_column_widgets
        self.__craft_widgets[craft_index]['data_cell_output_item'] = __item_output_column_widgets
        self.__craft_widgets[craft_index]['datarow'] = craft_row

        self.table_widget.controls.append(craft_row)
        self.table_widget.controls.append(divider)
        self.safe_update(self.table_widget)

        def del_craft():
            self.__craft_widgets.pop(craft_index)
            self.__crafts.pop(craft_index)
            craft_row.visible = False
            divider.visible = False
            self.safe_update(self.table_widget)
            self.__save_crafts()
        button_del_craft.on_click = lambda e: del_craft()

    def __update_total_profit(self, craft_index):
        craft_data = self.__crafts.get(craft_index, None)
        if not craft_data: return
        craft_widgets_data = self.__craft_widgets.get(craft_index, None)
        if not craft_widgets_data: return
        craft_widgets_data['total_price'].controls = []
        if not craft_data.get('input_item', None) and not craft_data.get('output_item', None): return

        max_theoretical_profit = 0
        max_theoretical_costs = 0
        expected_profit = 0
        expected_costs = 0

        for is_input_item, items in craft_data.items():
            for item_data in items.values():
                sell_price = int(item_data.get('sell_price', 0))
                count = int(item_data.get('count', 0))
                percent = float(item_data.get('percent', 100))
                total_price = sell_price * count

                if is_input_item == 'input_item':
                    max_theoretical_costs += total_price if percent < 100 else 0
                    expected_costs += total_price * (100 - percent) / 100 if percent < 100 else 0
                elif is_input_item == 'output_item':
                    max_theoretical_profit += total_price if percent > 0 else 0
                    expected_profit += total_price * percent / 100 if percent > 0 else 0

        net_expected_income = expected_profit - expected_costs

        if not self.__example_item and self.__items:
            self.__example_item = next((item for item in self.__items if item.sell_price_text), None)

        plus_text = ft.Text(
            f"Макс. возможная прибыль: {round(max_theoretical_profit / 100, 2) if not self.__example_item else self.__example_item.generate_number_in_currency(max_theoretical_profit)}",
            text_align=ft.TextAlign.CENTER, expand=True, size=12
        )
        minus_text = ft.Text(
            f"Макс. возможные затраты: {round(max_theoretical_costs / 100, 2) if not self.__example_item else self.__example_item.generate_number_in_currency(max_theoretical_costs)}",
            text_align=ft.TextAlign.CENTER, expand=True, size=12
        )

        average_profit_text_visible = max_theoretical_profit != expected_profit
        average_profit_text = ft.Text(
            f"Прогнозируемая прибыль: {round(expected_profit / 100, 2) if not self.__example_item else self.__example_item.generate_number_in_currency(expected_profit)}",
            text_align=ft.TextAlign.CENTER, expand=True, size=12
        )
        average_loss_text_visible = max_theoretical_costs != expected_costs
        average_loss_text = ft.Text(
            f"Прогнозируемые потери: {round(expected_costs / 100, 2) if not self.__example_item else self.__example_item.generate_number_in_currency(expected_costs)}",
            text_align=ft.TextAlign.CENTER, expand=True, size=12
        )
        potential_income_text = ft.Text(
            f"Потенциальный доход: {round(net_expected_income / 100, 2) if not self.__example_item else self.__example_item.generate_number_in_currency(net_expected_income)}",
            text_align=ft.TextAlign.CENTER, expand=True, size=12
        )
        if self.__example_item:
            plus_text.tooltip = f'С учетом комиссий: {self.__example_item.calcutate_commision(max_theoretical_profit)}'
            average_profit_text.tooltip = f'С учетом комиссий: {self.__example_item.calcutate_commision(expected_profit)}'

            profit_after_commision = self.__example_item.calcutate_commision_integer(expected_profit if average_profit_text_visible else max_theoretical_profit)
            total_price = self.__example_item.calcutate_commision(profit_after_commision-(expected_costs if average_loss_text_visible else max_theoretical_costs))
            potential_income_text.tooltip = f'С учетом комиссий: {total_price}'

        craft_widgets_data['total_price'].controls = [
            ft.Row(controls=[plus_text]),
            ft.Row(controls=[minus_text]),

            ft.Divider(visible=average_profit_text_visible or average_loss_text_visible),
            ft.Row(controls=[average_profit_text], visible=average_profit_text_visible),
            ft.Row(controls=[average_loss_text], visible=average_loss_text_visible),

            ft.Divider(),
            ft.Row(controls=[potential_income_text])
        ]

        self.safe_update(craft_widgets_data['total_price'])

    def update_craft_list(self):
        if not self.__crafts: return
        self.table_widget.controls = []
        self.__craft_widgets = {}

        if self.__items:
            for craft_index, craft_data in self.__crafts.items():
                for is_input in ['input_item', 'output_item']:
                    if is_input in craft_data:
                        for market_hash_name, item_data in craft_data[is_input].items():
                            item_market: MarketItem = next((item for item in self.__items if item.market_hash_name() == market_hash_name), None)
                            if not item_market: continue
                            self.__crafts[craft_index][is_input][market_hash_name]['item_name'] = item_market.name
                            self.__crafts[craft_index][is_input][market_hash_name]['sell_price'] = item_market.sell_price
                            self.__crafts[craft_index][is_input][market_hash_name]['sell_price_text'] = item_market.sell_price_text
                            self.__crafts[craft_index][is_input][market_hash_name]['market_url'] = item_market.market_url()
                            self.__crafts[craft_index][is_input][market_hash_name]['color'] = item_market.color()
                            self.__crafts[craft_index][is_input][market_hash_name]['icon_url'] = item_market.icon_url()
            self.__save_crafts()

        for craft_index in self.__crafts:
            if craft_index not in self.__craft_widgets:
                self.create_craft(craft_index=craft_index)
            for is_input in ['input_item', 'output_item']:
                if is_input in self.__crafts[craft_index]:
                    for market_hash_name, item_data in self.__crafts[craft_index][is_input].items():
                        self.__create_item(craft_index, is_input, item_data)
            self.__update_total_profit(craft_index)

        self.safe_update(self.table_widget)


    def __create_item(self, craft_index, is_input, item_dict: dict):
        widget: ft.Column = self.__craft_widgets.get(craft_index, {}).get(is_input)
        if not widget: return

        def change_count(new_count: ft.TextField):
            try:
                self.__crafts[craft_index][is_input][item_dict.get('market_hash_name')]['count'] = int(new_count.value)
                self.__save_crafts()
                self.__update_total_profit(craft_index)
            except:
                pass

        def change_precent(new_percent: ft.TextField):
            try:
                new_percent_value = new_percent.value.replace(',', '.')
                self.__crafts[craft_index][is_input][item_dict.get('market_hash_name')]['percent'] = float(new_percent_value)
                self.__save_crafts()
                self.__update_total_profit(craft_index)
            except:
                pass

        def del_item(main_widget: ft.Row):
            try:
                self.__crafts[craft_index][is_input].pop(item_dict.get('market_hash_name'))
                self.__save_crafts()
                main_widget.visible = False
                self.safe_update(main_widget)
                self.__update_total_profit(craft_index)
            except:
                pass

        item_image = ft.Image(src=item_dict.get('icon_url'), width=30, height=30)
        item_name = ft.Text(item_dict.get('item_name'), color=item_dict.get('color'), expand=True, max_lines=2, text_align=ft.TextAlign.CENTER)
        item_price = ft.TextField(label='Цена', value=f"{item_dict.get('sell_price_text', 0)}", width=120, dense=True, text_size=12, text_align=ft.TextAlign.RIGHT, disabled=True)

        if is_input == 'output_item':
            if not self.__example_item and self.__items:
                self.__example_item = next((item for item in self.__items if item.sell_price_text), None)
            item_price.tooltip = f'С учетом комиссий: {self.__example_item.calcutate_commision(int(item_dict.get("sell_price", 0)))}' if self.__example_item else ''

        item_count = ft.TextField(label='Кол-во', value=f"{item_dict.get('count', 0)}", width=80, dense=True, text_size=12, text_align=ft.TextAlign.RIGHT)
        item_count.on_change = lambda e: change_count(new_count=item_count)
        item_percent = ft.TextField(label='Процент', value=f"{item_dict.get('percent', 0)}", width=80, dense=True, text_size=12, text_align=ft.TextAlign.RIGHT,
                                    suffix_text='%', tooltip='Процент что предмет вернется/получится после крафта')
        item_percent.on_change = lambda e: change_precent(new_percent=item_percent)
        item_del = ft.IconButton(icon_size=25, icon=ft.icons.CLOSE, icon_color=ft.colors.RED_400, tooltip='Удалить')
        item_open_web = ft.IconButton(icon_size=25, icon=ft.icons.WEB, icon_color=ft.colors.RED_400, tooltip='Открыть торговую площадку')
        item_open_web.on_click = lambda e: webbrowser.open(item_dict.get('market_url'))

        __item_row_main = ft.Row(spacing=0)
        __item_row_main.controls = [item_image, item_name, item_price, item_count, item_percent, item_open_web, item_del]

        item_del.on_click = lambda e: del_item(main_widget=__item_row_main)

        widget.controls.append(__item_row_main)
        self.safe_update(widget)

    def __add_new_item(self, craft_index: str, is_input: bool):
        item_dict = 'input_item' if is_input else 'output_item'
        if craft_index not in self.__crafts:
            self.__crafts[craft_index] = {}
        if item_dict not in self.__crafts[craft_index]:
            self.__crafts[craft_index][item_dict] = {}

        def __select_item(item: MarketItem):
            __item_dict = {
                'item_name': item.name,
                'market_hash_name': item.market_hash_name(),
                'icon_url': item.icon_url(),
                'market_url': item.market_url(),
                'count': 1,
                'percent': 100,
                'color': item.color(),
                'sell_price': item.sell_price,
                'sell_price_text': item.sell_price_text
            }
            self.__crafts[craft_index][item_dict][item.market_hash_name()] = __item_dict
            self.__save_crafts()
            self.__create_item(craft_index, item_dict, __item_dict)
            self.__update_total_profit(craft_index)

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
        if self.__app_id != common.app_id: return

        self.update_items_widget_button.disabled = True
        self.update_items_widget_button.text = 'Ожидайте я обновляю предметы и цены'
        self.safe_update(self.update_items_widget_button)
        market_list = common.session.get_game_market_list(appid=self.__app_id)
        build_items = [MarketItem(item) for item in market_list]
        self.__items = [item for item in build_items if not item.is_bug_item() and item.is_current_game(self.__app_id)]
        self.__items.sort(key=lambda item: item.name)

        self.update_items_widget_button.text = 'Обновляю цены в текущих крафтах'
        self.safe_update(self.update_items_widget_button)
        self.update_craft_list()

        time.sleep(5)
        if self.__items:
            self.__example_item = next((item for item in self.__items if item.sell_price_text), None)
            self.create_widget_button.disabled = False
            self.create_widget_button.expand = True
            self.safe_update(self.create_widget_button)
            self.update_items_widget_button.expand = False

        self.update_items_widget_button.disabled = False
        self.update_items_widget_button.text = 'Обновить предметы и цены'
        self.safe_update(self.update_items_widget_button)

