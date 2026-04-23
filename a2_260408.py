# -*- coding: utf-8 -*-
"""
Co Ganh AI - Assignment 2 Semester 2 25-26
Author: AI-enhanced version

Algorithm: Iterative Deepening Alpha-Beta Pruning
Techniques:
    - F_Piece_Diff     : Piece difference (W1 highest priority)
  - F_Positional_Control : Board control by positional weights
  - F_Mobility       : Mobility
  - Make/Unmake Move : Replace copy_board to speed up
  - Zobrist Hashing  : Extremely fast 64-bit state encoding
  - Transposition Table : Table to store visited states
  - Advanced Move Ordering : TT-move -> Ganh/Chet -> Killer -> History
  - Quiescence Search : Avoid Horizon Effect at leaf nodes
  - Phase-based Weights : Early/Mid/Late game weight tuning
"""

import random
import time


def init_board():
    board = [[+1, +1, +1, +1, +1],
             [+1,  0,  0,  0, +1],
             [+1,  0,  0,  0, -1],
             [-1,  0,  0,  0, -1],
             [-1, -1, -1, -1, -1]]
    return board

def copy_board(board):
    return [row[:] for row in board]

def print_board(board):
    for i in range(5):
        for j in range(5):
            if board[4-i][j] == 1:
                print('X', end=' ')
            elif board[4-i][j] == -1:
                print('O', end=' ')
            else:
                print('-', end=' ')
        print()
    print()

def dict_neighbors():
    dict_n = {}
    for i in range(5):
        for j in range(5):
            temp = []
            if j == 0:
                temp.append((i, j+1))
            if j == 4:
                temp.append((i, j-1))
            if j > 0 and j < 4:
                temp.append((i, j-1))
                temp.append((i, j+1))
            if i == 0:
                temp.append((i+1, j))
            if i == 4:
                temp.append((i-1, j))
            if i > 0 and i < 4:
                temp.append((i-1, j))
                temp.append((i+1, j))
            if i == j:
                if i == 0:
                    temp.append((i+1, j+1))
                elif i == 4:
                    temp.append((i-1, j-1))
                else:
                    temp.append((i-1, j-1))
                    temp.append((i+1, j+1))
                    temp.append((i+1, j-1))
                    temp.append((i-1, j+1))
            elif i+j == 4:
                if i == 0:
                    temp.append((i+1, j-1))
                elif i == 4:
                    temp.append((i-1, j+1))
                else:
                    temp.append((i-1, j-1))
                    temp.append((i+1, j+1))
                    temp.append((i+1, j-1))
                    temp.append((i-1, j+1))
            if i == 0 and j == 2:
                temp.append((i+1, j-1))
                temp.append((i+1, j+1))
            if i == 4 and j == 2:
                temp.append((i-1, j-1))
                temp.append((i-1, j+1))
            if i == 2 and j == 0:
                temp.append((i+1, j+1))
                temp.append((i-1, j+1))
            if i == 2 and j == 4:
                temp.append((i+1, j-1))
                temp.append((i-1, j-1))
            dict_n[(i, j)] = temp
    return dict_n

dict_nei = dict_neighbors()

def get_valid_moves(board, player):
    re = []
    for i in range(5):
        for j in range(5):
            if board[i][j] == player:
                start = (i, j)
                for item in dict_nei[start]:
                    if board[item[0]][item[1]] == 0:
                        re.append((start, item))
    return re

def ngang(board, i, j, enemy):
    ret = []
    if (board[i][j-1] == enemy) and (board[i][j-1] == board[i][j+1]):
        ret.append((i, j-1))
        ret.append((i, j+1))
    return ret

def doc(board, i, j, enemy):
    ret = []
    if (board[i+1][j] == enemy) and (board[i+1][j] == board[i-1][j]):
        ret.append((i+1, j))
        ret.append((i-1, j))
    return ret

def cheo_1(board, i, j, enemy):
    ret = []
    if (board[i+1][j-1] == enemy) and (board[i+1][j-1] == board[i-1][j+1]):
        ret.append((i+1, j-1))
        ret.append((i-1, j+1))
    return ret

def cheo_2(board, i, j, enemy):
    ret = []
    if (board[i+1][j+1] == enemy) and (board[i+1][j+1] == board[i-1][j-1]):
        ret.append((i+1, j+1))
        ret.append((i-1, j-1))
    return ret

def ganh(board, i, j, enemy):
    ret = []
    if (i, j) in [(1, 1), (2, 2), (3, 3), (3, 1), (1, 3)]:
        ret = doc(board, i, j, enemy) + ngang(board, i, j, enemy) + \
              cheo_1(board, i, j, enemy) + cheo_2(board, i, j, enemy)
    if (i, j) in [(2, 1), (2, 3), (1, 2), (3, 2)]:
        ret = doc(board, i, j, enemy) + ngang(board, i, j, enemy)
    if (i, j) in [(0, 1), (0, 2), (0, 3), (4, 1), (4, 2), (4, 3)]:
        ret = ngang(board, i, j, enemy)
    if (i, j) in [(1, 0), (2, 0), (3, 0), (1, 4), (2, 4), (3, 4)]:
        ret = doc(board, i, j, enemy)
    return ret

def tim_lien_thong(i, j, enemy, board):
    ret = [(i, j)]
    candidates = list(dict_nei[(i, j)])
    for item in candidates:
        if board[item[0]][item[1]] == enemy and item not in ret:
            ret.append(item)
            for k in dict_nei[item]:
                if k not in candidates:
                    candidates.append(k)
    return ret

def thanh_phan_lien_thong(board, enemy):
    lien_thong = []
    for i in range(5):
        for j in range(5):
            if board[i][j] == enemy:
                add = all((i, j) not in lt for lt in lien_thong)
                if add:
                    lien_thong.append(tim_lien_thong(i, j, enemy, board))
    return lien_thong

def tim_khi(tplt, board):
    tap_khi = {}
    for idx, item_set in enumerate(tplt):
        temp = []
        for item in item_set:
            for nei in dict_nei[item]:
                if nei not in temp and board[nei[0]][nei[1]] == 0:
                    temp.append(nei)
        tap_khi[idx] = len(temp)
    return tap_khi

def chet(board, enemy):
    player = -enemy
    tplt = thanh_phan_lien_thong(board, enemy)
    khi = tim_khi(tplt, board)
    ret = False
    for i in range(len(khi)):
        if khi[i] == 0:
            ret = True
            for (pi, pj) in tplt[i]:
                board[pi][pj] = player
    return ret

def act_moves(move, player, board):
    start, end = move
    board[start[0]][start[1]] = 0
    board[end[0]][end[1]] = player
    list_ganh = ganh(board, end[0], end[1], player * -1)
    for item in list_ganh:
        board[item[0]][item[1]] = player
    ret2 = chet(board, player * -1)
    mo = []
    if len(list_ganh) == 0 and not ret2:
        for item in dict_nei[start]:
            if board[item[0]][item[1]] == -1 * player:
                board_copy = copy_board(board)
                move_temp = (item, start)
                if ganh(board_copy, start[0], start[1], player):
                    mo.append(move_temp)
    return mo

def npc_move(board, player, mo=None):
    if mo is None:
        mo = []
    moves = get_valid_moves(board, player)
    if not moves:
        return None
    if mo:
        for m in moves:
            if m in mo:
                return m
    chose_move = moves[random.randint(0, len(moves) - 1)]
    for item in moves:
        end = item[1]
        board_copy = copy_board(board)
        enemy = player * -1
        l_ganh = ganh(board_copy, end[0], end[1], enemy)
        if l_ganh:
            return item
        start = item[0]
        board_copy = copy_board(board)
        board_copy[start[0]][start[1]] = 0
        board_copy[end[0]][end[1]] = player
        if chet(board_copy, -player):
            return item
    return chose_move

def count_X(board):
    return sum(1 for i in range(5) for j in range(5) if board[i][j] == 1)


_rng_z = random.Random(20250506)          # fixed seed for reproducibility
ZOBRIST_TABLE = {
    (i, j, p): _rng_z.getrandbits(64)
    for i in range(5) for j in range(5) for p in (1, -1)
}

def compute_hash(board):
    """Encode board state into a 64-bit integer."""
    h = 0
    for i in range(5):
        for j in range(5):
            v = board[i][j]
            if v != 0:
                h ^= ZOBRIST_TABLE[(i, j, v)]
    return h


WEIGHT_MATRIX = [
    [1, 2, 3, 2, 1],
    [2, 5, 3, 5, 2],
    [3, 3, 8, 3, 3],
    [2, 5, 3, 5, 2],
    [1, 2, 3, 2, 1],
]


def count_pieces_both(board):
    p1 = pm1 = 0
    for i in range(5):
        for j in range(5):
            v = board[i][j]
            if v == 1:
                p1 += 1
            elif v == -1:
                pm1 += 1
    return p1, pm1

# Weights learned from Q-learning (train_rl_weights.py)
_RL_WEIGHTS = [0.763115, 0.606672, -0.269779]
W_PIECE = 100
RATIO_POS = _RL_WEIGHTS[1] / _RL_WEIGHTS[0]
RATIO_MOB = _RL_WEIGHTS[2] / _RL_WEIGHTS[0]
W_POS = 30 * RATIO_POS
W_MOB = 15 * RATIO_MOB

def evaluate(board, player):
    """Hybrid evaluation: RL (3 dimensions) + phase-aware explicit terms."""
    p_us = 0
    p_enemy = 0
    score_pos = 0
    score_mob = 0

    for i in range(5):
        for j in range(5):
            v = board[i][j]
            if v == 0:
                continue
            free_spaces = 0
            for ni, nj in dict_nei[(i, j)]:
                if board[ni][nj] == 0:
                    free_spaces += 1
            if v == player:
                p_us += 1
                score_pos += WEIGHT_MATRIX[i][j]
                score_mob += free_spaces
            else:
                p_enemy += 1
                score_pos -= WEIGHT_MATRIX[i][j]
                score_mob -= free_spaces

    if p_us == 0:
        return -999999
    if p_enemy == 0:
        return 999999

    score = (W_PIECE * (p_us - p_enemy)) + (W_POS * score_pos) + (W_MOB * score_mob)

    if min(p_us, p_enemy) < 5: 
        score += 25 * score_mob # End game mobility bonus
        score += 100 * (p_us - p_enemy) # End game piece difference bonus
    return score


def make_move_inplace(board, move, player):
    """
    Apply move DIRECTLY to board (no copy).
    Return undo_info dict to unmake later.
    """
    start, end = move
    enemy = -player

    board[start[0]][start[1]] = 0
    board[end[0]][end[1]] = player

    list_ganh = ganh(board, end[0], end[1], enemy)
    for pos in list_ganh:
        board[pos[0]][pos[1]] = player

    chet_killed = []
    tplt = thanh_phan_lien_thong(board, enemy)
    khi = tim_khi(tplt, board)
    for idx in range(len(khi)):
        if khi[idx] == 0:
            for pos in tplt[idx]:
                chet_killed.append(pos)
                board[pos[0]][pos[1]] = player

    mo = []
    if not list_ganh and not chet_killed:
        for item in dict_nei[start]:
            if board[item[0]][item[1]] == enemy:
                board_tmp = copy_board(board)
                if ganh(board_tmp, start[0], start[1], player):
                    mo.append((item, start))

    return {
        'start': start,
        'end': end,
        'list_ganh': list_ganh,
        'chet_killed': chet_killed,
        'mo': mo,
    }

def unmake_move_inplace(board, undo, player):
    """Undo make_move_inplace. Restore order: chet -> ganh -> move."""
    enemy = -player
    for pos in undo['chet_killed']:
        board[pos[0]][pos[1]] = enemy
    for pos in undo['list_ganh']:
        board[pos[0]][pos[1]] = enemy
    board[undo['end'][0]][undo['end'][1]] = 0
    board[undo['start'][0]][undo['start'][1]] = player


# ============================================================
#  PART 6 - LOW-LEVEL ORDERING HELPERS (pure)
# ============================================================

def _quick_ganh_count(board, move, player):
    """Quickly count pieces captured by a move (no chet, no allocation)."""
    (si, sj), (ei, ej) = move
    old_s = board[si][sj]
    old_e = board[ei][ej]
    board[si][sj] = 0
    board[ei][ej] = player
    count = len(ganh(board, ei, ej, -player))
    board[si][sj] = old_s
    board[ei][ej] = old_e
    return count

def _mo_signature(mo):
    if not mo:
        return ()
    return tuple(sorted(mo))


# ============================================================
#  PART 7 - ALPHA-BETA AGENT CLASS
# ============================================================

class AlphaBetaAgent:
    """
    Self-contained alpha-beta agent.

    Encapsulates per-instance mutable state:
      - Transposition Table (Zobrist-keyed)
      - Killer Heuristic
      - History Heuristic
      - (Optional) custom evaluator injected via constructor

    Search pipeline:
      iterative deepening -> alpha-beta -> quiescence -> evaluate
    """

    EXACT = 0
    LOWER_BOUND = 1
    UPPER_BOUND = 2

    def __init__(self,
                 evaluator=None,
                 tt_max=600_000,
                 max_depth=12,
                 time_cap=2.95,
                 time_min=0.5,
                 time_frac=0.1):
        self._evaluator = evaluator  # None -> use module-level evaluate()
        self.tt = {}
        self.tt_max = tt_max
        self.killer_moves = {}
        self.history = {}
        self.max_depth = max_depth
        self.time_cap = time_cap
        self.time_min = time_min
        self.time_frac = time_frac

    # ---------- evaluation ----------
    def evaluate(self, board, player):
        if self._evaluator is not None:
            return self._evaluator(board, player)
        return evaluate(board, player)

    # ---------- transposition table ----------
    def _tt_lookup(self, h, mo_sig, depth, alpha, beta):
        key = (h, mo_sig)
        if key not in self.tt:
            return None, None, False
        entry = self.tt[key]
        best_move = entry.get('best_move')
        if entry['depth'] < depth:
            return None, best_move, False
        flag = entry['flag']
        score = entry['score']
        if flag == self.EXACT:
            return score, best_move, True
        if flag == self.LOWER_BOUND:
            alpha = max(alpha, score)
        elif flag == self.UPPER_BOUND:
            beta = min(beta, score)
        if alpha >= beta:
            return score, best_move, True
        return None, best_move, False

    def _tt_store(self, h, mo_sig, depth, score, flag, best_move):
        if len(self.tt) >= self.tt_max:
            self.tt.clear()
        self.tt[(h, mo_sig)] = {
            'depth': depth,
            'score': score,
            'flag': flag,
            'best_move': best_move,
        }

    def _score_move_for_ordering(self, board, move, player, depth, tt_move):
        """
        Priority order:
            1. TT-move           (highest)
            2. Ganh/Chet move    (immediate capture)
            3. Killer Heuristic
            4. History Heuristic
            5. Destination position score
        """
        if move == tt_move:
            return 2_000_000

        score = 0
        g_count = _quick_ganh_count(board, move, player)
        if g_count > 0:
            score += 100_000 * g_count

        killers = self.killer_moves.get(depth, [])
        if move in killers:
            score += 50_000

        score += self.history.get(move, 0)
        score += WEIGHT_MATRIX[move[1][0]][move[1][1]] * 10
        return score

    def _order_moves(self, board, moves, player, depth, tt_move):
        if not moves:
            return moves
        scored = [
            (self._score_move_for_ordering(board, m, player, depth, tt_move), m)
            for m in moves
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored]

    def _quiescence(self, board, alpha, beta, player, mo, qdepth=0, max_qdepth=4):
        stand_pat = self.evaluate(board, player)
        if qdepth >= max_qdepth:
            return stand_pat
        if stand_pat >= beta:
            return beta
        alpha = max(alpha, stand_pat)

        moves = get_valid_moves(board, player)
        if mo:
            forced = [m for m in moves if m in mo]
            if forced:
                moves = forced

        if mo:
            capture_moves = moves
        else:
            capture_moves = [m for m in moves if _quick_ganh_count(board, m, player) > 0]

        for m in capture_moves:
            undo = make_move_inplace(board, m, player)
            score = -self._quiescence(
                board, -beta, -alpha, -player, undo['mo'], qdepth + 1, max_qdepth
            )
            unmake_move_inplace(board, undo, player)
            if score >= beta:
                return beta
            alpha = max(alpha, score)
        return alpha

    def _alphabeta(self, board, depth, alpha, beta, player, mo,
                   start_time, time_limit):
        if time.time() - start_time > time_limit:
            return None, None

        h = compute_hash(board)
        mo_sig = _mo_signature(mo)
        tt_score, tt_move, tt_cutoff = self._tt_lookup(h, mo_sig, depth, alpha, beta)

        moves = get_valid_moves(board, player)
        if mo:
            forced = [m for m in moves if m in mo]
            if forced:
                moves = forced

        if tt_cutoff:
            if tt_move is None or tt_move in moves:
                return tt_score, tt_move

        p1, pm1 = count_pieces_both(board)
        if p1 == 0:
            return (-9999 - depth) if player == 1 else (9999 + depth), None
        if pm1 == 0:
            return (9999 + depth) if player == 1 else (-9999 - depth), None
        if not moves:
            return -9999 - depth, None

        if depth == 0:
            if mo or any(_quick_ganh_count(board, m, player) > 0 for m in moves[:4]):
                return self._quiescence(board, alpha, beta, player, mo), None
            return self.evaluate(board, player), None

        ordered = self._order_moves(board, moves, player, depth, tt_move)

        best_score = -float('inf')
        best_move = None
        orig_alpha = alpha

        for m in ordered:
            undo = make_move_inplace(board, m, player)
            score, _ = self._alphabeta(
                board, depth - 1, -beta, -alpha,
                -player, undo['mo'], start_time, time_limit,
            )
            unmake_move_inplace(board, undo, player)

            if score is None:
                return None, None

            score = -score
            if score > best_score:
                best_score = score
                best_move = m
            alpha = max(alpha, score)

            if alpha >= beta:
                killers = self.killer_moves.setdefault(depth, [])
                if m not in killers:
                    killers.insert(0, m)
                self.killer_moves[depth] = killers[:2]
                self.history[m] = self.history.get(m, 0) + depth * depth
                break

        if best_score <= orig_alpha:
            flag = self.UPPER_BOUND
        elif best_score >= beta:
            flag = self.LOWER_BOUND
        else:
            flag = self.EXACT
        self._tt_store(h, mo_sig, depth, best_score, flag, best_move)
        return best_score, best_move

    def get_move(self, board, player, remain_time=99, mo=None):
        if mo is None:
            mo = []

        start_time = time.time()
        time_limit = min(self.time_cap, max(self.time_min, remain_time * self.time_frac))

        board_work = copy_board(board)

        valid_moves = get_valid_moves(board_work, player)
        if mo:
            forced = [m for m in valid_moves if m in mo]
            if forced:
                valid_moves = forced
        if not valid_moves:
            return None
        if len(valid_moves) == 1:
            return valid_moves[0]

        self.killer_moves = {}

        best_move = valid_moves[0]

        for m in valid_moves:
            if _quick_ganh_count(board_work, m, player) > 0:
                best_move = m
                break

        for depth in range(1, self.max_depth):
            elapsed = time.time() - start_time
            if elapsed >= time_limit * 0.85:
                break

            score, candidate = self._alphabeta(
                board_work, depth,
                -float('inf'), float('inf'),
                player, mo,
                start_time, time_limit * 0.88,
            )

            if score is None or candidate is None:
                break

            if mo and candidate not in valid_moves:
                continue
            best_move = candidate

            if abs(score) > 9000:
                break

        if mo and best_move not in valid_moves:
            return valid_moves[0]
        return best_move


_AGENT = AlphaBetaAgent()

def move(board, player, remain_time=99, mo=None):
    """
    Main function required by the assignment.
    Thin wrapper that delegates to a singleton AlphaBetaAgent.

    Input:
        board       : 5x5 matrix (1=us, -1=enemy, 0=empty)
        player      : 1 or -1
        remain_time : remaining time (seconds), default 99
        mo          : forced-move list from previous opponent turn

    Output:
        (start, end) - best move
    """
    return _AGENT.get_move(board, player, remain_time=remain_time, mo=mo)

def score_move_for_ordering(board, move, player, depth, tt_move):
    """Backwards-compatible shim (used by benchmark_rl_vs_nonrl.py)."""
    return _AGENT._score_move_for_ordering(board, move, player, depth, tt_move)


def main2(first='X'):
    board = init_board()
    count = 0
    limit = 100
    player = 1 if first == 'X' else -1
    print("Player play first" if player == 1 else "NPC play first")
    mo = []
    remain_time = {1: 99.0, -1: 99.0}
    match_start = time.time()
    player_total_move_time = 0.0
    player_moves = 0
    npc_moves = 0
    # print("Initial board state:")
    # print_board(board)
    # print("-" * 40)

    def finish_match(result):
        total_match_time = time.time() - match_start
        avg_player_move_time = (player_total_move_time / player_moves) if player_moves > 0 else 0.0
        print(f"Player average move time: {avg_player_move_time:.4f}s")
        print(f"Total match time: {total_match_time:.4f}s")
        print(f"Player moves: {player_moves}")
        print(f"NPC moves: {npc_moves}")
        return result

    while True:
        count += 1
        if count > limit:
            X_pieces = count_X(board)
            if X_pieces > 8:
                return finish_match(1)
            elif X_pieces < 8:
                print("Total game moves exceeded 100, and your piece count is < 8")
                return finish_match(-1)
            else:
                print("Total game moves exceeded 100, and your piece count is = 8")
                return finish_match(0)

        turn_start = time.time()
        if player == -1:
            chose_move = npc_move(board, player, mo)
        else:
            chose_move = move(board, player, remain_time=remain_time[player], mo=mo)   # use our AI with forced-mo context

        elapsed = time.time() - turn_start
        remain_time[player] = max(0.0, remain_time[player] - elapsed)
        if remain_time[player] <= 0:
            print(f"Player {'X' if player == 1 else 'O'} timed out. Remaining time: {remain_time[player]:.2f}s")
            return finish_match(-1 if player == 1 else 1)

        if player == 1 and elapsed > 3.2:
            print("Processing time exceeded 3.2 seconds")
            return finish_match(-1)

        if chose_move is None:
            if player == 1:
                print("No valid move was selected")
                return finish_match(-1)
            else:
                return finish_match(1)

        if player == 1 or player == -1:
            if mo and chose_move not in mo:
                print("Forced moves:", mo)
                print("Your selected move:", chose_move, "is invalid")
                return finish_match(-1)
            valid_moves = get_valid_moves(board, player)
            if chose_move not in valid_moves:
                print("Valid moves:", valid_moves)
                print("Your selected move:", chose_move, "is invalid")
                return finish_match(-1)

        current_player = player
        mo = act_moves(chose_move, current_player, board)

        if current_player == 1:
            player_total_move_time += elapsed
            player_moves += 1
        else:
            npc_moves += 1

        # print(
        #     f"Turn {count} | Player {'X' if current_player == 1 else 'O'} | "
        #     f"Move: {chose_move} | Decision time: {elapsed:.4f}s | "
        #     f"Remaining: {remain_time[current_player]:.2f}s"
        # )
        # print("Board state after move:")
        # print_board(board)
        # if mo:
        #     print(f"Forced moves for next player: {mo}")
        # print("-" * 40)

        player *= -1

    return finish_match(0)


def test():
    b = init_board()
    print_board(b)
    b[2][2] = 1
    print_board(b)
    mv = ((3, 3), (3, 2))
    ret = act_moves(mv, -1, b)
    b[3][1] = 1
    print_board(b)
    print(ret)
    mv = ((2, 2), (3, 3))
    ret = act_moves(mv, 1, b)
    print_board(b)
    print(ret)


# Run 10 test games and print results
if __name__ == '__main__':
    results = []
    NUM_GAMES = 100
    for i in range(NUM_GAMES):
        r = main2() if random.random() < 0.5 else main2(first='O')
        results.append(r)
        print(f"Game {i+1}: {'Win' if r == 1 else 'Lose' if r == -1 else 'Draw'}")
        print("=" * 50)
    wins = results.count(1)
    print(f"\nResult: {wins}/{NUM_GAMES} wins")
