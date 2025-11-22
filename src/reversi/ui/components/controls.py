import flet as ft
from typing import Callable, Dict

class GameControlsComponent:
    def __init__(self, 
                 on_new_game: Callable,
                 on_undo: Callable,
                 on_pass: Callable,
                 on_player_mode_change: Callable[[str, str], None],
                 on_save: Callable,
                 on_load: Callable):
        self.on_new_game = on_new_game
        self.on_undo = on_undo
        self.on_pass = on_pass
        self.on_player_mode_change = on_player_mode_change
        self.on_save = on_save
        self.on_load = on_load
        
        self.pass_button: ft.ElevatedButton | None = None
        self.player_mode_selectors: Dict[str, ft.Dropdown] = {}
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
        
        def build_selector(color: str, label: str, default: str) -> ft.Row:
            dropdown = ft.Dropdown(
                options=[
                    ft.dropdown.Option("human", "Human"),
                    ft.dropdown.Option("engine", "Engine"),
                ],
                value=default,
                on_change=lambda e, color=color: self.on_player_mode_change(color, e.control.value),
                dense=True,
                content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border_color="rgba(0,0,0,0.2)",
                border_radius=8,
                width=140,
            )
            self.player_mode_selectors[color] = dropdown
            return ft.Row(
                [
                    ft.Text(label, weight=ft.FontWeight.BOLD),
                    dropdown,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                spacing=8,
            )

        player_settings = ft.Column(
            [
                build_selector("BLACK", "Black", "human"),
                build_selector("WHITE", "White", "engine"),
            ],
            spacing=6,
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
                    player_settings,
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

    def set_player_mode(self, color: str, mode: str):
        selector = self.player_mode_selectors.get(color)
        if selector:
            selector.value = mode
            selector.update()
