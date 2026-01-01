from zandev_textual_widgets import MenuHeader
from zandev_textual_widgets.menu import Menu
from zandev_textual_widgets.menu import MenuBar
from zandev_textual_widgets.menu import MenuItem


file_menu = Menu(
    MenuItem('Open File', menu_action='screen.open_file'),
    MenuItem('Open Device', disabled=True),
    MenuItem('Disconnect', disabled=True),
    MenuItem('Exit', menu_action='screen.exit'),
    name='File',
    id='file_menu',
)
edit_menu = Menu(
    MenuItem('Transactions', disabled=True),
    MenuItem('Accounts', disabled=True),
    MenuItem('Labels', disabled=True),
    name='Edit',
    id='edit_menu',
)
view_menu = Menu(
    MenuItem('Statistics', menu_action='screen.statistics'),
    MenuItem('Cached Quotes', menu_action='screen.cached_quotes'),
    name='View',
    id='view_menu',
)
tools_menu = Menu(
    MenuItem('Fetch Quotes', menu_action='screen.fetch_quotes'),
    MenuItem('Change Currency', menu_action='screen.change_currency', disabled=True),
    name='Tools',
    id='tools_menu',
)
help_menu = Menu(
    MenuItem('About', disabled=True),
    name='Help',
    id='help_menu',
)

bar = MenuBar(
    MenuHeader(name='🏠'),
    MenuHeader(name='File', menu_id='file_menu'),
    MenuHeader(name='Edit', menu_id='edit_menu'),
    MenuHeader(name='View', menu_id='view_menu'),
    MenuHeader(name='Tools', menu_id='tools_menu'),
    MenuHeader(name='Help', menu_id='help_menu'),
)
