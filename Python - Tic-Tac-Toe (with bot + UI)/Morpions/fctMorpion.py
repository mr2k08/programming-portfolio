def diag(board: list, reverse: bool = False) -> tuple[str, str ,str]:
    """Retourne la diagonale du plateau de jeu."""
    return (board[2][0],board[1][1],board[0][2]) if reverse else (board[0][0],board[1][1],board[2][2])  # Diagonale inversée ou normale
    
def col(board: list, i: int) -> tuple[str, str ,str]:
    """Retourne une colonne du plateau."""
    return (board[0][i], board[1][i], board[2][i])  # Récupère les 3 éléments de la colonne i

def isLegal(row: str, col: str, occupied: list) -> bool:
    """Vérifie si le coup est légal (dans les limites et position libre)."""
    if (len(col), len(row)) == (1,1) and col.isdigit() and row.isdigit():  # Doit être des chiffres uniques
        row, col = int(row), int(col)  # Conversion en entiers
        if (0 < col < 4) and (0 < row < 4) and ((col, row) not in occupied):  # Vérification des limites et disponibilité
            return True
    return False
    
def check_winner(board: list) -> bool:
    """Vérifie s'il y a un gagnant sur le plateau."""
    for y in range(3):
        coln, row = set(col(board, y)), set(board[y])  # Conversion en sets pour vérifier
        if coln in ({'x'}, {'o'}) or row in ({'x'}, {'o'}):  # Ligne ou colonne gagnante
            return True
        diag_, rev_diag = set(diag(board)), set(diag(board, reverse= True))  # Vérification des diagonales
        if diag_ in ({'x'}, {'o'}) or rev_diag in ({'x'}, {'o'}):  # Diagonale gagnante
            return True
    return False        

def update_pos(board: list, pos: tuple, player: str) -> None:
    """Met à jour la position du joueur sur le plateau."""
    board[pos[0]-1][pos[1]-1] = player  # Ajuste les indices 

def display(board: list) -> None:
    """Affiche le plateau de jeu."""
    print(f'-------------\n| {board[0][0]} | {board[0][1]} | {board[0][2]} | \n-------------\n'
          f'| {board[1][0]} | {board[1][1]} | {board[1][2]} |\n-------------\n'
          f'| {board[2][0]} | {board[2][1]} | {board[2][2]} |\n-------------')  # Affichage formaté

