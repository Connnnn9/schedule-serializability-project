#!/usr/bin/env python3
"""
serializability_checker.py

Interactive conflict-serializability checker for a transaction schedule.

Run it with no arguments and it will ASK YOU for the schedule, then print
the analysis as 5 steps:

    Step 1 - Input schedule            (parsed operations)
    Step 2 - Schedule table            (one column per transaction)
    Step 3 - Conflicting pairs         (-> precedence edges)
    Step 4 - Precedence graph          (text form always; a plotted window
                                         too, if matplotlib/networkx are
                                         installed)
    Step 5 - Conclusion                (serializable + order, or cycle)

Two operations conflict if they:
  1. belong to different transactions,
  2. access the same data item, and
  3. at least one of them is a write.

For each pair of conflicting operations op1 (from Ti) before op2 (from Tj),
an edge Ti -> Tj is added to the precedence graph. The schedule is conflict
serializable iff this graph is acyclic. If acyclic, any topological sort of
the graph gives an equivalent serial order.

Schedule input format
----------------------
A schedule is a sequence of operations, each written as:
    R1(A)   -> transaction 1 reads data item A
    W2(A)   -> transaction 2 writes data item A
    C1      -> transaction 1 commits (optional, ignored for conflict analysis)

Operations are given in the order they execute, separated by commas or
whitespace, e.g.:
    R1(A) W1(A) R2(A) W2(A) R1(B) W1(B)

Usage
-----
    python3 serializability_checker.py                      # asks for input
    python3 serializability_checker.py "R1(A) W1(B) R2(B) W2(A)"
    python3 serializability_checker.py --file schedule.txt
    python3 serializability_checker.py --no-plot "..."       # skip the plot window
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple


class Operation:
    """A single read/write operation in a schedule."""

    __slots__ = ("op_type", "txn", "item", "index")

    def __init__(self, op_type: str, txn: int, item: str, index: int):
        self.op_type = op_type  # 'R' or 'W'
        self.txn = txn
        self.item = item
        self.index = index  # position in the schedule (0-based)

    def __repr__(self) -> str:
        return f"{self.op_type}{self.txn}({self.item})"


class ScheduleParseError(ValueError):
    pass


# Matches R1(A), W2(B), r1(a), etc. Commit/abort tokens (C1, A1) are matched
# separately so they can be recognized and skipped without error.
_OP_PATTERN = re.compile(r"^([RWrw])\s*(\d+)\s*\(\s*([A-Za-z0-9_]+)\s*\)$")
_TXN_ONLY_PATTERN = re.compile(r"^([A-Za-z]+)\s*(\d+)$")


def parse_schedule(text: str) -> List[Operation]:
    """Parse a schedule string into a list of Operation objects.

    Accepts operations separated by whitespace and/or commas. Commit/abort
    tokens like C1 or A2 are recognized and silently skipped since they do
    not participate in conflict analysis.
    """
    tokens = [t for t in re.split(r"[,\s]+", text.strip()) if t]
    if not tokens:
        raise ScheduleParseError("No operations found in schedule.")

    operations: List[Operation] = []
    for token in tokens:
        m = _OP_PATTERN.match(token)
        if m:
            op_type, txn, item = m.group(1).upper(), int(m.group(2)), m.group(3).upper()
            operations.append(Operation(op_type, txn, item, len(operations)))
            continue

        m2 = _TXN_ONLY_PATTERN.match(token)
        if m2 and m2.group(1).upper() in ("C", "COMMIT", "A", "ABORT"):
            # Commit/abort marker; not a conflict-relevant operation.
            continue

        raise ScheduleParseError(
            f"Could not parse operation '{token}' (expected form like R1(A) or W2(B))."
        )

    if not operations:
        raise ScheduleParseError("No read/write operations found in schedule.")

    return operations


EdgeReason = Tuple[int, int, str, Operation, Operation]


def build_precedence_graph(
    operations: List[Operation],
) -> Tuple[Dict[int, Set[int]], List[EdgeReason], Dict[Tuple[int, int], Set[str]]]:
    """Build the precedence graph from a list of operations.

    Returns:
        graph: adjacency dict mapping transaction id -> set of transaction ids
               it must precede (an edge Ti -> Tj means Ti must run before Tj).
        edge_reasons: ordered list of (Ti, Tj, item, op_i, op_j) - one row per
                      distinct conflicting (Ti, Tj, item) triple. This is the
                      "list down the conflicts" step.
        pair_items: dict mapping (Ti, Tj) -> set of items that produced that
                    edge, used to draw one combined arrow per pair.
    """
    by_item: Dict[str, List[Operation]] = defaultdict(list)
    for op in operations:
        by_item[op.item].append(op)

    txns: Set[int] = {op.txn for op in operations}
    graph: Dict[int, Set[int]] = {t: set() for t in txns}
    edge_reasons: List[EdgeReason] = []
    seen_triples: Set[Tuple[int, int, str]] = set()
    pair_items: Dict[Tuple[int, int], Set[str]] = defaultdict(set)

    for item, ops in by_item.items():
        ops_sorted = sorted(ops, key=lambda o: o.index)
        for i in range(len(ops_sorted)):
            for j in range(i + 1, len(ops_sorted)):
                op1, op2 = ops_sorted[i], ops_sorted[j]
                if op1.txn == op2.txn:
                    continue
                if op1.op_type == "R" and op2.op_type == "R":
                    continue  # read-read is not a conflict

                triple = (op1.txn, op2.txn, item)
                if triple in seen_triples:
                    continue
                seen_triples.add(triple)
                edge_reasons.append((op1.txn, op2.txn, item, op1, op2))

                graph[op1.txn].add(op2.txn)
                pair_items[(op1.txn, op2.txn)].add(item)

    return graph, edge_reasons, pair_items


def find_cycle(graph: Dict[int, Set[int]]) -> Optional[List[int]]:
    """Return a cycle (list of txn ids) if one exists in the graph, else None.

    Uses iterative DFS with a recursion-stack coloring scheme:
      0 = unvisited, 1 = on current DFS path, 2 = fully processed.
    """
    color: Dict[int, int] = {node: 0 for node in graph}
    parent: Dict[int, int] = {}

    for start in graph:
        if color[start] != 0:
            continue
        stack = [(start, iter(sorted(graph[start])))]
        color[start] = 1
        while stack:
            node, neighbors = stack[-1]
            advanced = False
            for nxt in neighbors:
                if color[nxt] == 0:
                    color[nxt] = 1
                    parent[nxt] = node
                    stack.append((nxt, iter(sorted(graph[nxt]))))
                    advanced = True
                    break
                elif color[nxt] == 1:
                    # Found a back edge -> reconstruct the cycle.
                    cycle = [nxt, node]
                    cur = node
                    while cur != nxt:
                        cur = parent[cur]
                        cycle.append(cur)
                    cycle.reverse()
                    return cycle
            if not advanced:
                color[node] = 2
                stack.pop()

    return None


def topological_sort(graph: Dict[int, Set[int]]) -> List[int]:
    """Return a topological ordering of transactions (assumes acyclic graph)."""
    in_degree = {node: 0 for node in graph}
    for node in graph:
        for nbr in graph[node]:
            in_degree[nbr] += 1

    ready = sorted([n for n, d in in_degree.items() if d == 0])
    order: List[int] = []

    while ready:
        ready.sort()
        node = ready.pop(0)
        order.append(node)
        for nbr in sorted(graph[node]):
            in_degree[nbr] -= 1
            if in_degree[nbr] == 0:
                ready.append(nbr)

    return order


# --------------------------------------------------------------------------
# Step-by-step printing
# --------------------------------------------------------------------------

def _print_step1(operations: List[Operation]) -> None:
    print("Step 1 - Input schedule")
    print("  S = " + " ".join(repr(op) for op in operations))
    print()


def _print_step2(operations: List[Operation], txns: List[int]) -> None:
    print("Step 2 - Schedule table")
    headers = [f"T{t}" for t in txns]
    col_width = max(6, max((len(repr(op)) for op in operations), default=6) + 2)
    header_row = "".join(h.center(col_width) for h in headers)
    print("  " + header_row)
    print("  " + "-" * len(header_row))
    for op in operations:
        row = "".join(
            (repr(op) if op.txn == t else "").center(col_width) for t in txns
        )
        print("  " + row)
    print()


def _print_step3(edge_reasons: List[EdgeReason]) -> None:
    print("Step 3 - Conflicting pairs -> precedence edges")
    if edge_reasons:
        for t1, t2, item, op1, op2 in edge_reasons:
            print(f"  T{t1} -> T{t2}   ({item}: {op1} before {op2})")
    else:
        print("  (no conflicts; graph has no edges)")
    print()


def _print_step4_text(pair_items: Dict[Tuple[int, int], Set[str]], cycle_pairs: Set[Tuple[int, int]]) -> None:
    print("Step 4 - Precedence (serialization) graph")
    if not pair_items:
        print("  (no edges)")
    for (t1, t2), items in sorted(pair_items.items()):
        marker = "  *** part of cycle ***" if (t1, t2) in cycle_pairs else ""
        label = ", ".join(sorted(items))
        print(f"  T{t1} --[{label}]--> T{t2}{marker}")


def _try_plot_graph(
    txns: List[int],
    pair_items: Dict[Tuple[int, int], Set[str]],
    cycle_pairs: Set[Tuple[int, int]],
    show_plot: bool,
) -> bool:
    """Attempt to draw the graph with networkx + matplotlib. Returns True if
    a plot was shown, False if the libraries aren't available (in which case
    the caller should fall back to the text rendering)."""
    if not show_plot:
        return False
    try:
        import networkx as nx
        import matplotlib.pyplot as plt
    except ImportError:
        return False

    G = nx.DiGraph()
    G.add_nodes_from(txns)
    for (t1, t2), items in pair_items.items():
        G.add_edge(t1, t2, items=items)

    pos = nx.circular_layout(G)
    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    edge_colors = ["#d64550" if (u, v) in cycle_pairs else "#6b2d91" for u, v in G.edges()]
    edge_widths = [3 if (u, v) in cycle_pairs else 1.5 for u, v in G.edges()]

    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=600, node_color="#6b2d91")
    nx.draw_networkx_labels(G, pos, ax=ax, labels={t: f"T{t}" for t in G.nodes()}, font_color="white", font_size=9)
    nx.draw_networkx_edges(
        G, pos, ax=ax, edge_color=edge_colors, width=edge_widths,
        arrowsize=12, connectionstyle="arc3,rad=0.15", min_source_margin=12, min_target_margin=12,
    )
    edge_labels = {(u, v): ", ".join(sorted(d["items"])) for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, ax=ax, edge_labels=edge_labels, font_size=8)

    # Curved edges (connectionstyle="arc3") only render correctly under an
    # equal aspect ratio; without this, matplotlib's autoscale can badly
    # under-estimate the plot bounds and squash the whole graph into a
    # corner of the figure.
    ax.margins(0.3)
    ax.set_aspect("equal", adjustable="datalim")
    ax.set_title("Precedence (serialization) graph", fontsize=11)
    ax.axis("off")
    fig.tight_layout()
    plt.show()
    return True


def _print_step5(cycle: Optional[List[int]], graph: Dict[int, Set[int]]) -> None:
    print("Step 5 - Conclusion")
    if cycle is None:
        order = topological_sort(graph)
        print("  Result: CONFLICT SERIALIZABLE")
        print("  The precedence graph has no cycle.")
        print("  Equivalent serial order: " + " -> ".join(f"T{t}" for t in order))
    else:
        cycle_str = " -> ".join(f"T{t}" for t in cycle)
        print("  Result: NOT CONFLICT SERIALIZABLE")
        print(f"  The precedence graph has a cycle: {cycle_str}")


def analyze_schedule(text: str, show_plot: bool = True) -> Dict[str, object]:
    """Parse the schedule and print the full 5-step analysis.

    Returns a dict with keys: operations, graph, edge_reasons, pair_items,
    cycle, serializable, order.
    """
    operations = parse_schedule(text)
    txns = sorted({op.txn for op in operations})
    graph, edge_reasons, pair_items = build_precedence_graph(operations)
    cycle = find_cycle(graph)
    cycle_pairs: Set[Tuple[int, int]] = set()
    if cycle:
        cycle_pairs = {(cycle[i], cycle[i + 1]) for i in range(len(cycle) - 1)}

    _print_step1(operations)
    _print_step2(operations, txns)
    _print_step3(edge_reasons)

    plotted = _try_plot_graph(txns, pair_items, cycle_pairs, show_plot)
    _print_step4_text(pair_items, cycle_pairs)
    if not plotted and show_plot:
        print("  (install matplotlib + networkx to also see a plotted graph window: "
              "pip install matplotlib networkx)")
    print()

    _print_step5(cycle, graph)

    order = None if cycle else topological_sort(graph)
    return {
        "operations": operations,
        "graph": graph,
        "edge_reasons": edge_reasons,
        "pair_items": pair_items,
        "cycle": cycle,
        "serializable": cycle is None,
        "order": order,
    }


def _read_input_text(args: argparse.Namespace) -> str:
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            return f.read()
    if args.schedule:
        return " ".join(args.schedule)
    if not sys.stdin.isatty():
        data = sys.stdin.read().strip()
        if data:
            return data
    # Interactive prompt - this is the default when run with no arguments.
    print("Enter a schedule (e.g. R1(A) W1(A) R2(A) W2(A) R1(B) W1(B) R2(B) W2(B)):")
    return input("> ")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check whether a transaction schedule is conflict serializable "
                     "(prompts for the schedule if none is given)."
    )
    parser.add_argument(
        "schedule",
        nargs="*",
        help="Schedule as a sequence of ops, e.g. R1(A) W1(B) R2(B) W2(A). "
             "Quote it as one argument or pass multiple tokens. "
             "If omitted, you will be prompted to type it in.",
    )
    parser.add_argument("--file", "-f", help="Read the schedule from a text file.")
    parser.add_argument(
        "--no-plot", action="store_true",
        help="Skip opening a matplotlib graph window; only print the text-based graph.",
    )
    args = parser.parse_args(argv)

    text = _read_input_text(args)

    try:
        result = analyze_schedule(text, show_plot=not args.no_plot)
    except ScheduleParseError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    return 0 if result["serializable"] else 1


if __name__ == "__main__":
    sys.exit(main())
