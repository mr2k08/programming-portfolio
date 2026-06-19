from fctMorpion import col, diag

def fill_in(lst: tuple, col: bool = False, diag: bool = False, i: int = 0, reverse: bool = False) -> tuple:
    """Trouve et retourne la position de la case vide dans une rangée/colonne/diagonale a 2/3 occupée."""
    if col: 
        return lst.index(' ') + 1, i + 1  # Colonne: retourne (index vide + 1, ligne)
    if diag: 
        return lst.index(' ') + 1, lst.index(' ') + 1  # Diagonale: retourne 
    if reverse: 
        return 3 - lst.index(' '), lst.index(' ') + 1  # Diagonale inversée: ajuste la première coordonnée
    return i + 1, lst.index(' ') + 1  # Ligne: retourne (ligne, index vide + 1)

def botAction(board: list, player: str) -> tuple | bool:
    """Analyse les lignes, colonnes et diagonales pour trouver un coup gagnant ou bloquer."""
    for i in range(3):
        if board[i].count(player) == 2 and (' ' in board[i]):  # Vérifie si une ligne peut être complétée
            return fill_in(board[i], i=i)  # Retourne la position gagnante
        coln = col(board, i) 
        if coln.count(player) == 2 and (' ' in coln):  # Vérifie si une colonne peut être complétée
            return fill_in(coln, i=i, col=True)  
        
    diag_, rev_diag = diag(board), diag(board, reverse= True)  
    if (diag_.count(player) == 2) and (' ' in diag_):  # Vérifie la diagonale normale
        return fill_in(diag_, diag = True, i=i)  # Retourne le coup gagnant
    if (rev_diag.count(player) == 2) and (' ' in rev_diag):  # Vérifie la diagonale inversée
        return fill_in(rev_diag, i=i, reverse= True)  
    return False  # Aucun coup gagnant trouvé

def botMove(board: list) -> tuple:
    """Décide le coup du bot: gagne d'abord, puis bloque, puis joue aléatoirement."""
    if botAction(board, 'o'):  # Priorité 1: cherche un coup gagnant
        return botAction(board, 'o')  
    elif botAction(board, 'x'):  # Priorité 2: bloque le joueur
        return botAction(board, 'x')  
    for y in range(3):  # Priorité 3: cherche une case libre
        for x in range(3):     
            if board[y][x] == ' ':  # Trouvé une case libre
                return y + 1, x + 1  

