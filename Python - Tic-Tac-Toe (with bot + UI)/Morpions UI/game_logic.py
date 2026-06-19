# fctMorpion.py

def diag(board: list, reverse: bool = False) -> tuple:
    """
    Retourne une diagonale du plateau.
    - reverse = True  : diagonale inversée
    """ 
    return (board[2][0], board[1][1], board[0][2]) if reverse else (board[0][0], board[1][1], board[2][2])
    


def col(board: list, column_index: int) -> tuple:
    """
    Retourne la colonne du plateau correspondant à l'indice donné.
    """
    return (
        board[0][column_index], board[1][column_index], board[2][column_index])


def check_winner(board: list) -> bool:
    """
    Vérifie si une ligne, colonne ou diagonale est entièrement occupée
    par le même joueur ('x' ou 'o').
    """
    for line_index in range(3):
        column_set = set(col(board, line_index))   # Ensemble des symboles d'une colonne
        row_set = set(board[line_index])            # Ensemble des symboles d'une ligne

        if column_set in ({'x'}, {'o'}) or row_set in ({'x'}, {'o'}):
            return True

        diagonal_set = set(diag(board))
        reverse_diagonal_set = set(diag(board, reverse=True))

        if diagonal_set in ({'x'}, {'o'}) or reverse_diagonal_set in ({'x'}, {'o'}):
            return True

    return False


def update_pos(board: list, position: tuple, player: str) -> None:
    """
    Met à jour le plateau avec le symbole du joueur.
    position est donnée sous la forme (ligne, colonne) en indices 0-based.
    """
    board[position[0]][position[1]] = player