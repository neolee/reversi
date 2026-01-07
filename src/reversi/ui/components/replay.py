import asyncio
from typing import Callable
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QStyle
from PySide6.QtCore import Qt

class ReplayController(QWidget):
    def __init__(self,
                 apply_snapshot_callback: Callable[[int], None],
                 get_timeline_len_callback: Callable[[], int],
                 is_game_started_callback: Callable[[], bool]):
        super().__init__()
        self.apply_snapshot = apply_snapshot_callback
        self.get_timeline_len = get_timeline_len_callback
        self.is_game_started = is_game_started_callback

        self.replay_index = 0
        self.replay_playing = False
        self._replay_task: asyncio.Task | None = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)

        # Style icons using standard library or simple text
        self.btn_start = QPushButton("⇤")
        self.btn_prev = QPushButton("←")
        self.btn_play = QPushButton("▶")
        self.btn_next = QPushButton("→")
        self.btn_end = QPushButton("⇥")

        for btn in [self.btn_start, self.btn_prev, self.btn_play, self.btn_next, self.btn_end]:
            btn.setFixedWidth(40)
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 16px;
                    padding: 0;
                    background: #f8f8f8;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    color: #333;
                }
                QPushButton:hover {
                    background: #eeeeee;
                }
                QPushButton:disabled {
                    color: #dddddd;
                    background: #fcfcfc;
                    border-color: #eee;
                }
            """)
        self.btn_start.clicked.connect(self.on_replay_start)
        self.btn_prev.clicked.connect(self.on_replay_prev)
        self.btn_play.clicked.connect(self.on_replay_play_pause)
        self.btn_next.clicked.connect(self.on_replay_next)
        self.btn_end.clicked.connect(self.on_replay_end)

        self.status_label = QLabel("Replay 0 / 0")
        self.status_label.setStyleSheet("font-size: 11px; color: #666;")

        layout.addStretch()
        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_prev)
        layout.addWidget(self.btn_play)
        layout.addWidget(self.btn_next)
        layout.addWidget(self.btn_end)
        layout.addSpacing(10)
        layout.addWidget(self.status_label)
        layout.addStretch()

        self.update_status()

    def update_status(self):
        total = self.get_timeline_len()
        max_index = max(total - 1, 0)

        self.status_label.setText(f"Replay {self.replay_index} / {max_index}" if total else "Replay 0 / 0")

        active_game = self.is_game_started()
        # Per user request: Unfinished games cannot be browsed (Replay toolbar disabled)
        # Note: We consider a game "finished" if game_started is False after some moves.
        toolbar_disabled = active_game or total == 0

        at_start = self.replay_index <= 0
        at_end = self.replay_index >= max_index

        self.btn_start.setEnabled(not toolbar_disabled and not at_start)
        self.btn_prev.setEnabled(not toolbar_disabled and not at_start)
        self.btn_play.setEnabled(not toolbar_disabled and (not at_end or self.replay_playing))
        self.btn_next.setEnabled(not toolbar_disabled and not at_end)
        self.btn_end.setEnabled(not toolbar_disabled and not at_end)

        self.btn_play.setText("⏸" if self.replay_playing else "▶")

    def sync_index(self, index: int):
        self.replay_index = index
        self.update_status()

    def on_replay_start(self):
        self.stop_autoplay()
        self.apply_snapshot(0)

    def on_replay_end(self):
        self.stop_autoplay()
        self.apply_snapshot(max(0, self.get_timeline_len() - 1))

    def on_replay_prev(self):
        self.stop_autoplay()
        idx = max(0, self.replay_index - 1)
        self.apply_snapshot(idx)

    def on_replay_next(self):
        self.stop_autoplay()
        idx = min(self.get_timeline_len() - 1, self.replay_index + 1)
        self.apply_snapshot(idx)

    def on_replay_play_pause(self):
        if self.replay_playing:
            self.stop_autoplay()
        else:
            self.start_autoplay()

    def start_autoplay(self):
        if self.replay_playing: return
        self.replay_playing = True
        self.update_status()
        self._replay_task = asyncio.create_task(self._autoplay_loop())

    def stop_autoplay(self):
        self.replay_playing = False
        if self._replay_task:
            self._replay_task.cancel()
            self._replay_task = None
        self.update_status()

    async def _autoplay_loop(self):
        try:
            while self.replay_playing:
                await asyncio.sleep(0.8)
                total = self.get_timeline_len()
                if self.replay_index < total - 1:
                    idx = self.replay_index + 1
                    self.apply_snapshot(idx)
                else:
                    self.replay_playing = False
                    break
        except asyncio.CancelledError:
            pass
        finally:
            self.replay_playing = False
            self.update_status()
