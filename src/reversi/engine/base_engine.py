from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from typing import Iterable, Optional, Tuple

from reversi.protocol.constants import Command, Response
from reversi.protocol.interface import EngineInterface
from reversi.engine.board import Board


class BaseEngine(EngineInterface, ABC):
    """Shared command handling and board bookkeeping for engines."""

    def __init__(self, board_size: int = 8, think_delay: float = 0.2):
        super().__init__()
        self.board_size = board_size
        self.think_delay = think_delay
        self.board = Board(size=board_size)
        self._running = False

    # ------------------------------------------------------------------
    # EngineInterface lifecycle
    # ------------------------------------------------------------------
    def start(self):
        self._running = True
        self._emit(Response.READY)

    def stop(self):
        self._running = False

    # ------------------------------------------------------------------
    # Command handling
    # ------------------------------------------------------------------
    def send_command(self, command: str):
        if not self._running:
            return

        parts = command.split()
        if not parts:
            return

        cmd = parts[0]

        if cmd == Command.INIT:
            self._handle_init()
        elif cmd == Command.NEWGAME:
            self._handle_newgame()
        elif cmd == Command.PLAY:
            self._handle_play(parts)
        elif cmd == Command.GENMOVE:
            color = parts[1] if len(parts) > 1 else self.board.current_player
            self._handle_genmove(color)
        elif cmd == Command.UNDO:
            self._handle_undo()
        elif cmd == Command.BOARD:
            self._emit_board_update()
        elif cmd == Command.VALID_MOVES:
            color = parts[1] if len(parts) > 1 else self.board.current_player
            self._emit_valid_moves(color)
        elif cmd == Command.PASS:
            color = parts[1] if len(parts) > 1 else self.board.current_player
            self._handle_pass(color)

    # ------------------------------------------------------------------
    # Shared handlers
    # ------------------------------------------------------------------
    def _handle_init(self):
        self.board = Board(size=self.board_size)
        self._emit(Response.READY)

    def _handle_newgame(self):
        self.board = Board(size=self.board_size)
        self._emit(Response.OK)
        self._emit_board_update()

    def _handle_play(self, parts):
        if len(parts) < 2:
            self._emit(f"{Response.ERROR} Missing coordinate")
            return

        coord = parts[1]
        try:
            r, c = Board.str_to_coord(coord)
            player = self.board.current_player
            if self.board.play_move(r, c, player):
                self._emit(Response.OK)
                self._emit_board_update()
                self._check_game_state()
            else:
                self._emit(f"{Response.ERROR} Illegal move {coord}")
        except ValueError:
            self._emit(f"{Response.ERROR} Invalid coordinate format")

    def _handle_genmove(self, color: str):
        threading.Thread(target=self._run_ai_turn, args=(color,), daemon=True).start()

    def _handle_undo(self):
        if self.board.undo():
            self._emit(Response.OK)
            self._emit_board_update()
        else:
            self._emit(f"{Response.ERROR} Cannot undo")

    def _emit_valid_moves(self, color: str):
        moves = self.board.get_valid_moves(color)
        moves_str = " ".join([self.board.coord_to_str(r, c) for r, c in moves])
        self._emit(f"{Response.VALID_MOVES} {moves_str}")

    def _handle_pass(self, color: str):
        if color != self.board.current_player:
            self._emit(f"{Response.ERROR} Not {color}'s turn")
            return
        if self.board.has_valid_move(color):
            self._emit(f"{Response.ERROR} Moves available for {color}")
            return
        if self.board.pass_turn(color):
            self._emit(Response.OK)
            self._emit_board_update()
            self._check_game_state()
        else:
            self._emit(f"{Response.ERROR} Unable to pass for {color}")

    # ------------------------------------------------------------------
    # AI execution
    # ------------------------------------------------------------------
    def _run_ai_turn(self, color: str):
        time.sleep(self.think_delay)

        valid_moves = self.board.get_valid_moves(color)
        if not valid_moves:
            self._emit_pass(color)
            return

        board_snapshot = self.board.clone()
        move = self._pick_move(board_snapshot, color, valid_moves)
        if move is None:
            move = valid_moves[0]

        r, c = move
        move_str = self.board.coord_to_str(r, c)
        if self.board.play_move(r, c, color):
            self._emit(f"{Response.MOVE} {move_str}")
            self._emit_board_update()
            self._check_game_state()
        else:
            self._emit(f"{Response.ERROR} Failed to apply move {move_str}")

    def _emit_pass(self, color: str):
        if self.board.pass_turn(color):
            self._emit(f"{Response.PASS} {color}")
            self._emit_board_update()
            self._check_game_state()
        else:
            self._emit(f"{Response.ERROR} Cannot pass {color}")

    @abstractmethod
    def _pick_move(
        self,
        board_snapshot: Board,
        color: str,
        valid_moves: Iterable[Tuple[int, int]],
    ) -> Optional[Tuple[int, int]]:
        """Return the chosen move as (row, col) or None to force fallback."""

    # ------------------------------------------------------------------
    # Board helpers
    # ------------------------------------------------------------------
    def _check_game_state(self):
        next_player = self.board.current_player
        if not self.board.has_valid_move(next_player):
            opponent = Board.WHITE if next_player == Board.BLACK else Board.BLACK
            if not self.board.has_valid_move(opponent):
                scores = self.board.get_score()
                winner = "DRAW"
                if scores[Board.BLACK] > scores[Board.WHITE]:
                    winner = "BLACK"
                elif scores[Board.WHITE] > scores[Board.BLACK]:
                    winner = "WHITE"
                self._emit(f"{Response.RESULT} {winner}")

    def _emit_board_update(self):
        state = []
        for r in range(self.board_size):
            for c in range(self.board_size):
                piece = self.board.get_piece(r, c)
                if piece == Board.BLACK:
                    state.append("B")
                elif piece == Board.WHITE:
                    state.append("W")
                else:
                    state.append(".")
        state_str = "".join(state)
        self._emit(f"{Response.BOARD} {self.board_size} {self.board.current_player} {state_str}")
