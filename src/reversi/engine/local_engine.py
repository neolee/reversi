import threading
import time
from math import inf

from reversi.protocol.interface import EngineInterface
from reversi.protocol.constants import Command, Response
from reversi.engine.board import Board

class LocalEngine(EngineInterface):
    def __init__(self, board_size: int = 8, search_depth: int = 3, think_delay: float = 0.2):
        super().__init__()
        self.board_size = board_size
        self.board = Board(size=board_size)
        self._running = False
        self.search_depth = search_depth
        self.think_delay = think_delay
        self._search_color = Board.BLACK

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

        elif cmd == Command.PASS:
            color = parts[1] if len(parts) > 1 else self.board.current_player
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

    def _ai_move(self, color: str):
        # Simulate thinking delay so UI has breathing room
        time.sleep(self.think_delay)

        valid_moves = self.board.get_valid_moves(color)
        if not valid_moves:
            if self.board.pass_turn(color):
                self._emit(f"{Response.PASS} {color}")
                self._emit_board_update()
                self._check_game_state()
            else:
                self._emit(f"{Response.ERROR} Cannot pass {color}")
            return

        self._search_color = color
        board_snapshot = self.board.clone()
        move, _ = self._minimax(board_snapshot, color, self.search_depth, -inf, inf)
        if move is None:
            move = valid_moves[0]

        r, c = move
        move_str = self.board.coord_to_str(r, c)
        
        # Execute the move on the internal board
        self.board.play_move(r, c, color)
        
        self._emit(f"{Response.MOVE} {move_str}")
        self._emit_board_update()
        self._check_game_state()

    def _minimax(self, board: Board, player: str, depth: int, alpha: float, beta: float):
        opponent = Board.WHITE if player == Board.BLACK else Board.BLACK
        valid_moves = board.get_valid_moves(player)

        if depth == 0 or board.is_game_over():
            return None, self._evaluate_board(board)

        if not valid_moves:
            if board.has_valid_move(opponent):
                board_pass = board.clone()
                board_pass.current_player = opponent
                return self._minimax(board_pass, opponent, depth - 1, alpha, beta)
            return None, self._evaluate_board(board)

        maximizing = player == self._search_color
        best_move = None

        if maximizing:
            value = -inf
            for move in valid_moves:
                child = board.clone()
                child.play_move(move[0], move[1], player)
                _, score = self._minimax(child, child.current_player, depth - 1, alpha, beta)
                if score > value:
                    value = score
                    best_move = move
                alpha = max(alpha, value)
                if beta <= alpha:
                    break
            return best_move, value
        else:
            value = inf
            for move in valid_moves:
                child = board.clone()
                child.play_move(move[0], move[1], player)
                _, score = self._minimax(child, child.current_player, depth - 1, alpha, beta)
                if score < value:
                    value = score
                    best_move = move
                beta = min(beta, value)
                if beta <= alpha:
                    break
            return best_move, value

    def _evaluate_board(self, board: Board) -> float:
        opponent = Board.WHITE if self._search_color == Board.BLACK else Board.BLACK
        scores = board.get_score()
        disc_balance = scores[self._search_color] - scores[opponent]

        my_moves = len(board.get_valid_moves(self._search_color))
        opp_moves = len(board.get_valid_moves(opponent))
        mobility = my_moves - opp_moves

        corner_score = self._corner_heuristic(board, self._search_color) - self._corner_heuristic(board, opponent)

        return disc_balance * 1.5 + mobility * 5 + corner_score * 25

    def _corner_heuristic(self, board: Board, player: str) -> int:
        corners = [
            (0, 0),
            (0, board.size - 1),
            (board.size - 1, 0),
            (board.size - 1, board.size - 1),
        ]
        score = 0
        for r, c in corners:
            piece = board.get_piece(r, c)
            if piece == player:
                score += 1
        return score

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
