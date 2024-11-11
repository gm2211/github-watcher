class Colors:
    # Background colors
    BG_DARKEST = "#0d1117"    # Main window background
    BG_DARKER = "#161b22"     # Section frame background
    BG_DARK = "#21262d"       # Card background
    BG_LIGHT = "#30363d"      # Button/input background
    BG_LIGHTER = "#373e47"    # Button hover

    # Text colors
    TEXT_PRIMARY = "#c9d1d9"
    TEXT_SECONDARY = "#8b949e"
    TEXT_LINK = "#58a6ff"

    # Border colors
    BORDER_DEFAULT = "#30363d"
    BORDER_MUTED = "#21262d"

    # Status colors
    SUCCESS = "#238636"
    WARNING = "#9e6a03"
    DANGER = "#da3633"
    INFO = "#1f6feb"

    # Status colors with opacity
    SUCCESS_BG = "rgba(35, 134, 54, 0.15)"
    WARNING_BG = "rgba(158, 106, 3, 0.15)"
    DANGER_BG = "rgba(218, 54, 51, 0.15)"
    INFO_BG = "rgba(31, 111, 235, 0.15)"

class Styles:
    MAIN_WINDOW = f"""
        QMainWindow {{
            background-color: {Colors.BG_DARKEST};
        }}
    """

    SECTION_FRAME = f"""
        QFrame#sectionFrame {{
            background-color: {Colors.BG_DARKER};
            border-radius: 12px;
            margin: 5px;
            border: 1px solid {Colors.BORDER_DEFAULT};
        }}
        QFrame {{
            background: transparent;
        }}
    """

    PR_CARD = f"""
        QFrame#prCard {{
            background-color: {Colors.BG_DARK};
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 12px;
            padding: 10px;
            margin: 3px 0;
        }}
        QFrame#prCard:hover {{
            background-color: {Colors.BG_LIGHT};
        }}
    """

    BUTTON = f"""
        QPushButton {{
            background-color: {Colors.BG_LIGHT};
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 6px;
            padding: 5px 10px;
            color: {Colors.TEXT_PRIMARY};
            font-size: 12px;
            height: 25px;
        }}
        QPushButton:hover {{
            background-color: {Colors.BG_LIGHTER};
        }}
    """

    CHECKBOX = f"""
        QCheckBox {{
            color: {Colors.TEXT_PRIMARY};
            font-size: 12px;
        }}
        QCheckBox::indicator {{
            width: 13px;
            height: 13px;
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 3px;
            background: {Colors.BG_DARK};
        }}
        QCheckBox::indicator:checked {{
            background: {Colors.INFO};
            border-color: {Colors.INFO};
        }}
    """

    COMBO_BOX = f"""
        QComboBox {{
            background-color: {Colors.BG_DARK};
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 6px;
            color: {Colors.TEXT_PRIMARY};
            padding: 3px 10px;
            min-width: 200px;
            font-size: 12px;
        }}
        QComboBox:hover {{
            background-color: {Colors.BG_LIGHT};
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: {Colors.BG_DARK};
            border: 1px solid {Colors.BORDER_DEFAULT};
            color: {Colors.TEXT_PRIMARY};
            selection-background-color: {Colors.BG_LIGHT};
        }}
    """

    SCROLL_AREA = f"""
        QScrollArea {{
            border: none;
            background-color: transparent;
        }}
        QScrollBar:vertical {{
            background: {Colors.BG_DARK};
            width: 10px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {Colors.BG_LIGHTER};
            min-height: 20px;
            border-radius: 5px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
            background: none;
        }}
    """ 