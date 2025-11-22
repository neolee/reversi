import flet as ft

class ScoreboardComponent:
    def __init__(self, height: float = 82):
        self.height = height
        self.black_score_text = ft.Text("● Black 2", size=22, weight=ft.FontWeight.BOLD, color="#111111")
        self.white_score_text = ft.Text("○ White 2", size=22, weight=ft.FontWeight.BOLD, color="#444444")
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

        score_row = ft.Row(
            [self.black_score_text, ft.Container(width=12), self.white_score_text],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER
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
        self.black_score_text.value = f"● Black {black}"
        self.white_score_text.value = f"○ White {white}"
        self.black_score_text.update()
        self.white_score_text.update()

    def set_status(self, message: str, color: str = "#333333"):
        self.status_text.value = message
        self.status_text.color = color
        self.status_text.update()
