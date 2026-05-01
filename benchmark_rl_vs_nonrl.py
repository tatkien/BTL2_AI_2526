import argparse
import random
import time
from dataclasses import dataclass

import main as base


@dataclass
class SearchStats:
    move_count: int = 0
    depth_sum: int = 0
    search_seconds: float = 0.0
    nodes: int = 0
    q_nodes: int = 0
    tt_probes: int = 0
    tt_hits: int = 0
    generated_branches: int = 0
    pruned_branches: int = 0

    def merge(self, other):
        self.move_count += other.move_count
        self.depth_sum += other.depth_sum
        self.search_seconds += other.search_seconds
        self.nodes += other.nodes
        self.q_nodes += other.q_nodes
        self.tt_probes += other.tt_probes
        self.tt_hits += other.tt_hits
        self.generated_branches += other.generated_branches
        self.pruned_branches += other.pruned_branches

    def metrics(self):
        total_nodes = self.nodes + self.q_nodes
        avg_depth = (self.depth_sum / self.move_count) if self.move_count else 0.0
        nps = (total_nodes / self.search_seconds) if self.search_seconds > 1e-9 else 0.0
        beta_cutoff_rate = (
            self.pruned_branches / self.generated_branches if self.generated_branches else 0.0
        )
        cache_hit_rate = self.tt_hits / self.tt_probes if self.tt_probes else 0.0
        return {
            "avg_depth": avg_depth,
            "nps": nps,
            "beta_cutoff_rate": beta_cutoff_rate,
            "cache_hit_rate": cache_hit_rate,
            "moves": self.move_count,
            "nodes": self.nodes,
            "q_nodes": self.q_nodes,
            "total_nodes": total_nodes,
            "search_seconds": self.search_seconds,
        }


class Engine:
    def __init__(self, evaluator, name):
        self.evaluator = evaluator
        self.name = name
        self.tt = {}
        self.tt_max = 600_000
        self.killer_moves = {}
        self.history = {}
        self.stats = SearchStats()
        self.exact = 0
        self.lower_bound = 1
        self.upper_bound = 2

    @staticmethod
    def _mo_signature(mo):
        if not mo:
            return ()
        return tuple(sorted(mo))

    def tt_lookup(self, h, mo_sig, depth, alpha, beta):
        self.stats.tt_probes += 1
        key = (h, mo_sig)
        if key not in self.tt:
            return None, None, False

        self.stats.tt_hits += 1
        entry = self.tt[key]
        best_move = entry.get("best_move")
        if entry["depth"] < depth:
            return None, best_move, False
        flag = entry["flag"]
        score = entry["score"]
        if flag == self.exact:
            return score, best_move, True
        if flag == self.lower_bound:
            alpha = max(alpha, score)
        elif flag == self.upper_bound:
            beta = min(beta, score)
        if alpha >= beta:
            return score, best_move, True
        return None, best_move, False

    def tt_store(self, h, mo_sig, depth, score, flag, best_move):
        if len(self.tt) >= self.tt_max:
            self.tt.clear()
        self.tt[(h, mo_sig)] = {
            "depth": depth,
            "score": score,
            "flag": flag,
            "best_move": best_move,
        }

    def order_moves(self, board, moves, player, depth, tt_move):
        if not moves:
            return moves
        scored = [
            (base.score_move_for_ordering(board, m, player, depth, tt_move), m)
            for m in moves
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored]

    def quiescence(self, board, alpha, beta, player, mo, qdepth=0, max_qdepth=4):
        self.stats.q_nodes += 1
        stand_pat = self.evaluator(board, player)

        if qdepth >= max_qdepth:
            return stand_pat
        if stand_pat >= beta:
            return beta
        alpha = max(alpha, stand_pat)

        moves = base.get_valid_moves(board, player)
        if mo:
            forced = [m for m in moves if m in mo]
            if forced:
                moves = forced

        if mo:
            capture_moves = moves
        else:
            capture_moves = [m for m in moves if base._quick_ganh_count(board, m, player) > 0]

        for m in capture_moves:
            undo = base.make_move_inplace(board, m, player)
            score = -self.quiescence(
                board, -beta, -alpha, -player, undo["mo"], qdepth + 1, max_qdepth
            )
            base.unmake_move_inplace(board, undo, player)

            if score >= beta:
                return beta
            alpha = max(alpha, score)

        return alpha

    def alphabeta(self, board, depth, alpha, beta, player, mo, start_time, time_limit):
        self.stats.nodes += 1
        if time.time() - start_time > time_limit:
            return None, None

        h = base.compute_hash(board)
        mo_sig = self._mo_signature(mo)
        tt_score, tt_move, tt_cutoff = self.tt_lookup(h, mo_sig, depth, alpha, beta)

        moves = base.get_valid_moves(board, player)
        if mo:
            forced = [m for m in moves if m in mo]
            if forced:
                moves = forced

        if tt_cutoff:
            if tt_move is None or tt_move in moves:
                return tt_score, tt_move

        p1, pm1 = base.count_pieces_both(board)
        if p1 == 0:
            return (-9999 - depth) if player == 1 else (9999 + depth), None
        if pm1 == 0:
            return (9999 + depth) if player == 1 else (-9999 - depth), None
        if not moves:
            return -9999 - depth, None

        if depth == 0:
            if mo or any(base._quick_ganh_count(board, m, player) > 0 for m in moves[:4]):
                return self.quiescence(board, alpha, beta, player, mo), None
            return self.evaluator(board, player), None

        ordered = self.order_moves(board, moves, player, depth, tt_move)
        self.stats.generated_branches += len(ordered)

        best_score = -float("inf")
        best_move = None
        orig_alpha = alpha

        for idx, m in enumerate(ordered):
            undo = base.make_move_inplace(board, m, player)
            score, _ = self.alphabeta(
                board, depth - 1, -beta, -alpha, -player, undo["mo"], start_time, time_limit
            )
            base.unmake_move_inplace(board, undo, player)

            if score is None:
                return None, None

            score = -score
            if score > best_score:
                best_score = score
                best_move = m
            alpha = max(alpha, score)

            if alpha >= beta:
                remaining = len(ordered) - idx - 1
                if remaining > 0:
                    self.stats.pruned_branches += remaining
                killers = self.killer_moves.setdefault(depth, [])
                if m not in killers:
                    killers.insert(0, m)
                self.killer_moves[depth] = killers[:2]
                self.history[m] = self.history.get(m, 0) + depth * depth
                break

        if best_score <= orig_alpha:
            flag = self.upper_bound
        elif best_score >= beta:
            flag = self.lower_bound
        else:
            flag = self.exact
        self.tt_store(h, mo_sig, depth, best_score, flag, best_move)
        return best_score, best_move

    def move(self, board, player, remain_time=99.0, mo=None):
        if mo is None:
            mo = []

        start_time = time.time()
        time_limit = min(2.95, max(0.3, remain_time * 0.08))
        board_work = base.copy_board(board)

        valid_moves = base.get_valid_moves(board_work, player)
        if mo:
            forced = [m for m in valid_moves if m in mo]
            if forced:
                valid_moves = forced
        if not valid_moves:
            return None, 0
        if len(valid_moves) == 1:
            return valid_moves[0], 0

        self.killer_moves = {}
        best_move = valid_moves[0]
        best_depth = 0

        for m in valid_moves:
            if base._quick_ganh_count(board_work, m, player) > 0:
                best_move = m
                break

        for depth in range(1, 12):
            elapsed = time.time() - start_time
            if elapsed >= time_limit * 0.85:
                break

            score, candidate = self.alphabeta(
                board_work,
                depth,
                -float("inf"),
                float("inf"),
                player,
                mo,
                start_time,
                time_limit * 0.88,
            )
            if score is None or candidate is None:
                break
            if mo and candidate not in valid_moves:
                continue
            best_move = candidate
            best_depth = depth
            if abs(score) > 9000:
                break

        if mo and best_move not in valid_moves:
            return valid_moves[0], best_depth
        return best_move, best_depth

POSITION_BONUS = [
    [ 0, 10, 20, 10,  0],
    [10, 30, 10, 30, 10],
    [20, 10, 50, 10, 20],
    [10, 30, 10, 30, 10],
    [ 0, 10, 20, 10,  0]
]

def evaluate_non_rl(board, player):
    p1, pm1 = base.count_pieces_both(board)
    if p1 == 0:
        return -9999 if player == 1 else 9999
    if pm1 == 0:
        return 9999 if player == 1 else -9999

    score_piece = (p1 - pm1) * 1000 if player == 1 else (pm1 - p1) * 1000
    
    score_pos = 0
    for i in range(5):
        for j in range(5):
            if board[i][j] == player:
                score_pos += POSITION_BONUS[i][j]
            elif board[i][j] == player * -1:
                score_pos -= POSITION_BONUS[i][j]
                
    score_mob = (len(base.get_valid_moves(board, player)) - len(base.get_valid_moves(board, player * -1))) * 5
    return score_piece + score_pos + score_mob

def finish_limit(board):
    x_pieces = base.count_X(board)
    if x_pieces > 8:
        return 1
    if x_pieces < 8:
        return -1
    return 0


def play_one_game(rl_engine, non_rl_engine, first_player=1, move_limit=100):
    board = base.init_board()
    player = first_player
    mo = []
    remain_time = {1: 99.0, -1: 99.0}
    count = 0
    game_depth_sum = {1: 0, -1: 0}
    game_move_count = {1: 0, -1: 0}

    def finalize(outcome):
        rl_avg_depth = game_depth_sum[1] / game_move_count[1] if game_move_count[1] else 0.0
        non_rl_avg_depth = game_depth_sum[-1] / game_move_count[-1] if game_move_count[-1] else 0.0
        return outcome, rl_avg_depth, non_rl_avg_depth

    while True:
        count += 1
        if count > move_limit:
            return finalize(finish_limit(board))

        turn_start = time.time()
        if player == 1:
            chosen, depth = rl_engine.move(board, player, remain_time[player], mo)
            elapsed = time.time() - turn_start
            rl_engine.stats.move_count += 1
            rl_engine.stats.depth_sum += depth
            rl_engine.stats.search_seconds += elapsed
            game_move_count[1] += 1
            game_depth_sum[1] += depth
        else:
            chosen, depth = non_rl_engine.move(board, player, remain_time[player], mo)
            elapsed = time.time() - turn_start
            non_rl_engine.stats.move_count += 1
            non_rl_engine.stats.depth_sum += depth
            non_rl_engine.stats.search_seconds += elapsed
            game_move_count[-1] += 1
            game_depth_sum[-1] += depth

        remain_time[player] = max(0.0, remain_time[player] - elapsed)
        if remain_time[player] <= 0:
            return finalize(-1 if player == 1 else 1)
        if elapsed > 3.2:
            return finalize(-1 if player == 1 else 1)
        if chosen is None:
            return finalize(-1 if player == 1 else 1)

        if mo and chosen not in mo:
            return finalize(-1 if player == 1 else 1)
        valid_moves = base.get_valid_moves(board, player)
        if chosen not in valid_moves:
            return finalize(-1 if player == 1 else 1)

        current_player = player
        mo = base.act_moves(chosen, current_player, board)
        player *= -1


def print_metrics(label, stats):
    m = stats.metrics()
    print(f"{label}:")
    print(f"  Moves: {m['moves']}")
    print(f"  Average Search Depth: {m['avg_depth']:.3f}")
    print(f"  NPS: {m['nps']:.2f}")
    print(f"  Beta-Cutoff Rate: {m['beta_cutoff_rate'] * 100:.2f}%")
    print(f"  Cache Hit Rate: {m['cache_hit_rate'] * 100:.2f}%")
    print(f"  Total Nodes: {m['total_nodes']} (AB={m['nodes']}, Q={m['q_nodes']})")
    print(f"  Search Time: {m['search_seconds']:.3f}s")


def run_benchmark(games=100, seed=42):
    random.seed(seed)
    rl_engine = Engine(base.evaluate, "RL")
    non_rl_engine = Engine(evaluate_non_rl, "Non-RL")
    results = []

    start = time.time()
    for i in range(games):
        first = 1 if i % 2 == 0 else -1
        result, rl_game_depth, non_rl_game_depth = play_one_game(
            rl_engine, non_rl_engine, first_player=first
        )
        results.append(result)
        print(
            f"Game {i + 1}/{games}: "
            f"{'RL win' if result == 1 else 'RL lose' if result == -1 else 'Draw'} | "
            f"Depth RL={rl_game_depth:.2f}, Non-RL={non_rl_game_depth:.2f}"
        )
    elapsed = time.time() - start

    wins = results.count(1)
    losses = results.count(-1)
    draws = results.count(0)

    print("\n=== Benchmark Summary ===")
    print(f"Games: {games}")
    print(f"RL Wins/Losses/Draws: {wins}/{losses}/{draws}")
    print(f"Total Wall Time: {elapsed:.2f}s")
    print("")
    print_metrics("RL Engine", rl_engine.stats)
    print("")
    print_metrics("Non-RL Engine", non_rl_engine.stats)


def main():
    parser = argparse.ArgumentParser(
        description="100-game benchmark: RL alpha-beta vs non-RL alpha-beta with search metrics."
    )
    parser.add_argument("--games", type=int, default=100, help="Number of games to run (default: 100)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()
    run_benchmark(games=args.games, seed=args.seed)


if __name__ == "__main__":
    main()
