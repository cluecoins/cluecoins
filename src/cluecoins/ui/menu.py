from zandev_textual_widgets import MenuHeader
from zandev_textual_widgets.menu import MenuBar


def bar() -> MenuBar:
    return MenuBar(
        MenuHeader(name='File', menu_id='file_menu'),
        MenuHeader(name='Edit', menu_id='edit_menu'),
        MenuHeader(name='View', menu_id='view_menu'),
        MenuHeader(name='Tools', menu_id='tools_menu'),
        MenuHeader(name='Help', menu_id='help_menu'),
    )
