import json
import os
from datetime import datetime
from urllib.parse import quote
import flet as ft
from typing import Callable, Any

class PersistenceManager:
    def __init__(self,
                 page_getter: Callable[[], ft.Page | None],
                 get_save_payload_callback: Callable[[], dict],
                 load_game_data_callback: Callable[[dict], None],
                 log_callback: Callable[[str], None]):
        self.get_page = page_getter
        self.get_save_payload = get_save_payload_callback
        self.load_game_data = load_game_data_callback
        self.log = log_callback

        self.save_picker: ft.FilePicker | None = None
        self.load_picker: ft.FilePicker | None = None

    def register_pickers(self, overlay: list[ft.Control]):
        self.save_picker = ft.FilePicker(on_result=self._handle_save_dialog)
        self.load_picker = ft.FilePicker(on_result=self._handle_load_dialog)
        overlay.append(self.save_picker)
        overlay.append(self.load_picker)

    def request_save(self, e):
        payload = self.get_save_payload()
        timeline = payload.get("timeline", [])
        if not timeline:
            self.log("Warning: Nothing to save yet. Play or load a game first.")
            return
        if not self.save_picker:
            return
        self.log(f"GUI: Save requested (timeline entries: {len(timeline)})")
        default_name = f"reversi-{datetime.now():%Y%m%d-%H%M%S}.json"

        page = self.get_page()
        initial_dir = page.client_storage.get("last_picker_path") if page else None

        self.save_picker.save_file(
            file_name=default_name,
            allowed_extensions=["json"],
            initial_directory=initial_dir,
        )

    def request_load(self, e):
        if not self.load_picker:
            return
        self.log("GUI: Load requested")

        page = self.get_page()
        initial_dir = page.client_storage.get("last_picker_path") if page else None

        self.load_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=["json"],
            initial_directory=initial_dir,
        )

    def _handle_save_dialog(self, e: ft.FilePickerResultEvent):
        if not e.path and not e.files:
            self.log("Save canceled")
            return

        payload = self.get_save_payload()
        page = self.get_page()

        if e.path:
            if page:
                page.client_storage.set("last_picker_path", os.path.dirname(e.path))
            try:
                self._save_game_to_path(e.path, payload)
                self.log(f"Saved game to {e.path}")
            except Exception as exc:
                self.log(f"Error saving game: {exc}")
            return

        file_name = e.files[0].name if e.files else f"reversi-{datetime.now():%Y%m%d-%H%M%S}.json"
        self._download_payload(payload, file_name)
        self.log(f"Saved game as download {file_name}")

    def _handle_load_dialog(self, e: ft.FilePickerResultEvent):
        if not e.files:
            self.log("Load canceled")
            return

        file_info = e.files[0]
        page = self.get_page()

        if file_info.path:
            if page:
                page.client_storage.set("last_picker_path", os.path.dirname(file_info.path))
            try:
                self._load_game_from_path(file_info.path)
                self.log(f"Loaded game from {file_info.path}")
            except Exception as exc:
                self.log(f"Error loading game: {exc}")
            return

        file_bytes = getattr(file_info, "bytes", None)
        if file_bytes:
            try:
                self._load_game_from_bytes(file_bytes)
                display_name = file_info.name or "selected file"
                self.log(f"Loaded game from {display_name} (download)")
            except Exception as exc:
                self.log(f"Error loading game: {exc}")
            return
        self.log("Error loading game: picker returned no usable data")

    def _save_game_to_path(self, path: str, payload: dict):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)

    def _download_payload(self, payload: dict, file_name: str):
        page = self.get_page()
        if not page:
            return
        json_str = json.dumps(payload, indent=2)
        data_url = "data:application/json;charset=utf-8," + quote(json_str)
        page.launch_url(data_url, web_window_name=file_name)

    def _load_game_from_path(self, path: str):
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.load_game_data(data)

    def _load_game_from_bytes(self, data_bytes: bytes):
        decoded = data_bytes.decode("utf-8")
        data = json.loads(decoded)
        self.load_game_data(data)
