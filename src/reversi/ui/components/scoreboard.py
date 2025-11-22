import flet as ft

class ScoreboardComponent:
    def __init__(self, height: float = 82):
        self.height = height
        self.black_label = "Black"
        self.white_label = "White"
        self.black_score = 2
        self.white_score = 2
        self.black_name_text = ft.Text(self._name_text("BLACK"), size=20, weight=ft.FontWeight.BOLD, color="#111111")
        self.white_name_text = ft.Text(self._name_text("WHITE"), size=20, weight=ft.FontWeight.BOLD, color="#111111", text_align=ft.TextAlign.RIGHT)
        self.black_score_text = ft.Text(str(self.black_score), size=26, weight=ft.FontWeight.BOLD, color="#111111")
        self.white_score_text = ft.Text(str(self.white_score), size=26, weight=ft.FontWeight.BOLD, color="#111111")
        self.status_text = ft.Text("Waiting for engine...", size=13, color="#333333", weight=ft.FontWeight.BOLD)
        self.container = None

    def create(self) -> ft.Container:
        header_row = ft.Row(
            [
                ft.Text("BLACK", size=11, color="#666666"),
                self.status_text,
                ft.Text("WHITE", size=11, color="#666666")
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
        )

        scores_center = ft.Row(
            [self.black_score_text, self.white_score_text],
            spacing=40,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
        score_row = ft.Row(
            [
                ft.Container(content=self.black_name_text, alignment=ft.alignment.center_left, expand=1),
                scores_center,
                ft.Container(content=self.white_name_text, alignment=ft.alignment.center_right, expand=1),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self.container = ft.Container(
            content=ft.Column(
                [header_row, score_row],
                spacing=4,
                alignment=ft.MainAxisAlignment.START,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH
            ),
            padding=ft.padding.symmetric(vertical=6, horizontal=14),
            bgcolor="#f9f9f9",
            border_radius=14,
            border=ft.border.all(1, "#e0e0e0"),
            shadow=ft.BoxShadow(
                blur_radius=6,
                color="rgba(0,0,0,0.08)",
                offset=ft.Offset(0, 3)
            ),
            height=self.height,
            alignment=ft.alignment.center
        )
        return self.container

    def update_scores(self, black: int, white: int):
        self.black_score = black
        self.white_score = white
        self.black_score_text.value = str(self.black_score)
        self.white_score_text.value = str(self.white_score)
        if self.black_score_text.page:
            self.black_score_text.update()
        if self.white_score_text.page:
            self.white_score_text.update()

    def set_player_label(self, color: str, label: str):
        if color == "BLACK":
            self.black_label = label or "Black"
            self.black_name_text.value = self._name_text("BLACK")
            if self.black_name_text.page:
                self.black_name_text.update()
        elif color == "WHITE":
            self.white_label = label or "White"
            self.white_name_text.value = self._name_text("WHITE")
            if self.white_name_text.page:
                self.white_name_text.update()

    def set_status(self, message: str, color: str = "#333333"):
        self.status_text.value = message
        self.status_text.color = color
        self.status_text.update()

    def _name_text(self, color: str) -> str:
        if color == "BLACK":
            return f"{self.black_label} ●"
        return f"○ {self.white_label}"
