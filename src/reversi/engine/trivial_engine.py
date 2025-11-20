import random
import threading
import time

from reversi.protocol.interface import EngineInterface
from reversi.protocol.constants import Command, Response
from reversi.engine.board import Board


class TrivialEngine(EngineInterface):
    """Random-move engine used for testing and baseline comparisons."""

    def __init__(self, board_size: int = 8):
        super().__init__()
        self.board_size = board_size
        self.board = Board(size=board_size)
        self._running = False

    def start(self):
        self._running = True
        self._emit(Response.READY)

    def stop(self):
        self._running = False

    def send_command(self, command: str):
        if not self._running:
            return

        parts = command.split()
        if not parts:
            return
        cmd = parts[0]

        if cmd == Command.INIT:
            self.board = Board(size=self.board_size)
            self._emit(Response.READY)

        elif cmd == Command.NEWGAME:
            self.board = Board(size=self.board_size)
            self._emit(Response.OK)
            self._emit_board_update()

        elif cmd == Command.PLAY:
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

        elif cmd == Command.GENMOVE:
            color = parts[1] if len(parts) > 1 else self.board.current_player
            threading.Thread(target=self._ai_move, args=(color,)).start()

        elif cmd == Command.UNDO:
            if self.board.undo():
                self._emit(Response.OK)
                self._emit_board_update()
            else:
                self._emit(f"{Response.ERROR} Cannot undo")

        elif cmd == Command.BOARD:
            self._emit_board_update()

        elif cmd == Command.VALID_MOVES:
            color = parts[1] if len(parts) > 1 else self.board.current_player
            moves = self.board.get_valid_moves(color)
            moves_str = " ".join([self.board.coord_to_str(r, c) for r, c in moves])
            self._emit(f"{Response.VALID_MOVES} {moves_str}")

    def _ai_move(self, color: str):
        time.sleep(0.2)
        valid_moves = self.board.get_valid_moves(color)
        if not valid_moves:
            self._emit(Response.PASS)
            return

        r, c = random.choice(valid_moves)
        move_str = self.board.coord_to_str(r, c)
        self.board.play_move(r, c, color)
        self._emit(f"{Response.MOVE} {move_str}")
        self._emit_board_update()
        self._check_game_state()

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
                p = self.board.get_piece(r, c)
                if p == Board.BLACK:
                    state.append("B")
                elif p == Board.WHITE:
                    state.append("W")
                else:
                    state.append(".")
        state_str = "".join(state)
        self._emit(f"{Response.BOARD} {self.board_size} {self.board.current_player} {state_str}")
