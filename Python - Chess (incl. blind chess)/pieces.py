#type: ignore
import numpy as np
from math import dist
from itertools import product

# ═══════════════════════════════════════════════════════════════════════════════
# GAME STATE
# ═══════════════════════════════════════════════════════════════════════════════

board = np.array([
    ['bR','bk','bB','bQ','bK','bB','bk','bR'],
    ['bP','bP','bP','bP','bP','bP','bP','bP'],
    ['-', '-', '-', '-', '-', '-', '-', '-'],
    ['-', '-', '-', '-', '-', '-', '-', '-'],
    ['-', '-', '-', '-', '-', '-', '-', '-'],
    ['-', '-', '-', '-', '-', '-', '-', '-'],
    ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
    ['R', 'k', 'B', 'Q', 'K', 'B', 'k', 'R']
], dtype=object)

castling_rights = {
    'K':    True,   # white king
    'R_a':  True,   # white queenside rook col 0
    'R_h':  True,   # white kingside  rook col 7
    'bK':   True,
    'bR_a': True,
    'bR_h': True,
}

en_passant_target = None  # (row, col) or None

# ═══════════════════════════════════════════════════════════════════════════════
# BACKEND — pure logic, no I/O
# ═══════════════════════════════════════════════════════════════════════════════

# ── shared utilities ──────────────────────────────────────────────────────────

def algebraic_reader(move):
    return 8 - int(move[1]), 'abcdefgh'.index(move[0])

def diff(i, A, B):
    return abs(A[i] - B[i])

def in_bounds(y, x):
    return 0 <= y <= 7 and 0 <= x <= 7

def color_of(piece):
    return 'black' if piece.startswith('b') else 'white'

def own_len(color):
    return 1 if color == 'white' else 2

# ── sliding piece helpers ─────────────────────────────────────────────────────

def check_ray(board, start_pos, end_pos, dy, dx):
    y, x = start_pos[0] + dy, start_pos[1] + dx
    while (y, x) != end_pos:
        if not in_bounds(y, x) or board[y, x] != '-':
            return False
        y += dy
        x += dx
    return True

def check_straight(board, start_pos, end_pos):
    if start_pos[0] == end_pos[0]:
        return check_ray(board, start_pos, end_pos, 0, 1 if end_pos[1] > start_pos[1] else -1)
    if start_pos[1] == end_pos[1]:
        return check_ray(board, start_pos, end_pos, 1 if end_pos[0] > start_pos[0] else -1, 0)
    return False

def check_diagonal(board, start_pos, end_pos):
    if diff(0, start_pos, end_pos) != diff(1, start_pos, end_pos):
        return False
    dy = 1 if end_pos[0] > start_pos[0] else -1
    dx = 1 if end_pos[1] > start_pos[1] else -1
    return check_ray(board, start_pos, end_pos, dy, dx)

# ── move legality ─────────────────────────────────────────────────────────────

def isLegal(board, start_pos, end_pos, skip_king_safety=False):
    global en_passant_target

    if start_pos == end_pos:
        return False
    piece  = board[start_pos]
    target = board[end_pos]
    if target != '-' and color_of(target) == color_of(piece):
        return False

    match piece:

        case 'R' | 'bR':
            return check_straight(board, start_pos, end_pos)

        case 'B' | 'bB':
            return check_diagonal(board, start_pos, end_pos)

        case 'Q' | 'bQ':
            return check_straight(board, start_pos, end_pos) \
                or check_diagonal(board, start_pos, end_pos)

        case 'k' | 'bk':
            return dist(start_pos, end_pos) == 5 ** 0.5

        case 'K' | 'bK':
            if abs(start_pos[0] - end_pos[0]) > 1 or abs(start_pos[1] - end_pos[1]) > 1:
                return False
            if skip_king_safety:
                return True
            color    = color_of(piece)
            captured = board[end_pos]
            board[end_pos], board[start_pos] = piece, '-'
            in_check = check_present(board, color)
            board[start_pos], board[end_pos] = piece, captured
            return not in_check

        case 'P' | 'bP':
            is_white  = piece == 'P'
            dy        = -1 if is_white else  1
            home_row  =  6 if is_white else  1
            enemy_len =  2 if is_white else  1
            row_diff  = end_pos[0] - start_pos[0]
            col_diff  = diff(1, start_pos, end_pos)

            if row_diff == dy and col_diff == 0 and target == '-':
                return True
            if row_diff == dy and col_diff == 1 and target != '-' and len(target) == enemy_len:
                return True
            if row_diff == 2*dy and col_diff == 0 and start_pos[0] == home_row \
                    and target == '-' and board[start_pos[0] + dy, start_pos[1]] == '-':
                return True
            if row_diff == dy and col_diff == 1 and end_pos == en_passant_target:
                return True
            return False

    return False

# ── castling ──────────────────────────────────────────────────────────────────

def castle(board, color='white'):
    row    = 7  if color == 'white' else 0
    k_key  = 'K'    if color == 'white' else 'bK'
    rh_key = 'R_h'  if color == 'white' else 'bR_h'
    ra_key = 'R_a'  if color == 'white' else 'bR_a'

    if board[row, 4] != k_key:      return []
    if not castling_rights[k_key]:  return []
    if check_present(board, color): return []

    results = []

    if castling_rights[rh_key] and board[row,5] == '-' and board[row,6] == '-':
        if not _king_through_check(board, (row,4), (row,5), color) \
           and not _king_through_check(board, (row,4), (row,6), color):
            results.append((row, 6))

    if castling_rights[ra_key] \
            and board[row,3] == '-' and board[row,2] == '-' and board[row,1] == '-':
        if not _king_through_check(board, (row,4), (row,3), color) \
           and not _king_through_check(board, (row,4), (row,2), color):
            results.append((row, 2))

    return results

def _king_through_check(board, king_pos, square, color):
    piece = board[king_pos]
    board[square], board[king_pos] = piece, '-'
    attacked = bool(check_present(board, color))
    board[king_pos], board[square] = piece, '-'
    return attacked

def apply_castle(board, color, end_col):
    row   = 7 if color == 'white' else 0
    rook  = 'R' if color == 'white' else 'bR'
    k_key = 'K' if color == 'white' else 'bK'

    if end_col == 6:
        board[row,6], board[row,4] = board[row,4], '-'
        board[row,5], board[row,7] = rook, '-'
        castling_rights['R_h' if color == 'white' else 'bR_h'] = False
    else:
        board[row,2], board[row,4] = board[row,4], '-'
        board[row,3], board[row,0] = rook, '-'
        castling_rights['R_a' if color == 'white' else 'bR_a'] = False

    castling_rights[k_key] = False

# ── en passant ────────────────────────────────────────────────────────────────

def apply_en_passant(board, start_pos, end_pos):
    board[end_pos]                  = board[start_pos]
    board[start_pos]                = '-'
    board[start_pos[0], end_pos[1]] = '-'

# ── position update ───────────────────────────────────────────────────────────

def update_position(board, start_pos, end_pos):
    global en_passant_target
    piece = board[start_pos]
    en_passant_target = None

    if piece == 'P'  and start_pos[0] - end_pos[0] == 2:
        en_passant_target = (start_pos[0] - 1, start_pos[1])
    elif piece == 'bP' and end_pos[0] - start_pos[0] == 2:
        en_passant_target = (start_pos[0] + 1, start_pos[1])

    if   piece == 'K':  castling_rights['K']  = castling_rights['R_h']  = castling_rights['R_a']  = False
    elif piece == 'bK': castling_rights['bK'] = castling_rights['bR_h'] = castling_rights['bR_a'] = False
    elif piece == 'R':
        if start_pos == (7, 0): castling_rights['R_a'] = False
        if start_pos == (7, 7): castling_rights['R_h'] = False
    elif piece == 'bR':
        if start_pos == (0, 0): castling_rights['bR_a'] = False
        if start_pos == (0, 7): castling_rights['bR_h'] = False

    board[end_pos], board[start_pos] = piece, '-'

# ── check / checkmate / stalemate ─────────────────────────────────────────────

def check_present(board, color='white'):
    ky, kx = np.where(board == ('K' if color == 'white' else 'bK'))
    ky, kx = ky.item(), kx.item()
    attackers = [
        (y, x)
        for y in range(8) for x in range(8)
        if isLegal(board, (y,x), (ky,kx), skip_king_safety=True)
    ]
    return attackers if attackers else False

def checkmate_present(board, current_color='white'):
    attackers = check_present(board, current_color)
    if not attackers:
        return False

    ky, kx = np.where(board == ('K' if current_color == 'white' else 'bK'))
    ky, kx = ky.item(), kx.item()

    for offset in product([1,0,-1], repeat=2):
        sq = (ky + offset[0], kx + offset[1])
        if in_bounds(*sq) and isLegal(board, (ky,kx), sq):
            return False

    if len(attackers) > 1:
        return True

    blocking_squares = getInBetween(board, (ky,kx), attackers)
    blocking_squares.append([attackers[0]])
    return not isBlockable(board, blocking_squares, current_color)

def stalemate_present(board, color):
    if check_present(board, color):
        return False
    ol = own_len(color)
    for start in product(range(8), repeat=2):
        if board[start] == '-' or len(board[start]) != ol:
            continue
        for end in product(range(8), repeat=2):
            if isLegal(board, start, end):
                return False
    return True

def isBlockable(board, square_groups, color='white'):
    ol = own_len(color)
    covered = 0
    for coord in product(range(8), repeat=2):
        p = board[coord]
        if p == '-' or len(p) != ol:
            continue
        for i, group in enumerate(square_groups):
            if not group or group[0] == (-1,-1):
                continue
            if any(isLegal(board, coord, sq) for sq in group):
                covered += 1
                square_groups[i] = [(-1,-1)]
                break
    return covered >= len(square_groups)

def getInBetween(board, king_pos, attackers_pos):
    result = []
    for attacker in attackers_pos:
        t = board[attacker]
        if t in ('R','bR','Q','bQ'):
            if attacker[0] == king_pos[0]:
                mn = min(king_pos[1], attacker[1])
                result.append([(king_pos[0], mn+i+1) for i in range(diff(1,king_pos,attacker)-1)])
            elif attacker[1] == king_pos[1]:
                mn = min(king_pos[0], attacker[0])
                result.append([(mn+i+1, king_pos[1]) for i in range(diff(0,king_pos,attacker)-1)])
        if t in ('B','bB','Q','bQ'):
            dy = 1 if attacker[0] < king_pos[0] else -1
            dx = 1 if attacker[1] < king_pos[1] else -1
            y, x = attacker[0]+dy, attacker[1]+dx
            diag = []
            while (y,x) != king_pos:
                diag.append((y,x))
                y += dy; x += dx
            result.append(diag)
    return result

# ── pawn promotion ────────────────────────────────────────────────────────────

def promote_pawn(board, pos, color):
    options = {'q':'Q','r':'R','b':'B','k':'k'} if color == 'white' \
         else {'q':'bQ','r':'bR','b':'bB','k':'bk'}
    while True:
        choice = input("Promote to (q=Queen, r=Rook, b=Bishop, k=Knight) [q]: ").strip().lower() or 'q'
        if choice in options:
            board[pos] = options[choice]
            return
        print("Invalid choice.")

# ═══════════════════════════════════════════════════════════════════════════════
# FRONTEND — display, input parsing, notation
# ═══════════════════════════════════════════════════════════════════════════════

# ── ANSI constants ────────────────────────────────────────────────────────────

RESET    = '\033[0m'
BOLD     = '\033[1m'
BG_LIGHT = '\033[48;5;222m'
BG_DARK  = '\033[48;5;130m'
FG_WHITE         = '\033[97m\033[1m'              # bright white — white pieces
FG_BLACK_ON_LIGHT = '\033[38;2;180;80;0m\033[1m'  # burnt orange RGB — black pieces on cream
FG_BLACK_ON_DARK  = '\033[38;2;255;160;0m\033[1m'  # bright orange RGB — black pieces on brown
FG_RANK  = '\033[38;5;244m'
FG_CHECK = '\033[91m'
FG_TITLE = '\033[38;5;214m'
FG_NUM   = '\033[38;5;240m'
DIM      = '\033[2m'

PIECES = {
    'K': '♔','Q': '♕','R': '♖','B': '♗','k': '♘','P': '♙',
    'bK':'♚','bQ':'♛','bR':'♜','bB':'♝','bk':'♞','bP':'♟',
    '-': ' ',
}

# ── board + panel display ─────────────────────────────────────────────────────

def display(board, color='white', in_check=False, move_history=None):
    if move_history is None: move_history = []
    rows  = board if color == 'white' else np.rot90(board, 2)
    files = 'abcdefgh' if color == 'white' else 'hgfedcba'
    ranks = list(range(8,0,-1)) if color == 'white' else list(range(1,9))
    player = "White" if color == 'white' else "Black"

    print('\033[2J\033[H', end='')
    print(f"\n  {FG_TITLE}{BOLD}♟  C H E S S  —  {player}'s turn{RESET}\n")

    SQ = 4

    board_lines = []
    for row_i, row in enumerate(rows):
        rank = ranks[row_i]
        top = "   "
        mid = f" {FG_RANK}{BOLD}{rank}{RESET} "
        for col_i, piece in enumerate(row):
            is_light = (row_i + col_i) % 2 == 0
            bg  = BG_LIGHT if is_light else BG_DARK
            fg  = (FG_BLACK_ON_LIGHT if is_light else FG_BLACK_ON_DARK) if piece.startswith('b') else FG_WHITE
            sym = PIECES.get(piece, '?')
            pad_l = (SQ - 1) // 2
            pad_r = SQ - 1 - pad_l
            empty = ' ' * SQ
            top += f"{bg}{empty}{RESET}"
            mid += f"{bg}{fg}{' '*pad_l}{sym}{' '*pad_r}{RESET}"
        board_lines.append(top)
        board_lines.append(mid)

    board_lines.append(
        "    " + "".join(
            f"{' ' * ((SQ-1)//2)}{FG_RANK}{BOLD}{f}{RESET}{' ' * (SQ - (SQ-1)//2 - 1)}"
            for f in files
        )
    )

    W = 20
    T = f"{FG_TITLE}{BOLD}"
    board_h = len(board_lines)

    panel = []
    panel.append(f"{T}┌{'─'*W}┐{RESET}")
    panel.append(f"{T}│{'MOVE HISTORY':^{W}}│{RESET}")
    panel.append(f"{T}├{'─'*W}┤{RESET}")

    pairs, hist, n = [], move_history[:], 1
    while hist:
        w = hist.pop(0)
        b = hist.pop(0) if hist else ''
        pairs.append((n, w, b)); n += 1

    max_rows = board_h - 4
    for num, w, b in (pairs[-max_rows:] if len(pairs) > max_rows else pairs):
        used = 5 + len(w) + (3 + len(b) if b else 0)
        pad  = max(W - used, 0)
        colored = (
            f" {FG_NUM}{num:>2}.{RESET} {FG_WHITE}{w}{RESET}"
            + (f"   {FG_BLACK_ON_DARK}{b}{RESET}" if b else "")
            + " " * pad
        )
        panel.append(f"{T}│{RESET}{colored}{T}│{RESET}")

    while len(panel) < board_h - 2:
        panel.append(f"{T}│{' '*W}│{RESET}")
    panel.append(f"{T}└{'─'*W}┘{RESET}")
    panel.append("")

    while len(board_lines) < len(panel): board_lines.append("")
    while len(panel) < len(board_lines): panel.append("")

    for bl, pl in zip(board_lines, panel):
        print(f"{bl}   {pl}")
    print()
    if in_check:
        print(f"  {FG_CHECK}{BOLD}⚠  Check!{RESET}\n")

# ── input validation ──────────────────────────────────────────────────────────

def coord_legal(coord, color='white', start=True):
    if len(coord) != 2 or coord[0] not in 'abcdefgh' \
            or not coord[1].isdigit() or not 0 < int(coord[1]) < 9:
        return False
    piece = board[algebraic_reader(coord)]
    if start and len(piece) != own_len(color):
        return False
    return True

def parse_move(raw):
    raw = raw.strip().lower()
    if raw in ('o-o', '0-0'):     return ('castle', 'kingside')
    if raw in ('o-o-o', '0-0-0'): return ('castle', 'queenside')
    raw = raw.replace(' ', '')
    if len(raw) == 4 and raw[0] in 'abcdefgh' and raw[1].isdigit() \
            and raw[2] in 'abcdefgh' and raw[3].isdigit():
        return raw[:2], raw[2:]
    return None

# ── move notation ─────────────────────────────────────────────────────────────

def move_to_notation(board, start_pos, end_pos, is_castle=None, is_ep=False):
    files = 'abcdefgh'
    if is_castle == 'kingside':  return 'O-O'
    if is_castle == 'queenside': return 'O-O-O'
    piece     = board[start_pos]
    piece_sym = {'K':'K','Q':'Q','R':'R','B':'B','k':'N','P':'',
                 'bK':'K','bQ':'Q','bR':'R','bB':'B','bk':'N','bP':''}
    sym     = piece_sym.get(piece, '')
    capture = 'x' if board[end_pos] != '-' or is_ep else ''
    if piece in ('P','bP') and capture:
        sym = files[start_pos[1]]
    dest = files[end_pos[1]] + str(8 - end_pos[0])
    return f"{sym}{capture}{dest}"

# ═══════════════════════════════════════════════════════════════════════════════
# GAME LOOP
# ═══════════════════════════════════════════════════════════════════════════════

def game_loop():
    global board, castling_rights, en_passant_target

    board = np.array([
        ['bR','bk','bB','bQ','bK','bB','bk','bR'],
        ['bP','bP','bP','bP','bP','bP','bP','bP'],
        ['-', '-', '-', '-', '-', '-', '-', '-'],
        ['-', '-', '-', '-', '-', '-', '-', '-'],
        ['-', '-', '-', '-', '-', '-', '-', '-'],
        ['-', '-', '-', '-', '-', '-', '-', '-'],
        ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
        ['R', 'k', 'B', 'Q', 'K', 'B', 'k', 'R']
    ], dtype=object)
    castling_rights    = {'K':True,'R_a':True,'R_h':True,'bK':True,'bR_a':True,'bR_h':True}
    en_passant_target  = None
    move_history       = []
    turn               = 'white'

    while True:
        in_check = bool(check_present(board, turn))

        if checkmate_present(board, turn):
            display(board, turn, in_check=True, move_history=move_history)
            winner = 'Black' if turn == 'white' else 'White'
            print(f"  {FG_CHECK}{BOLD}♚  Checkmate! {winner} wins.{RESET}\n")
            break

        if stalemate_present(board, turn):
            display(board, turn, move_history=move_history)
            print(f"  {FG_TITLE}{BOLD}½  Stalemate — draw.{RESET}\n")
            break

        display(board, turn, in_check=in_check, move_history=move_history)

        raw = input(f"  Move (e.g. e2 e4  |  O-O  |  O-O-O  |  quit) → ").strip()
        if raw.lower() == 'quit':
            print("Game over.")
            break

        parsed = parse_move(raw)
        if parsed is None:
            print("Invalid format. Use 'e2 e4' or 'O-O' / 'O-O-O'.")
            continue

        if parsed[0] == 'castle':
            legal_castle_squares = castle(board, turn)
            target_col = 6 if parsed[1] == 'kingside' else 2
            target_row = 7 if turn == 'white' else 0
            if (target_row, target_col) in legal_castle_squares:
                side = 'kingside' if target_col == 6 else 'queenside'
                move_history.append(move_to_notation(board, (target_row,4), (target_row,target_col), is_castle=side))
                apply_castle(board, turn, target_col)
                turn = 'black' if turn == 'white' else 'white'
            else:
                print("Castling not available.")
            continue

        start_coord, end_coord = parsed

        if not coord_legal(start_coord, turn, start=True):
            print("No valid piece at that square for your color.")
            continue
        if not coord_legal(end_coord, turn, start=False):
            print("Invalid destination square.")
            continue

        start_pos = algebraic_reader(start_coord)
        end_pos   = algebraic_reader(end_coord)

        if not isLegal(board, start_pos, end_pos):
            print("Illegal move.")
            continue

        piece = board[start_pos]
        is_en_passant = piece in ('P','bP') and end_pos == en_passant_target \
                        and diff(1, start_pos, end_pos) == 1

        notation = move_to_notation(board, start_pos, end_pos, is_ep=is_en_passant)
        if is_en_passant:
            apply_en_passant(board, start_pos, end_pos)
            en_passant_target = None
        else:
            update_position(board, start_pos, end_pos)
        move_history.append(notation)

        if board[end_pos] == 'P'  and end_pos[0] == 0:
            promote_pawn(board, end_pos, 'white')
        elif board[end_pos] == 'bP' and end_pos[0] == 7:
            promote_pawn(board, end_pos, 'black')

        turn = 'black' if turn == 'white' else 'white'

if __name__ == '__main__':
    game_loop()