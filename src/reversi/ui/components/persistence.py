import json
import os
from datetime import datetime
from typing import Callable
from PySide6.QtWidgets import QFileDialog, QWidget

class PersistenceManager:
    def __init__(self,
                 parent_widget: QWidget,
                 get_save_payload_callback: Callable[[], dict],
                 load_game_data_callback: Callable[[dict], None],
                 log_callback: Callable[[str], None]):
        self.parent = parent_widget
        self.get_save_payload = get_save_payload_callback
        self.load_game_data = load_game_data_callback
        self.log = log_callback

    def request_save(self):
        payload = self.get_save_payload()
        timeline = payload.get("timeline", [])
        if not timeline:
            self.log("Warning: Nothing to save yet. Play or load a game first.")
            return

        self.log(f"GUI: Save requested (timeline entries: {len(timeline)})")

        default_name = self._build_default_filename(payload)
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent,
            "Save Game",
            os.path.join(self._get_initial_dir(), default_name),
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                self.log(f"Saved game to {file_path}")
            except Exception as e:
                self.log(f"Error saving game: {e}")

    def request_load(self):
        self.log("GUI: Load requested")
        file_path, _ = QFileDialog.getOpenFileName(
            self.parent,
            "Load Game",
            self._get_initial_dir(),
            "JSON Files (*.json)"
        )

        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.load_game_data(data)
                self.log(f"Loaded game from {file_path}")
            except Exception as e:
                self.log(f"Error loading game: {e}")

    def _get_initial_dir(self) -> str:
        # Just return home dir or current dir for simplicity
        return os.path.expanduser("~")

    def _build_default_filename(self, payload: dict) -> str:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"reversi-{timestamp}.json"
