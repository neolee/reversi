from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class ScoreboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(20, 15, 20, 15)

        # Row 1: Small Labels
        row1 = QHBoxLayout()
        self.label_black_title = QLabel("BLACK")
        self.label_status = QLabel("Game Waiting")
        self.label_white_title = QLabel("WHITE")

        for label in [self.label_black_title, self.label_status, self.label_white_title]:
            label.setObjectName("small_label")

        row1.addWidget(self.label_black_title, 1, Qt.AlignmentFlag.AlignLeft)
        row1.addWidget(self.label_status, 2, Qt.AlignmentFlag.AlignCenter)
        row1.addWidget(self.label_white_title, 1, Qt.AlignmentFlag.AlignRight)

        # Row 2: Large Labels
        row2 = QHBoxLayout()
        self.label_black_player = QLabel("Human ●")
        self.label_score = QLabel("2 : 2")
        self.label_white_player = QLabel("○ AI")

        self.label_black_player.setObjectName("player_label")
        self.label_score.setObjectName("score_text")
        self.label_white_player.setObjectName("player_label")

        row2.addWidget(self.label_black_player, 1, Qt.AlignmentFlag.AlignLeft)
        row2.addWidget(self.label_score, 2, Qt.AlignmentFlag.AlignCenter)
        row2.addWidget(self.label_white_player, 1, Qt.AlignmentFlag.AlignRight)

        main_layout.addLayout(row1)
        main_layout.addLayout(row2)

    def update_scores(self, black, white):
        self.label_score.setText(f"{black} : {white}")

    def set_status(self, turn_color, player_name, is_human):
        role = "Human" if is_human else "AI"
        color_name = "Black" if turn_color == "BLACK" else "White"
        text = f"{color_name} ({player_name}) to move"
        self.label_status.setText(text)

    def set_status_text(self, text):
        self.label_status.setText(text)

    def set_players(self, black_name, white_name):
        self.label_black_player.setText(f"{black_name} ●")
        self.label_white_player.setText(f"○ {white_name}")
