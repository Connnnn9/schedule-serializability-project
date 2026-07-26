# Conflict Serializability Checker — Script Guide

`serializability_checker.py` is a standalone, dependency-light Python script that checks whether a transaction schedule is conflict serializable. Run it and it walks through the analysis in five steps: the parsed input schedule, a per-transaction table, the conflicting-pair precedence edges, the precedence graph, and the final verdict.

## Requirements

The core analysis needs only the Python standard library (Python 3.8+). The graph plot in Step 4 is optional and only appears if `matplotlib` and `networkx` are installed:

```
python3 -m pip install matplotlib networkx
```

Without them, Step 4 still prints a text-based version of the graph, so the script works out of the box either way.

## Running it

The simplest way is to run it with no arguments — it will prompt you for the schedule:

```
python3 serializability_checker.py
```

```
Enter a schedule (e.g. R1(A) W1(A) R2(A) W2(A) R1(B) W1(B) R2(B) W2(B)):
> W2(x), W1(x), R3(x), R1(x), W2(y), R3(y), R3(z), R2(x)
```

You can also pass the schedule directly on the command line, read it from a file, or skip the plotted graph window:

```
python3 serializability_checker.py "R1(A) W2(A) R2(B) W1(B)"
python3 serializability_checker.py --file schedule.txt
python3 serializability_checker.py --no-plot "R1(A) W2(A) R2(B) W1(B)"
```

The exit code is `0` if the schedule is serializable and `1` if it is not, so the script can be used in shell scripts or CI checks.

## Input format

A schedule is a sequence of operations separated by commas or whitespace. Each operation is written as `R<txn>(<item>)` for a read or `W<txn>(<item>)` for a write, e.g. `R1(A)` (transaction 1 reads item A) or `W2(B)` (transaction 2 writes item B). Commit/abort markers like `C1` or `A2` are recognized and ignored, since they don't participate in conflict analysis. Transaction numbers, item names, and read/write letters are case-insensitive.

## The five steps

**Step 1 — Input schedule.** The parsed sequence of operations, echoed back so you can confirm it was read correctly.

**Step 2 — Schedule table.** Each operation placed in the column of the transaction that issued it, in execution order — the same layout used in textbook examples.

**Step 3 — Conflicting pairs → precedence edges.** Two operations conflict if they belong to different transactions, touch the same data item, and at least one is a write. For every conflicting pair, an edge `Ti -> Tj` is listed, along with which two operations and which item produced it.

**Step 4 — Precedence graph.** A text rendering of the graph (one line per transaction pair, with the conflicting items combined), plus a plotted graph window if `matplotlib`/`networkx` are available. Edges that are part of a cycle are marked in the text output and drawn in red in the plot.

**Step 5 — Conclusion.** The schedule is conflict serializable if and only if the precedence graph has no cycle. If it's serializable, the script prints an equivalent serial order (from a topological sort of the graph). If not, it prints the cycle that proves it isn't.

## Using it as a library

`analyze_schedule(text, show_plot=True)` can be imported and called directly from other Python code; it prints the five steps and returns a dict with the parsed operations, the graph, the edge list, the cycle (if any), and the equivalent serial order (if serializable).
