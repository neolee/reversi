import random
import threading
import time
from reversi.protocol.interface import EngineInterface
from reversi.protocol.constants import Command, Response
from reversi.engine.board import Board

class LocalEngine(EngineInterface):
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
            self._emit_board_update() # Optional: notify UI of reset

        elif cmd == Command.PLAY:
            # PLAY <coord>
            if len(parts) < 2:
                self._emit(f"{Response.ERROR} Missing coordinate")
                return
            coord = parts[1]
            try:
                r, c = Board.str_to_coord(coord)
                # We need to know whose turn it is.
                # The protocol says PLAY <coord>, implying the current player.
                # But usually engines track whose turn it is.
                player = self.board.current_player
                
                if self.board.play_move(r, c, player):
                    self._emit(Response.OK)
                    self._emit_board_update()
                    # Check if game over or pass needed
                    self._check_game_state()
                else:
                    self._emit(f"{Response.ERROR} Illegal move {coord}")
            except ValueError:
                self._emit(f"{Response.ERROR} Invalid coordinate format")

        elif cmd == Command.GENMOVE:
            # GENMOVE <color>
            # If color is not provided, use current player
            color = parts[1] if len(parts) > 1 else self.board.current_player
            
            # Run AI in a separate thread to not block UI
            threading.Thread(target=self._ai_move, args=(color,)).start()

        elif cmd == Command.UNDO:
            if self.board.undo():
                self._emit(Response.OK)
                self._emit_board_update() # Notify UI to refresh
            else:
                self._emit(f"{Response.ERROR} Cannot undo")

        elif cmd == Command.BOARD:
            self._emit_board_update()

        elif cmd == Command.VALID_MOVES:
            # VALID_MOVES [color]
            color = parts[1] if len(parts) > 1 else self.board.current_player
            moves = self.board.get_valid_moves(color)
            moves_str = " ".join([self.board.coord_to_str(r, c) for r, c in moves])
            self._emit(f"{Response.VALID_MOVES} {moves_str}")

    def _ai_move(self, color: str):
        # Simulate thinking
        time.sleep(0.5)
        
        valid_moves = self.board.get_valid_moves(color)
        if not valid_moves:
            self._emit(Response.PASS)
            return

        # Simple Random AI for now
        # TODO: Implement Minimax
        r, c = random.choice(valid_moves)
        move_str = self.board.coord_to_str(r, c)
        
        # Execute the move on the internal board
        self.board.play_move(r, c, color)
        
        self._emit(f"{Response.MOVE} {move_str}")
        self._emit_board_update()
        self._check_game_state()

    def _check_game_state(self):
        # Check if next player has moves
        next_player = self.board.current_player
        if not self.board.has_valid_move(next_player):
            # If next player has no moves, check if game is over
            opponent = Board.WHITE if next_player == Board.BLACK else Board.BLACK
            if not self.board.has_valid_move(opponent):
                # Game Over
                scores = self.board.get_score()
                winner = "DRAW"
                if scores[Board.BLACK] > scores[Board.WHITE]:
                    winner = "BLACK"
                elif scores[Board.WHITE] > scores[Board.BLACK]:
                    winner = "WHITE"
                self._emit(f"{Response.RESULT} {winner}")
            else:
                # Pass
                # In some protocols, the engine might auto-pass or wait for a command.
                # Here we just inform.
                pass

    def _emit_board_update(self):
        # Format: BOARD <size> <current_player> <state_string>
        # state_string: row by row, . for empty, B for Black, W for White
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
