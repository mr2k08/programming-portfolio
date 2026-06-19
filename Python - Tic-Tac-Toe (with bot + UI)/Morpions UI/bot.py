from game_logic import col, diag

def fill_in(line: tuple,
            is_column: bool = False,
            is_diagonal: bool = False,
            line_index: int = 0,
            reverse: bool = False) -> tuple:
    """
    Retourne la position de la case vide dans une ligne, colonne ou diagonale.
    Les coordonnées retournées sont en indices 0-based.
    """
    empty_index = line.index(' ')
    if is_column:
        return empty_index, line_index
    if is_diagonal:
        return empty_index, empty_index
    if reverse:
        return 2 - empty_index, empty_index

    return line_index, empty_index

def botAction(board: list, player: str):
    """
    Recherche un coup gagnant ou bloquant pour le joueur donné.
    Retourne une position (ligne, colonne) ou False.
    """
    for line_index in range(3):
        if board[line_index].count(player) == 2 and ' ' in board[line_index]:
            return fill_in(board[line_index], line_index=line_index)
        column_values = col(board, line_index)
        if column_values.count(player) == 2 and ' ' in column_values:
            return fill_in(column_values, is_column=True, line_index=line_index)
    diagonal_values = diag(board)
    if diagonal_values.count(player) == 2 and ' ' in diagonal_values:
        return fill_in(diagonal_values, is_diagonal=True)
    reverse_diagonal_values = diag(board, reverse=True)
    if reverse_diagonal_values.count(player) == 2 and ' ' in reverse_diagonal_values:
        return fill_in(reverse_diagonal_values, reverse=True)

    return False

def botMove(board: list) -> tuple:
    """
    Décide le coup du bot :
    1. Gagner
    2. Bloquer
    3. Jouer la première case libre
    """
    winning_move = botAction(board, 'o')
    if winning_move:
        return winning_move

    blocking_move = botAction(board, 'x')
    if blocking_move:
        return blocking_move

    for row_index in range(3):
        for column_index in range(3):
            if board[row_index][column_index] == ' ':
                return row_index, column_index
