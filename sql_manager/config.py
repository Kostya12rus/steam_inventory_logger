from .sqlite_manager import sqlite_manager


def make_property(key_name: str, type_value: type = str, default_return=None):
    """
    Создаёт свойство для класса с возможностью чтения и записи значения в базу данных.

    Args:
        key_name (str): Ключевое имя для извлечения или записи в базу данных.
        type_value (type): Ожидаемый тип данных значения.
        default_return (str | None): Значение, которое будет возвращено, если значение в базе данных отсутствует.

    Returns:
        property: Свойство для класса с методами getter и setter.
    """

    def getter(self):
        """Метод для получения значения из базы данных."""
        value = sqlite_manager.get_setting(key_name)
        # Если значение существует, возвращаем его, иначе возвращаем значение по умолчанию
        return value if value is not None else default_return

    def setter(self, value):
        """Метод для записи значения в базу данных."""
        # Если значение соответствует ожидаемому типу, сохраняем его в базу данных
        if isinstance(value, type_value):
            sqlite_manager.save_setting(key_name, value)

    return property(getter, setter)


class Setting:
    session = make_property('session', bytes, b'')
    login = make_property('login', str, '')
    password = make_property('password', str, '')
    default_currency = make_property('default_currency', int, 1)
    app_id = make_property('app_id', int, 2923300)
    prefix_currency = make_property('prefix_currency', str, '')
    suffix_currency = make_property('suffix_currency', str, 'руб')

    current_items_price = make_property('current_items_price', dict, {})
    current_items_price_old = make_property('current_items_price_old', dict, {})
    items_nameid = make_property('items_nameid', dict, {})


setting = Setting()
