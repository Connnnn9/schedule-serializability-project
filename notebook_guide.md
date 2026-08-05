# Conflict Serializability Checker — Notebook Guide

`serializability_checker.ipynb` is a Jupyter notebook version of the conflict serializability checker. It builds a precedence (serialization) graph for a transaction schedule and checks it for cycles, with the graph drawn inline using `networkx` and `matplotlib`.

## Requirements

```
python3 -m pip install networkx pandas matplotlib ipywidgets jupyter ipykernel
```

Then open the notebook in VS Code (Python + Jupyter extensions), JupyterLab, classic Jupyter, or Google Colab.

If you're running it in VS Code: make sure the packages above are installed into the *same* Python interpreter the notebook's kernel is using. Run `import sys; print(sys.executable)` in a cell to check which interpreter that is, then install into that exact path if `pip install` alone doesn't match it.

## Structure

The notebook has five sections, meant to be run top to bottom:

1. **Setup** — imports the libraries used throughout (`networkx`, `matplotlib`, `pandas`, `re`). Run once per session.
2. **Core logic** — `Operation` and `parse_schedule` (turns a schedule string into a list of operations), `build_precedence_graph` (**assignment Step 1**: builds the directed conflict graph), and `find_cycle` / `equivalent_serial_order` (**assignment Step 2**: cycle detection via DFS, plus a topological sort for the equivalent serial order when there's no cycle).
3. **`analyze_schedule(schedule_text, figsize=(3.5, 3.5))`** — a single function that runs all five analysis steps (parsed input, schedule table, conflict edges, the drawn graph with the cycle highlighted in red — **assignment Step 3** — and the verdict) and prints/plots them together as one combined output.
4. **Usage** — a pre-filled call to `analyze_schedule(...)` with the in-class example, so you can see it working immediately.
5. **Load a schedule from a file** — a `FileUpload` widget (needs `ipywidgets`). Click **Choose file**, pick a `.txt` schedule file, click **Analyze uploaded file**. There's also a **Clear** button to reset the picker without analyzing. This is the notebook's file-input path, satisfying the "accept input from a file" requirement.

## Running it

After running the Setup and Core logic cells, call the function with any schedule string:

```python
analyze_schedule("R1(A), W2(A), R2(B), W1(B)")
```

This prints, in order:

1. the parsed input schedule
2. a table with one column per transaction, operations placed in execution order
3. the list of conflicting-pair precedence edges (`Ti -> Tj`, with the item and the two operations that caused it)
4. the precedence graph, plotted inline (cycle edges shown in red)
5. the conclusion — either "conflict serializable" with an equivalent serial order, or "not conflict serializable" with the cycle

To analyze a schedule from a file instead of typing a string, scroll to **Load a schedule from a file**, run that cell, click **Choose file**, select a `.txt` file, then click **Analyze uploaded file** — it runs the same five-step analysis on the uploaded content.


## Input format

Operations are written as `R<txn>(<item>)` or `W<txn>(<item>)`, separated by commas or whitespace, e.g. `R1(A), W1(A), R2(A), W2(A)`. Commit/abort markers (`C1`, `A2`, ...) are recognized and ignored. The same format applies whether you type the string directly or upload it in a `.txt` file.

## Adjusting the plot size

`analyze_schedule` takes a `figsize` argument if the default 3.5×3.5 inch graph is too big or too small for your screen:

```python
analyze_schedule("R1(A), W2(A), R2(B), W1(B)", figsize=(2.5, 2.5))
```

The plot uses an equal aspect ratio internally so curved edges between transactions render correctly at any size.
