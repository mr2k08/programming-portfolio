import numpy as np
from math import dist
from pieces import algebraic_reader, isLegal, display, update_position, diff, coord_legal, getInBetween, check_present

board = np.array([['bR','bk','bB','bQ','bK','bB','bk','bR'],
                  ['bP','bP','bP','bP','-','-','bP','bP'],
                  ['-', '-', '-', '-', '-', '-', '-', '-' ],
                  ['-', '-', '-', '-','bR', '-', '-', 'B' ],
                  ['-', '-', '-', '-', '-', '-', '-', '-' ],
                  ['-', 'Q', '-', '-', '-', '-', '-', '-' ],
                  ['P', 'P', '-', 'P', '-', 'P', 'P', 'P' ],
                  ['R', 'k', 'B', 'Q', 'K', '-', '-', 'bR' ]])

move = (algebraic_reader('b3'), algebraic_reader('e6'))
start_pos, end_pos = move[0], move[1]

if coord_legal('b3', start= True, color= 'white') and coord_legal('e6', start=False, color= 'black'):
    print('coords are legal\n')

print('in between diag: ', getInBetween(board, (0, 4), [(3, 7)]))
print('in between Rv: ', getInBetween(board, (7, 4), [(3, 4)]))
print('in between Rh: ', getInBetween(board, (7, 4), [(7, 7)]))

if isLegal(board,start_pos, end_pos):
    print('molecule')

    update_position(board, start_pos, end_pos)

display(board)

'''
bugs--

diag: correct
rv: correct
rh: fuck

'''
