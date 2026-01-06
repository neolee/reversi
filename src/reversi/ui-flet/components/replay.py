import asyncio
import flet as ft
from typing import Callable, cast


class ReplayController:
    def __init__(self,
                 page_getter: Callable[[], ft.Page | None],
                 apply_snapshot_callback: Callable[[int], None],
                 get_timeline_len_callback: Callable[[], int],
                 is_game_started_callback: Callable[[], bool]):
        self.get_page = page_getter
        self.apply_snapshot = apply_snapshot_callback
        self.get_timeline_len = get_timeline_len_callback
        self.is_game_started = is_game_started_callback

        self.replay_index = 0
        self.replay_playing = False
        self._replay_task: asyncio.Task | None = None

        # UI Elements
        self.replay_status_text: ft.Text | None = None
        self.replay_buttons: dict[str, ft.IconButton] = {}
        self.toolbar_height = 58

    def create_toolbar(self) -> ft.Container:
        self.replay_status_text = ft.Text("Replay 0 / 0", size=12, color="#333333")
        self.replay_buttons = {
            "start": ft.IconButton(icon="first_page", on_click=self.on_replay_start, tooltip="Jump to start"),
            "prev": ft.IconButton(icon="chevron_left", on_click=self.on_replay_prev, tooltip="Step back"),
            "play": ft.IconButton(icon="play_arrow", on_click=self.on_replay_play_pause, tooltip="Play/Pause replay"),
            "next": ft.IconButton(icon="chevron_right", on_click=self.on_replay_next, tooltip="Step forward"),
            "end": ft.IconButton(icon="last_page", on_click=self.on_replay_end, tooltip="Jump to end"),
        }
        toolbar = ft.Row(
            [
                self.replay_buttons["start"],
                self.replay_buttons["prev"],
                self.replay_buttons["play"],
                self.replay_buttons["next"],
                self.replay_buttons["end"],
                ft.Container(width=16),
                self.replay_status_text,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=6,
        )
        container = ft.Container(
            content=toolbar,
            padding=ft.padding.symmetric(vertical=6, horizontal=16),
            bgcolor="#f1f1f1",
            border_radius=12,
            border=ft.border.all(1, "#dcdcdc"),
            height=self.toolbar_height,
            alignment=ft.alignment.center
        )
        self.update_status()
        return container

    def update_status(self):
        total = self.get_timeline_len()
        max_index = max(total - 1, 0)
        status = f"Replay {self.replay_index} / {max_index}" if total else "Replay 0 / 0"
        if self.replay_status_text:
            self.replay_status_text.value = status
            if getattr(self.replay_status_text, "page", None):
                self.replay_status_text.update()

        base_disabled = self.is_game_started() or total == 0
        at_start = self.replay_index <= 0
        at_end = self.replay_index >= max_index

        if self.replay_buttons:
            self.replay_buttons["start"].disabled = base_disabled or at_start
            self.replay_buttons["prev"].disabled = base_disabled or at_start
            self.replay_buttons["play"].disabled = base_disabled or at_end
            self.replay_buttons["next"].disabled = base_disabled or at_end
            self.replay_buttons["end"].disabled = base_disabled or at_end

            for btn in self.replay_buttons.values():
                if getattr(btn, "page", None):
                    btn.update()

    def reset(self):
        self.replay_index = 0
        self.replay_playing = False
        self.stop_autoplay()
        self.update_status()

    def sync_index(self, index: int):
        """Called by App when a move is made to sync the index"""
        self.replay_index = index
        self.update_status()

    def on_replay_start(self, e):
        if self.is_game_started() or self.get_timeline_len() == 0:
            return
        self.stop_autoplay()
        self.apply_snapshot(0)

    def on_replay_prev(self, e):
        if self.is_game_started() or self.get_timeline_len() == 0:
            return
        self.stop_autoplay()
        self.apply_snapshot(max(0, self.replay_index - 1))

    def on_replay_next(self, e):
        if self.is_game_started() or self.get_timeline_len() == 0:
            return
        self.stop_autoplay()
        self.apply_snapshot(min(self.get_timeline_len() - 1, self.replay_index + 1))

    def on_replay_end(self, e):
        if self.is_game_started() or self.get_timeline_len() == 0:
            return
        self.stop_autoplay()
        self.apply_snapshot(self.get_timeline_len() - 1)

    def on_replay_play_pause(self, e):
        if self.is_game_started() or self.get_timeline_len() == 0:
            return
        if self.replay_playing:
            self.stop_autoplay()
        else:
            self.start_autoplay()

    def start_autoplay(self):
        if self.replay_playing or self.get_timeline_len() == 0:
            return
        self.replay_playing = True
        self._update_play_button()
        page = self.get_page()
        if page:
            self._replay_task = cast(asyncio.Task, page.run_task(self._autoplay_loop))
        else:
            self._replay_task = asyncio.create_task(self._autoplay_loop())

    def stop_autoplay(self):
        if self._replay_task and not self._replay_task.done():
            self._replay_task.cancel()
        self._replay_task = None
        if self.replay_playing:
            self.replay_playing = False
            self._update_play_button()

    async def _autoplay_loop(self):
        try:
            while self.replay_playing and self.replay_index < self.get_timeline_len() - 1:
                await asyncio.sleep(1.0)
                self.apply_snapshot(self.replay_index + 1)
            self.replay_playing = False
            self._update_play_button()
        except asyncio.CancelledError:
            pass

    def _update_play_button(self):
        play_btn = self.replay_buttons.get("play")
        if play_btn:
            play_btn.icon = "pause" if self.replay_playing else "play_arrow"
            if getattr(play_btn, "page", None):
                play_btn.update()
