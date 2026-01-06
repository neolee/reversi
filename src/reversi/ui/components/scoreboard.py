from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt

class ScoreboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)

        self.black_label = QLabel("Black (Human): 2")
        self.white_label = QLabel("White (AI): 2")
        self.status_label = QLabel("Black's Turn")

        layout.addWidget(self.black_label)
        layout.addStretch()
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.white_label)

        self.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
            }
        """)

    def update_scores(self, black, white):
        self.black_label.setText(f"Black: {black}")
        self.white_label.setText(f"White: {white}")

    def set_status(self, text):
        self.status_label.setText(text)
