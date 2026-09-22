import json
import time
import streamlit as st
from utils import *
from logic_ import *
from sudoku_solver import (
    atom,
    build_definite_kb,
    build_general_kb,
    solve_full_grid_fc,
    solve_full_grid_bc,
    pl_bc_entails,
)

def describe_atom(symbol):
    text = str(symbol)

    if text.startswith("Not"):
        r, c, v = text[3:].split("_")
        return f"Row {r}, column {c} cannot contain {v}"

    if text.startswith("Is"):
        r, c, v = text[2:].split("_")
        return f"Row {r}, column {c} contains {v}"

    return text

def explain_rule(conclusion, premises, n):
    text = str(conclusion)

    if text.startswith("Is"):
        r, c, v = map(int, text[2:].split("_"))

        # Check whether every other value has been ruled out
        other_values = [
            value for value in range(1, n + 1)
            if value != v
        ]

        expected = {
            f"Not{r}_{c}_{value}"
            for value in other_values
        }

        actual = {str(premise) for premise in premises}

        if actual == expected:
            excluded = ", ".join(map(str, other_values))

            return (
                f"Last remaining candidate: "
                f"values {excluded} have all been ruled out "
                f"for row {r}, column {c}. "
                f"Since each cell must contain one value from 1 to {n}, "
                f"this cell must contain {v}."
            )

    return f"These premises imply: {describe_atom(conclusion)}."


def render_board(board, givens, box_h, box_w, focus=None):
    html = '<table class="sudoku-board">'

    for r, row in enumerate(board, start=1):
        html += "<tr>"

        for c, value in enumerate(row, start=1):
            classes = []

            if f"{r}_{c}" in givens:
                classes.append("given")

            if c % box_w == 0:
                classes.append("box-right")

            if r % box_h == 0:
                classes.append("box-bottom")

            if (r, c) == focus:
                classes.append("focus")

            class_names = " ".join(classes)
            text = str(int(value)) if value != "" else ""

            html += (
                f'<td class="{class_names}">'
                f'<div class="cell">{text}</div>'
                '</td>'
            )

        html += "</tr>"

    html += "</table>"
    st.html(html)
# Grid CSS 
st.html("""
<style>
.sudoku-board {
    border-collapse: collapse;
    table-layout: fixed;
    width: 100%;
    max-width: 480px;
    border: 3px solid #475569;
    margin: 16px 0;
}

.sudoku-board td {
    padding: 0;
    border: 1px solid #cbd5e1;
    background: #ffffff;
    color: #0369a1;
}

.sudoku-board .cell {
    aspect-ratio: 1;
    display: grid;
    place-items: center;
    font-size: 22px;
}

.sudoku-board .given {
    background: #e2e8f0;
    color: #0f172a;
    font-weight: bold;
}

.sudoku-board .focus {
    background: #fef3c7;
    outline: 3px solid #d97706;
    outline-offset: -3px;
}

.sudoku-board .box-right {
    border-right: 3px solid #475569;
}

.sudoku-board .box-bottom {
    border-bottom: 3px solid #475569;
}
</style>
""")

st.title('Sudoku Solver')

with open('puzzles.json') as f:
    pool = json.load(f)

# --- 1. Puzzle selection & visual board display ---
# TODO: a dropdown/selectbox to pick a puzzle by index from pool['puzzles'].
# TODO: render the grid (e.g. a table or grid of st.columns), showing given
# cells and empty cells differently (e.g. bold givens, blank otherwise).

# Get the list of puzzles
puzzles = pool["puzzles"]

# Let the user select a puzzle
puzzle_index = st.selectbox(
    "Select a puzzle",
    options=range(len(puzzles)),
    format_func=lambda i: f"Puzzle {i + 1}",
)

# Get the selected puzzle and its initial clues
selected_puzzle = puzzles[puzzle_index]
givens = selected_puzzle["givens"]

if st.session_state.get("active_puzzle") != puzzle_index:
    st.session_state["active_puzzle"] = puzzle_index
    st.session_state.pop("solve_result", None)
    st.session_state.pop("query_result", None)
    st.session_state.pop("replay_step", None)

st.write(f"Given cells: {len(givens)}")


# Build the puzzle board
n = pool["n"]

board = []

for r in range(1, n + 1):
    row = []

    for c in range(1, n + 1):
        key = f"{r}_{c}"
        value = str(givens.get(key, ""))
        row.append(value)

    board.append(row)

render_board(
    board,
    givens,
    pool["box_h"],
    pool["box_w"],
)

# --- 2. Full-grid auto-solver, with algorithm selection ---
# TODO: a radio/selectbox letting the user choose forward chaining
# (solve_full_grid_fc) or backward chaining (solve_full_grid_bc).
# TODO: a button that times and calls the chosen solver on
# (n, box_h, box_w, givens), then displays the solved grid and the elapsed
# time.

algorithm = st.radio(
    "Choose an algorithm",
    ["Forward chaining", "Backward chaining"],
    index=1,
)

if algorithm == "Forward chaining":
    st.warning(
        "Forward chaining may take tens of minutes or longer "
        "for a full puzzle with the current solver."
    )

# Convert JSON keys such as "1_2" into tuples such as (1, 2)
solver_givens = {
    tuple(map(int, key.split("_"))): value
    for key, value in givens.items()
}

if st.button("Solve puzzle"):
    # Clear the previous result before a new attempt
    st.session_state.pop("solve_result", None)

    try:
        start = time.perf_counter()

        if algorithm == "Forward chaining":
            result = solve_full_grid_fc(
                n, pool["box_h"], pool["box_w"], solver_givens
            )
        else:
            result = solve_full_grid_bc(
                n, pool["box_h"], pool["box_w"], solver_givens
            )

        elapsed = time.perf_counter() - start

        # Save the result for later page reruns
        st.session_state["solve_result"] = {
            "grid": result,
            "elapsed": elapsed,
            "algorithm": algorithm,
        }

    except NotImplementedError:
        st.warning("The selected solver has not been implemented yet.")

# Display saved results on every rerun
if "solve_result" in st.session_state:
    saved = st.session_state["solve_result"]

    result_board = [
        [str(saved["grid"].get((r, c), "")) for c in range(1, n + 1)]
        for r in range(1, n + 1)
    ]

    st.subheader("Solver result")
    render_board(
        result_board,
        givens,
        pool["box_h"],
        pool["box_w"],
    )

    st.caption(
        "Gray / bold: initial givens · Blue: inferred values"
    )
    st.write(f"Algorithm used: {saved['algorithm']}")
    st.write(f"Elapsed time: {saved['elapsed']:.3f} seconds")


# --- 3. Targeted cell entailment query ---
# TODO: number inputs for row (r), column (c), value (v).
# TODO: a button that builds the definite KB, calls
# pl_bc_entails(kb, atom('Is', r, c, v)), and displays True/False.

st.subheader("Query a cell")

with st.form("cell_query"):
    r = st.number_input("Row", min_value=1, max_value=n, value=1)
    c = st.number_input("Column", min_value=1, max_value=n, value=1)
    v = st.number_input("Value", min_value=1, max_value=n, value=1)

    submitted = st.form_submit_button("Check entailment")

if submitted:
    st.session_state.pop("query_result", None)
    st.session_state.pop("replay_step", None)

    try:
        kb = build_definite_kb(
            n, pool["box_h"], pool["box_w"], solver_givens
        )

        query = atom("Is", r, c, v)
        trace = []
        verdict = pl_bc_entails(kb, query, trace=trace)

        st.session_state["query_result"] = {
            "row": r,
            "column": c,
            "value": v,
            "verdict": verdict,
            "trace": trace,
        }

    except NotImplementedError as error:
        st.warning(f"Not implemented: {error}")


if "query_result" in st.session_state:
    saved_query = st.session_state["query_result"]

    st.write(
        f"Is row {saved_query['row']}, "
        f"column {saved_query['column']} "
        f"equal to {saved_query['value']}? "
        f"{saved_query['verdict']}"
    )

    if not saved_query["verdict"]:
        st.caption(
            "False means the knowledge base could not prove this query; "
            "it does not by itself prove the opposite."
        )
# --- 4. Reasoning trace ("tutor mode") ---
# TODO: instrument your forward- or backward-chaining approach to record each
# reasoning step (which rule fired, on what premises, producing what
# conclusion) as it answers the query above.
# TODO: render that trace as human-readable output -- e.g. a sequence of
# st.expander(...) blocks, one per step, each with a plain-English sentence
# -- not a raw list/dict dump.
# Keep the core solver functions in sudoku_solver.py; do not duplicate them here.

st.subheader("Reasoning trace")

if "query_result" not in st.session_state:
    st.info("Submit a cell query to view its reasoning trace.")

else:
    saved_query = st.session_state["query_result"]
    trace = saved_query["trace"]

    st.caption(
        f"Recorded deductions while checking row {saved_query['row']}, "
        f"column {saved_query['column']}, "
        f"value {saved_query['value']}."
    )

    if not trace:
        st.info("No successful deductions were recorded for this query.")

    else:
        st.subheader("Step-by-step replay")

        # Step navigation
        previous_col, step_col, next_col = st.columns([1, 2, 1])

        if previous_col.button("← Previous"):
            current = st.session_state.get("replay_step", 0)
            st.session_state["replay_step"] = max(0, current - 1)

        if next_col.button("Next →"):
            current = st.session_state.get("replay_step", 0)
            st.session_state["replay_step"] = min(
                len(trace), current + 1
            )

        step_count = step_col.number_input(
            "Replay step",
            min_value=0,
            max_value=len(trace),
            step=1,
            key="replay_step",
        )

        st.caption(
            f"Step {step_count} of {len(trace)} "
            "· Step 0 = initial puzzle"
        )

        # Start from the original givens
        replay_board = [
            [
                str(givens.get(f"{r}_{c}", ""))
                for c in range(1, n + 1)
            ]
            for r in range(1, n + 1)
        ]

        # Add only values proved up to the selected step
        for event in trace[:step_count]:
            symbol = str(event["conclusion"])

            if symbol.startswith("Is"):
                rr, cc, vv = map(int, symbol[2:].split("_"))
                replay_board[rr - 1][cc - 1] = str(vv)

        # Identify the cell involved in the current step
        focus = None

        if step_count > 0:
            current_step = trace[step_count - 1]
            symbol = str(current_step["conclusion"])

            prefix_length = 3 if symbol.startswith("Not") else 2
            rr, cc, vv = map(
                int, symbol[prefix_length:].split("_")
            )

            focus = (rr, cc)

        # Left: board. Right: reasoning for the selected step.
        board_col, reasoning_col = st.columns(
            [1, 1],
            gap="large",
        )

        with board_col:
            render_board(
                replay_board,
                givens,
                pool["box_h"],
                pool["box_w"],
                focus=focus,
            )

            st.caption(
                "Yellow: current cell · Gray / bold: givens · "
                "Blue: inferred values"
            )

        with reasoning_col:
            with st.container(border=True):
                if step_count == 0:
                    st.markdown("#### Initial puzzle")
                    st.write("Only the original givens are shown.")
                    st.caption(
                        "Choose Next to follow the reasoning."
                    )

                else:
                    st.markdown(f"#### Step {step_count}")

                    st.info(
                        describe_atom(current_step["conclusion"])
                    )

                    premises = current_step["premises"]

                    if not premises:
                        st.write(
                            "This is an initial given in the puzzle."
                        )

                    else:
                        st.write(
                            explain_rule(
                                current_step["conclusion"],
                                premises,
                                n,
                            )
                        )

                        with st.expander(
                            "Premises used",
                            expanded=True,
                        ):
                            for premise in premises:
                                st.write(
                                    f"- {describe_atom(premise)}"
                                )

        # Full trace, shown in pages
        st.divider()
        st.markdown("#### Full reasoning log")

        page_size = 10
        total_steps = len(trace)
        total_pages = (
            total_steps + page_size - 1
        ) // page_size

        page = st.selectbox(
            "Trace page",
            options=range(1, total_pages + 1),
            format_func=lambda p: f"Page {p} of {total_pages}",
        )

        start = (page - 1) * page_size
        end = min(start + page_size, total_steps)

        st.caption(
            f"Showing steps {start + 1}–{end} of {total_steps}"
        )

        for step_number, step in enumerate(
            trace[start:end],
            start=start + 1,
        ):
            conclusion = describe_atom(step["conclusion"])
            premises = step["premises"]

            with st.expander(
                f"Step {step_number}: {conclusion}"
            ):
                if not premises:
                    st.write(
                        "This is an initial given in the puzzle."
                    )

                else:
                    st.write("Established premises:")

                    for premise in premises:
                        st.write(
                            f"- {describe_atom(premise)}"
                        )

                    st.write(
                        explain_rule(
                            step["conclusion"],
                            premises,
                            n,
                        )
                    )