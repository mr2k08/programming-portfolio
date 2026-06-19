import cowsay as cs
from fctMorpion import *
from robotMorpion import *
# Initialisation du plateau et des variables de jeu
board: list = [[' ']*3 for _ in range(3)]
player: bool = True
occupied: list = []

# Affichage du message de bienvenue et des règles
print("\nBienvenue au jeu des Morpions: \n\nRégles de jeu:\n "
"- choisir son mode de jeu\n "
"- entrer l'index de la colonne puis de la rangée afin de jouer\n")

# Demander le mode de jeu avec validation
choice: str = input('mode 2 joueurs? (\033[92moui\033[97m/\033[91mnon\033[97m): ')
while not choice in ('oui', 'non'):
    print('\ninvalide\n')
    choice = input('mode 2 joueurs? (\033[92moui\033[97m/\033[91mnon\033[97m): ')
print()
display(board)
match choice:
    case 'oui':
        # Mode 2 joueurs
        player = True
        while not check_winner(board): # S'assurer qu'on arrête le jeu si on a un gagnant
            icon: str = 'x' if player else 'o'
            coln: str = input(f'\033[94m{icon}: entrer col: \033[97m')
            rang: str = input(f'\033[96m{icon}: entrer rang: \033[97m')
            # Valider le coup
            while not isLegal(coln, rang, occupied):
                print('\nillegal\n')        
                coln, rang = input(f'\033[94m{icon}: entrer col: \033[97m'), input(f'\033[96m{icon}: entrer rang: \033[97m')
            coln, rang = int(coln), int(rang)
            occupied.append((rang, coln))
            # Vérifier si la partie est finie avant le prochain tour
            if check_winner(board) or len(occupied) == 9: 
                display(board)
                break
            # Mettre à jour le plateau
            update_pos(board, (rang, coln), icon)
            display(board)
            player = not player

    case 'non':
        # Mode contre le bot
        while not check_winner(board):
            player = 'x'
            coln: str = input(f'\033[94m{player}: entrer col: \033[97m')
            rang: str = input(f'\033[96m{player}: entrer rang: \033[97m')
            # Valider le coup du joueur
            while not isLegal(coln, rang, occupied):
                print('\nillegal\n')        
                coln, rang = input(f'\033[94m{player}: entrer col: \033[97m'), input(f'\033[96m{player}: entrer rang: \033[97m')
            coln, rang = int(coln), int(rang)
            # Vérifier si la partie est finie avant le prochain tour
            occupied.append((rang, coln))
            # Mettre à jour le plateau avec le coup du joueur
            update_pos(board, (rang, coln), player)
            if check_winner(board) or len(occupied) == 9: 
                display(board)
                break
            # Coup du bot
            player = 'o'
            comp_move = botMove(board)
            update_pos(board, comp_move, player)
            occupied.append(comp_move)
            display(board)    
        # Afficher le résultat

if check_winner(board): # Si 9 cases sont occupées alors on a exaeco
    cs.trex('\no a gagné !' if player in ('o', False) else '\nx a gagné !')
else: 
    cs.cow('\négalité\n')