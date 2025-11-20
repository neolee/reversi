from typing import List, Tuple, Optional, Set

class Board:
    BLACK = "BLACK"
    WHITE = "WHITE"
    EMPTY = None

    def __init__(self, size: int = 8):
        self.size = size
        self.grid: List[List[Optional[str]]] = [[self.EMPTY for _ in range(size)] for _ in range(size)]
        self.current_player = self.BLACK
        self.history = [] # Stack to store history for undo
        self._init_board()

    def _init_board(self):
        """Initialize the board with the standard 4 starting pieces."""
        mid = self.size // 2
        # 0-indexed coordinates
        # D4 (3,3), E5 (4,4) -> WHITE
        # E4 (4,3), D5 (3,4) -> BLACK
        self.grid[mid-1][mid-1] = self.WHITE
        self.grid[mid][mid] = self.WHITE
        self.grid[mid][mid-1] = self.BLACK
        self.grid[mid-1][mid] = self.BLACK
        self.current_player = self.BLACK

    def is_on_board(self, r: int, c: int) -> bool:
        return 0 <= r < self.size and 0 <= c < self.size

    def get_piece(self, r: int, c: int) -> Optional[str]:
        if self.is_on_board(r, c):
            return self.grid[r][c]
        return None

    def get_valid_moves(self, player: str) -> List[Tuple[int, int]]:
        """Return a list of (row, col) tuples for valid moves."""
        valid_moves = []
        for r in range(self.size):
            for c in range(self.size):
                if self.is_valid_move(r, c, player):
                    valid_moves.append((r, c))
        return valid_moves

    def is_valid_move(self, r: int, c: int, player: str) -> bool:
        if not self.is_on_board(r, c) or self.grid[r][c] is not None:
            return False
        
        opponent = self.WHITE if player == self.BLACK else self.BLACK
        
        # Check all 8 directions
        directions = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
        
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            if self.is_on_board(nr, nc) and self.grid[nr][nc] == opponent:
                # Found opponent piece, keep checking in this direction
                while True:
                    nr += dr
                    nc += dc
                    if not self.is_on_board(nr, nc):
                        break
                    if self.grid[nr][nc] == self.EMPTY:
                        break
                    if self.grid[nr][nc] == player:
                        return True # Found a line of opponent pieces capped by player
        return False

    def play_move(self, r: int, c: int, player: str) -> bool:
        """Execute a move. Returns True if successful."""
        if not self.is_valid_move(r, c, player):
            return False

        # Save state for undo
        self._save_state()

        self.grid[r][c] = player
        opponent = self.WHITE if player == self.BLACK else self.BLACK
        
        directions = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
        
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            pieces_to_flip = []
            
            while self.is_on_board(nr, nc) and self.grid[nr][nc] == opponent:
                pieces_to_flip.append((nr, nc))
                nr += dr
                nc += dc
            
            if self.is_on_board(nr, nc) and self.grid[nr][nc] == player:
                for fr, fc in pieces_to_flip:
                    self.grid[fr][fc] = player

        self.current_player = opponent
        return True

    def pass_turn(self, player: str) -> bool:
        """Pass the turn to the opponent without placing a disk."""
        if player not in (self.BLACK, self.WHITE):
            return False

        opponent = self.WHITE if player == self.BLACK else self.BLACK
        if self.current_player != player:
            return False

        self._save_state()
        self.current_player = opponent
        return True

    def has_valid_move(self, player: str) -> bool:
        return len(self.get_valid_moves(player)) > 0

    def is_game_over(self) -> bool:
        return not self.has_valid_move(self.BLACK) and not self.has_valid_move(self.WHITE)

    def get_score(self):
        black_score = 0
        white_score = 0
        for r in range(self.size):
            for c in range(self.size):
                if self.grid[r][c] == self.BLACK:
                    black_score += 1
                elif self.grid[r][c] == self.WHITE:
                    white_score += 1
        return {self.BLACK: black_score, self.WHITE: white_score}

    def _save_state(self):
        # Deep copy grid
        grid_copy = [row[:] for row in self.grid]
        self.history.append({
            'grid': grid_copy,
            'current_player': self.current_player
        })

    def undo(self):
        if self.history:
            state = self.history.pop()
            self.grid = state['grid']
            self.current_player = state['current_player']
            return True
        return False

    def coord_to_str(self, r: int, c: int) -> str:
        return f"{chr(65+c)}{r+1}"

    @staticmethod
    def str_to_coord(coord: str) -> Tuple[int, int]:
        c = ord(coord[0].upper()) - 65
        r = int(coord[1:]) - 1
        return r, c

    def clone(self) -> "Board":
        copied = Board(self.size)
        copied.grid = [row[:] for row in self.grid]
        copied.current_player = self.current_player
        copied.history = []
        return copied
