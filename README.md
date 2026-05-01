# Cờ Gánh AI - AI Assignment 2

This repository contains an AI agent designed to play the traditional Vietnamese board game **Cờ Gánh**. The agent uses **Iterative Deepening Alpha-Beta Pruning** along with several advanced search enhancements to play efficiently and effectively.

## Repository Contents

* `main.py`: The core implementation of the Cờ Gánh AI. It contains the board representation, game rules (Make/Unmake moves), the heuristic evaluation function, and the Iterative Deepening Alpha-Beta search mechanism.
* `benchmark_rl_vs_nonrl.py`: A benchmarking script to evaluate and profile the performance of the AI agent, outputting vital statistics such as Nodes Per Second (NPS), average search depth, beta cutoff rate, and transposition table (cache) hit rate.

## AI Techniques Used

The AI in `main.py` is implemented using several advanced optimization techniques for Minimax:

- **Iterative Deepening Search (IDS):** Allows the agent to search progressively deeper until a given time limit is reached.
- **Alpha-Beta Pruning:** Standard optimization to prune unpromising branches.
- **Transposition Table & Zobrist Hashing:** Uses a rapid 64-bit state encoding to cache previously evaluated board states, completely avoiding redundant calculations.
- **Advanced Move Ordering:** Prioritizes moves that are most likely to be good (TT-move -> Ganh/Chet captures -> Killer moves -> History heuristic) to trigger Alpha-Beta cutoffs earlier.
- **Quiescence Search:** Mitigates the Horizon Effect by extending the search for unstable positions at the leaf nodes.
- **Phase-based Evaluation Function:** Tuned weights for Early, Mid, and Late game phases, taking into account:
    - Piece differences
    - Board control via positional weights
    - Piece mobility

## Usage

### Running the AI
You can import the module or run `main.py` directly to start the agent:
```bash
python main.py
```

### Running the Benchmark
To assess the performance and search metrics of the agent:
```bash
python benchmark_rl_vs_nonrl.py
```

## Requirements

* Python 3.x
* Standard Python libraries (`argparse`, `time`, `random`, `dataclasses`)
