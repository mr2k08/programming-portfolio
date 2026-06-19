def diag(board: list, reverse: bool = False) -> tuple[str, str ,str]:
    """Retourne la diagonale du plateau de jeu."""
    return (board[2][0],board[1][1],board[0][2]) if reverse else (board[0][0],board[1][1],board[2][2])

def col(board: list, i: int) -> tuple[str, str ,str]:
    """Retourne une colonne du plateau."""
    return (board[0][i], board[1][i], board[2][i])

def isLegal(row: str, col: str, occupied: list) -> bool:
    """Vérifie si le coup est légal (dans les limites et position libre)."""
    if (len(col), len(row)) == (1,1) and col.isdigit() and row.isdigit():
        row, col = int(row), int(col)
        if (0 < col < 4) and (0 < row < 4) and ((col, row) not in occupied):
            return True
    return False

def check_winner(board: list) -> bool:
    """Vérifie s'il y a un gagnant sur le plateau."""
    for y in range(3):
        coln, row = set(col(board, y)), set(board[y])
        if coln in ({'x'}, {'o'}) or row in ({'x'}, {'o'}):
            return True
        diag_, rev_diag = set(diag(board)), set(diag(board, reverse= True))
        if diag_ in ({'x'}, {'o'}) or rev_diag in ({'x'}, {'o'}):
            return True
    return False

def update_pos(board: list, pos: tuple, player: str) -> None:
    """Met à jour la position du joueur sur le plateau."""
    board[pos[0]-1][pos[1]-1] = player

def display(board: list) -> None:
    """Affiche le plateau de jeu."""
    print(f'-------------\n| {board[0][0]} | {board[0][1]} | {board[0][2]} | \n-------------\n'
          f'| {board[1][0]} | {board[1][1]} | {board[1][2]} |\n-------------\n'
          f'| {board[2][0]} | {board[2][1]} | {board[2][2]} |\n-------------')
