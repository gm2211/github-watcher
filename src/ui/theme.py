class Colors:
    # GitHub Dark Theme Colors (exact values from GitHub's CSS)
    BG_DARKEST = "#0d1117"  # Canvas default (main background)
    BG_DARKER = "#161b22"  # Surface overlay (section background)
    BG_DARK = "#21262d"  # Surface primary (card background)
    BG_LIGHT = "#30363d"  # Surface secondary (button background)
    BG_LIGHTER = "#373e47"  # Surface tertiary (button hover)
    BG_HEADER = "#010409"  # Header background (even darker than darkest)

    # Text colors
    TEXT_PRIMARY = "#c9d1d9"  # Default text
    TEXT_SECONDARY = "#8b949e"  # Muted text
    TEXT_LINK = "#58a6ff"  # Links and accents
    TEXT_HEADER = "#e6edf3"  # Brighter text for header
    TEXT_HEADER_SECONDARY = "#7d8590"  # Secondary text in header

    # Border colors
    BORDER_DEFAULT = "#30363d"  # Default borders
    BORDER_MUTED = "#21262d"  # Muted borders
    BORDER_HEADER = "#21262d"  # Header border
    BORDER_HEADER_BOTTOM = "#30363d"  # Bottom border for header

    # Status colors
    SUCCESS = "#2ea043"  # Success
    WARNING = "#d29922"  # Warning
    DANGER = "#f85149"  # Danger
    INFO = "#2f81f7"  # Info/Accent

    # Status colors with opacity
    SUCCESS_BG = "rgba(46, 160, 67, 0.15)"
    WARNING_BG = "rgba(210, 153, 34, 0.15)"
    DANGER_BG = "rgba(248, 81, 73, 0.15)"
    INFO_BG = "rgba(47, 129, 247, 0.15)"


class Styles:
    SECTION_FRAME_CSS_CLASS = "sectionFrame"
    MAIN_WINDOW = f"""
        QMainWindow {{
            background-color: {Colors.BG_DARKEST};
            color: {Colors.TEXT_PRIMARY};
        }}
        QWidget {{
            color: {Colors.TEXT_PRIMARY};
        }}
    """

    HEADER = f"""
        QWidget#headerContainer {{
            background-color: {Colors.BG_HEADER};
            border-bottom: 1px solid {Colors.BORDER_HEADER_BOTTOM};
            margin-bottom: 24px;
        }}
        QLabel#headerTitle {{
            color: {Colors.TEXT_HEADER};
            font-size: 20px;
            font-weight: 600;
            margin-right: 16px;
        }}
        QLabel#loadingLabel {{
            color: {Colors.INFO};
            font-size: 12px;
            padding: 0 5px;
        }}
        QPushButton {{
            color: {Colors.TEXT_HEADER_SECONDARY};
            background: transparent;
            border: none;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 500;
            margin-bottom: 8px;
        }}
        QPushButton:hover {{
            background-color: {Colors.BG_DARK};
            color: {Colors.TEXT_HEADER};
        }}
    """

    FILTERS = f"""
        QWidget#filtersBar {{
            background-color: {Colors.BG_HEADER};
            padding: 0px 16px 16px 16px;
            margin: 0;
        }}
        QLabel {{
            color: {Colors.TEXT_HEADER_SECONDARY};
            font-size: 13px;
            font-weight: 500;
        }}
        QCheckBox {{
            color: {Colors.TEXT_HEADER_SECONDARY};
            font-size: 13px;
            font-weight: 500;
            spacing: 6px;
            padding: 2px 4px;
            border-radius: 4px;
        }}
        QCheckBox:hover {{
            color: {Colors.TEXT_HEADER};
            background-color: {Colors.BG_DARK};
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 4px;
            background: {Colors.BG_DARK};
        }}
        QCheckBox::indicator:checked {{
            background: {Colors.INFO};
            border-color: {Colors.INFO};
        }}
        QCheckBox::indicator:hover {{
            border-color: {Colors.TEXT_HEADER};
        }}
        QComboBox {{
            background-color: {Colors.BG_DARK};
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 4px;
            padding: 2px 8px;
            color: {Colors.TEXT_HEADER_SECONDARY};
            font-size: 13px;
            font-weight: 500;
            min-width: 150px;
        }}
        QComboBox:hover {{
            border-color: {Colors.TEXT_HEADER};
            color: {Colors.TEXT_HEADER};
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox::down-arrow {{
            image: none;
            width: 0px;
        }}
    """

    SECTION_FRAME = f"""
        QFrame#{SECTION_FRAME_CSS_CLASS} {{
            background-color: {Colors.BG_DARK};
            border-radius: 6px;
            margin: 5px;
            border: 1px solid {Colors.BORDER_DEFAULT};
        }}
        QFrame {{
            background: transparent;
        }}
        QLabel {{
            color: {Colors.TEXT_PRIMARY};
        }}
    """

    PR_CARD = f"""
        QFrame#prCard {{
            background-color: {Colors.BG_DARK};
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 6px;
            padding: 10px;
            margin: 3px 0;
        }}
        QFrame#prCard:hover {{
            border-color: {Colors.TEXT_LINK};
            background-color: {Colors.BG_LIGHT};
        }}
        QLabel {{
            color: {Colors.TEXT_PRIMARY};
        }}
        QLabel[link=true] {{
            color: {Colors.TEXT_LINK};
        }}
    """

    BUTTON = f"""
        QPushButton {{
            background-color: {Colors.BG_LIGHT};
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 6px;
            padding: 5px 16px;
            color: {Colors.TEXT_PRIMARY};
            font-size: 12px;
            height: 28px;
            min-width: 70px;
        }}
        QPushButton:hover {{
            background-color: {Colors.BG_LIGHTER};
            border-color: {Colors.TEXT_LINK};
        }}
    """

    CHECKBOX = f"""
        QCheckBox {{
            color: {Colors.TEXT_PRIMARY};
            font-size: 12px;
            spacing: 5px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 6px;
            background: {Colors.BG_DARKEST};
        }}
        QCheckBox::indicator:hover {{
            border-color: {Colors.TEXT_LINK};
        }}
        QCheckBox::indicator:checked {{
            background: {Colors.INFO};
            border-color: {Colors.INFO};
        }}
    """

    COMBO_BOX = f"""
        QComboBox {{
            background-color: {Colors.BG_DARKEST};
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 6px;
            color: {Colors.TEXT_PRIMARY};
            padding: 5px 10px;
            min-width: 200px;
            font-size: 12px;
        }}
        QComboBox:hover {{
            border-color: {Colors.TEXT_LINK};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: {Colors.BG_DARKEST};
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 6px;
            color: {Colors.TEXT_PRIMARY};
            selection-background-color: {Colors.BG_DARK};
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 5px 10px;
            min-height: 25px;
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {Colors.BG_DARK};
        }}
    """

    SCROLL_AREA = f"""
        QScrollArea {{
            border: none;
            background-color: transparent;
        }}
        QScrollBar:vertical {{
            background: {Colors.BG_DARKEST};
            width: 8px;
            margin: 0;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {Colors.BG_LIGHTER};
            min-height: 20px;
            border-radius: 4px;
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
            background: none;
        }}
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {{
            background: none;
        }}
    """

    DIALOG = f"""
        QDialog {{
            background-color: {Colors.BG_DARKEST};
            color: {Colors.TEXT_PRIMARY};
        }}
        QLabel {{
            color: {Colors.TEXT_PRIMARY};
        }}
        QGroupBox {{
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 6px;
            margin-top: 1em;
            padding-top: 1em;
            color: {Colors.TEXT_PRIMARY};
            background-color: {Colors.BG_DARK};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px;
            background-color: {Colors.BG_DARK};
        }}
        QTextEdit {{
            background-color: {Colors.BG_DARKEST};
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 6px;
            color: {Colors.TEXT_PRIMARY};
            padding: 5px;
        }}
        QSpinBox {{
            background-color: {Colors.BG_DARKEST};
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 6px;
            color: {Colors.TEXT_PRIMARY};
            padding: 5px;
        }}
    """
