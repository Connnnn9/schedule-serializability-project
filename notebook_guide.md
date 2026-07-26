# Conflict Serializability Checker — Notebook Guide

`serializability_checker.ipynb` is a Jupyter notebook version of the conflict serializability checker. It builds a precedence (serialization) graph for a transaction schedule and checks it for cycles, with the graph drawn inline using `networkx` and `matplotlib`.

## Requirements

```
python3 -m pip install nbformat networkx pandas matplotlib jupyter
```

Then open the notebook with `jupyter notebook serializability_checker.ipynb` (or open it in JupyterLab, VS Code, google colab, or any notebook-compatible editor).

## Structure

The notebook has three parts:

1. **Setup and core logic** — imports, the `Operation` class, `parse_schedule`, `build_precedence_graph`, `find_cycle`, and `equivalent_serial_order`. Run these cells once per session.
2. **`analyze_schedule(schedule_text, figsize=(3.5, 3.5))`** — a single function that runs all five analysis steps and prints/plots them together as one combined output.
3. **Usage cells** — pre-filled calls to `analyze_schedule(...)` with the slide example plus a serializable and a non-serializable example, so you can see it working immediately.

## Running it

After running the setup cells, call the function with any schedule string:

```python
analyze_schedule("R1(A), W2(A), R2(B), W1(B)")
```

This prints, in order:

1. the parsed input schedule
2. a table with one column per transaction, operations placed in execution order
3. the list of conflicting-pair precedence edges (`Ti -> Tj`, with the item and the two operations that caused it)
4. the precedence graph, plotted inline (cycle edges shown in red)
5. the conclusion — either "conflict serializable" with an equivalent serial order, or "not conflict serializable" with the cycle

## Input format

Operations are written as `R<txn>(<item>)` or `W<txn>(<item>)`, separated by commas or whitespace, e.g. `R1(A), W1(A), R2(A), W2(A)`. Commit/abort markers (`C1`, `A2`, ...) are recognized and ignored.

## Adjusting the plot size

`analyze_schedule` takes a `figsize` argument if the default 3.5×3.5 inch graph is too big or too small for your screen:

```python
analyze_schedule("R1(A), W2(A), R2(B), W1(B)", figsize=(2.5, 2.5))
```

The plot uses an equal aspect ratio internally so curved edges between transactions render correctly at any size.
