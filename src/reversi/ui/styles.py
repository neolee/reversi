def get_main_stylesheet():
    return """
        QMainWindow, QDialog {
            background-color: #f8f9fa;
        }
        #central_widget {
            background-color: #f8f9fa;
        }
        #app_title {
            font-size: 28px;
            font-weight: 900;
            color: #1B5E20;
            margin-bottom: 15px;
        }
        #section_header {
            font-size: 11px;
            font-weight: bold;
            color: #666;
            margin-top: 20px;
            margin-bottom: 10px;
            letter-spacing: 1.5px;
            text-transform: uppercase;
        }
        QLabel {
            color: #333333;
            font-family: ".AppleSystemUIFont", "SF Pro", "Helvetica Neue", "Segoe UI", "Arial", sans-serif;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            margin-top: 1.5em;
            padding-top: 10px;
            color: #495057;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QTextEdit {
            background-color: #ffffff;
            color: #212529;
            border: 1px solid #ced4da;
            border-radius: 6px;
            font-family: "SF Mono", "Menlo", "Monaco", "Cascadia Code", "Fira Code", "Consolas", "Courier New", monospace;
            font-size: 10px;
            padding: 5px;
        }
        QPushButton {
            background-color: #f1f3f5;
            border: 1px solid #ced4da;
            border-radius: 6px;
            padding: 8px 12px;
            min-height: 24px;
            font-weight: 600;
            color: #495057;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #e9ecef;
            border-color: #adb5bd;
        }
        QPushButton:pressed {
            background-color: #dee2e6;
        }
        QPushButton:disabled {
            background-color: #f8f9fa;
            color: #adb5bd;
            border: 1px solid #e9ecef;
        }
        #action_button {
            font-size: 12px;
            min-height: 24px;
        }
        #settings_button {
            font-size: 28px;
            padding: 2px;
            border: none;
            background: transparent;
        }
        #settings_button:hover {
            background-color: #e9ecef;
            border-radius: 6px;
        }
        #primary_button {
            background-color: #2e7d32;
            color: white;
            border: none;
            font-size: 13px;
            min-height: 24px;
        }
        #primary_button:hover {
            background-color: #388e3c;
        }
        #primary_button:disabled {
            background-color: #a5d6a7;
            color: #ffffff;
        }
        QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: white;
            border: 1px solid #ced4da;
            border-radius: 4px;
            padding: 4px 8px;
            min-height: 24px;
            color: #333;
        }
        QComboBox::item:selected {
            background-color: #2e7d32;
            color: white;
        }
        QComboBox QAbstractItemView {
            background-color: white;
            color: #333;
            border: 1px solid #ced4da;
            selection-background-color: #2e7d32;
            selection-color: white;
            outline: none;
        }
        QComboBox QAbstractItemView::item {
            min-height: 28px;
            padding-left: 8px;
            background-color: transparent;
        }
        QComboBox QAbstractItemView::item:selected {
            background-color: #2e7d32;
            color: white;
        }
        QComboBox QAbstractItemView::item:hover {
            background-color: #e8f5e9;
            color: #2e7d32;
        }
        QComboBox::drop-down {
            border: 0px;
        }
        QComboBox::down-arrow {
            width: 24px;
            height: 24px;
        }
        #dialog_header {
            font-size: 18px;
            font-weight: bold;
            color: #1B5E20;
            margin-bottom: 5px;
        }
        #info_label {
            color: #6c757d;
            font-size: 11px;
        }
        #small_label {
            font-size: 11px;
            color: #888888;
            font-weight: bold;
            letter-spacing: 1px;
        }
        #player_label {
            font-size: 18px;
            font-weight: bold;
            color: #333333;
        }
        #score_text {
            font-size: 24px;
            font-weight: 900;
            color: #202020;
            font-family: "SF Mono", "Menlo", "Monaco", "Cascadia Code", "Consolas", "Courier New", monospace;
        }
        QCheckBox {
            color: #333333;
            spacing: 8px;
            font-weight: 500;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border: 1px solid #adb5bd;
            border-radius: 3px;
            background-color: white;
        }
        QCheckBox::indicator:hover {
            border-color: #2e7d32;
        }
        QCheckBox::indicator:checked {
            background-color: #2e7d32;
            border-color: #2e7d32;
            image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='20 6 9 17 4 12'%3E%3C/polyline%3E%3C/svg%3E");
        }
        #color_label {
            font-weight: bold;
            color: #495057;
            font-size: 11px;
            letter-spacing: 0.5px;
        }
    """
