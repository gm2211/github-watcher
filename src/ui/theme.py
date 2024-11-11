class Colors:
    # Main Background Colors - Softer dark theme
    BG_DARKEST = "#0d1117"  # Main background - GitHub dark
    BG_DARKER = "#161b22"   # Secondary background
    BG_DARK = "#1c2128"     # Softer dark for cards
    BG_LIGHT = "#2d333b"    # Lighter background for interactive elements
    BG_LIGHTER = "#373e47"  # Hover states
    BG_HEADER = "#1c2128"   # Header background

    # Text Colors - Improved contrast and readability
    TEXT_PRIMARY = "#e6edf3"    # Main text - Brighter for better contrast
    TEXT_SECONDARY = "#7d8590"  # Secondary text - Softer gray
    TEXT_LINK = "#539bf5"       # Links - More vibrant blue
    TEXT_HEADER = "#f0f3f6"     # Header text - Very bright for emphasis
    TEXT_HEADER_SECONDARY = "#8b949e"  # Secondary header text

    # Border Colors - Subtle depth
    BORDER_DEFAULT = "#373e47"  # Default borders - More visible
    BORDER_MUTED = "#2d333b"    # Subtle borders
    BORDER_HEADER = "#2d333b"   # Header border
    BORDER_HEADER_BOTTOM = "#373e47"  # Header bottom border

    # Status Colors - More vibrant
    SUCCESS = "#3fb950"  # Success - Brighter green
    WARNING = "#d29922"  # Warning - Warm yellow
    DANGER = "#f85149"   # Danger - Bright red
    INFO = "#58a6ff"     # Info - Bright blue

    # Status Background Colors - Improved contrast
    SUCCESS_BG = "rgba(46, 160, 67, 0.2)"    # Success bg - More visible
    WARNING_BG = "rgba(210, 153, 34, 0.2)"   # Warning bg
    DANGER_BG = "rgba(248, 81, 73, 0.2)"     # Danger bg
    INFO_BG = "rgba(88, 166, 255, 0.2)"      # Info bg

    # Interactive States - New
    HOVER_OVERLAY = "rgba(177, 186, 196, 0.12)"  # Hover state overlay
    ACTIVE_BG = "#323941"    # Active/selected state
    FOCUS_BORDER = "#58a6ff" # Focus state border


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
            border-radius: 8px;
            margin-bottom: 0px;
            padding-bottom: 0px;
            border: 1px solid {Colors.BORDER_HEADER};
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
            background: {Colors.BG_DARK};
            border: 1px solid {Colors.BORDER_DEFAULT};
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {Colors.BG_LIGHT};
            color: {Colors.TEXT_HEADER};
            border-color: {Colors.BORDER_HEADER};
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
            padding: 4px 8px;
            border-radius: 6px;
            background: {Colors.BG_DARK};
            border: 1px solid {Colors.BORDER_DEFAULT};
        }}
        QCheckBox:hover {{
            color: {Colors.TEXT_HEADER};
            background-color: {Colors.BG_LIGHT};
            border-color: {Colors.BORDER_HEADER};
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 4px;
            background: {Colors.BG_DARKER};
        }}
        QCheckBox::indicator:checked {{
            background: {Colors.INFO};
            border-color: {Colors.INFO};
        }}
        QCheckBox::indicator:hover {{
            border-color: {Colors.INFO};
        }}
        QComboBox {{
            background-color: {Colors.BG_DARK};
            border: 1px solid {Colors.BORDER_DEFAULT};
            border-radius: 6px;
            padding: 4px 8px;
            color: {Colors.TEXT_HEADER_SECONDARY};
            font-size: 13px;
            font-weight: 500;
            min-width: 150px;
        }}
        QComboBox:hover {{
            border-color: {Colors.INFO};
            color: {Colors.TEXT_HEADER};
            background-color: {Colors.BG_LIGHT};
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
            border-radius: 8px;
            margin: 5px;
            border: 1px solid {Colors.BORDER_DEFAULT};
        }}
        QFrame#{SECTION_FRAME_CSS_CLASS}:hover {{
            border-color: {Colors.BORDER_HEADER};
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
