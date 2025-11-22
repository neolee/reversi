import flet as ft
from typing import Callable

class GameControlsComponent:
    def __init__(self, 
                 on_new_game: Callable,
                 on_undo: Callable,
                 on_pass: Callable,
                 on_color_change: Callable,
                 on_save: Callable,
                 on_load: Callable):
        self.on_new_game = on_new_game
        self.on_undo = on_undo
        self.on_pass = on_pass
        self.on_color_change = on_color_change
        self.on_save = on_save
        self.on_load = on_load
        
        self.pass_button: ft.ElevatedButton | None = None
        self.color_selector: ft.RadioGroup | None = None
        self.container: ft.Container | None = None

    def create_sidebar(self, log_view: ft.Control) -> ft.Container:
        # Log Area
        log_container = ft.Container(
            content=log_view,
            border=ft.border.all(1, "grey400"),
            border_radius=5,
            padding=5,
            expand=True,
            bgcolor="grey100"
        )

        self.pass_button = ft.ElevatedButton(
            "Pass Turn",
            on_click=self.on_pass,
            disabled=True,
            expand=1
        )
        
        self.color_selector = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(value="BLACK", label="Play as Black (First)"),
                ft.Radio(value="WHITE", label="Play as White (Second)")
            ]),
            on_change=self.on_color_change,
            value="BLACK"
        )
        
        control_row = ft.Row(
            [
                ft.ElevatedButton("Undo", on_click=self.on_undo, expand=1),
                self.pass_button
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            spacing=10
        )
        
        save_row = ft.Row(
            [
                ft.ElevatedButton("Save", on_click=self.on_save, expand=1),
                ft.ElevatedButton("Load", on_click=self.on_load, expand=1)
            ],
            spacing=10
        )
        
        self.container = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Reversi", size=30, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Text("Game Settings", size=20, weight=ft.FontWeight.BOLD),
                    self.color_selector,
                    ft.ElevatedButton("Start New Game", on_click=self.on_new_game, width=200),
                    ft.Divider(),
                    ft.Text("Controls", size=20, weight=ft.FontWeight.BOLD),
                    control_row,
                    save_row,
                    ft.Divider(),
                    ft.Text("Engine Log", size=16, weight=ft.FontWeight.BOLD),
                    log_container
                ],
                spacing=10,
                expand=True,
            ),
            width=300,
            padding=10,
            bgcolor="grey50"
        )
        return self.container

    def set_pass_disabled(self, disabled: bool):
        if self.pass_button:
            self.pass_button.disabled = disabled
            self.pass_button.update()

    def set_color(self, color: str):
        if self.color_selector:
            self.color_selector.value = color
            self.color_selector.update()
