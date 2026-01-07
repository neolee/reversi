def get_main_stylesheet():
    return """
        #central_widget {
            background-color: #f5f5f5;
        }
        #app_title {
            font-size: 32px;
            font-weight: 900;
            color: #1B5E20;
            margin-bottom: 5px;
        }
        #section_header {
            font-size: 11px;
            font-weight: bold;
            color: #888;
            margin-top: 15px;
            margin-bottom: 5px;
            letter-spacing: 1px;
        }
        QLabel {
            color: #202020;
        }
        QTextEdit {
            background-color: #ffffff;
            color: #333333;
            border: 1px solid #d0d0d0;
            border-radius: 4px;
            font-family: 'SF Mono', 'Courier New', monospace;
            font-size: 10px;
        }
        QPushButton {
            background-color: #e8e8e8;
            border: 1px solid #c8c8c8;
            border-radius: 6px;
            padding: 8px;
            font-weight: bold;
            color: #333333;
        }
        QPushButton:hover {
            background-color: #dcdcdc;
        }
        QPushButton:pressed {
            background-color: #cfcfcf;
        }
        QPushButton:disabled {
            background-color: #f0f0f0;
            color: #bbbbbb;
            border: 1px solid #e0e0e0;
        }
        #action_button {
            font-size: 12px;
            min-height: 24px;
        }
        #primary_button {
            background-color: #2e7d32;
            color: white;
            border: none;
            font-size: 12px;
            min-height: 24px;
        }
        #primary_button:hover {
            background-color: #388e3c;
        }
        #primary_button:disabled {
            background-color: #a5d6a7;
            color: #ffffff;
        }
    """
