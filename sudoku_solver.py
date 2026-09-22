"""IT5005 Assignment 1: student implementation file.

Implement the functions marked below. Do not modify utils.py or logic_.py.
"""

from utils import *
from logic_ import *


# Do not change this function; it is used to create atomic propositions.
def atom(prefix, r, c, v):
    """prefix is 'Is' or 'Not'. Returns the Expr for e.g. Is3_2_4."""
    return expr(f'{prefix}{r}_{c}_{v}')


def build_general_kb(n, box_h, box_w, givens):
    """Return a PropKB encoding this n x n Sudoku's constraints plus the given
    cells, as general clauses.

    Parameters
    ----------
    n, box_h, box_w : int
    givens : dict[(int, int), int]

    Returns
    -------
    PropKB
    """
    kb = PropKB()

    # Create all cell coordinates.
    cells = [
        (r, c)
        for r in range(1, n + 1)
        for c in range(1, n + 1)
    ]

    def add_no_duplicates(unit):
        """Prevent two cells in the same unit from sharing a value."""
        for v in range(1, n + 1):
            for i in range(len(unit)):
                for j in range(i + 1, len(unit)):
                    r1, c1 = unit[i]
                    r2, c2 = unit[j]

                    kb.tell(
                        ~atom('Is', r1, c1, v) |
                        ~atom('Is', r2, c2, v)
                    )

    # Rule 1: Each cell contains at least one value.
    for r, c in cells:
        clause = atom('Is', r, c, 1)

        for v in range(2, n + 1):
            clause = clause | atom('Is', r, c, v)

        kb.tell(clause)

    # Rule 2: Each cell contains at most one value.
    for r, c in cells:
        for v1 in range(1, n + 1):
            for v2 in range(v1 + 1, n + 1):
                kb.tell(
                    ~atom('Is', r, c, v1) |
                    ~atom('Is', r, c, v2)
                )

    # Rules 3 and 4: Row and column uniqueness.
    for r in range(1, n + 1):
        row = [(r, c) for c in range(1, n + 1)]
        add_no_duplicates(row)

    for c in range(1, n + 1):
        column = [(r, c) for r in range(1, n + 1)]
        add_no_duplicates(column)

    # Rule 5: Box uniqueness.
    for start_r in range(1, n + 1, box_h):
        for start_c in range(1, n + 1, box_w):
            box = [
                (r, c)
                for r in range(start_r, start_r + box_h)
                for c in range(start_c, start_c + box_w)
            ]

            add_no_duplicates(box)

    # Rule 6: Add the given values as facts.
    for (r, c), v in givens.items():
        kb.tell(atom('Is', r, c, v))

    return kb


def build_definite_kb(n, box_h, box_w, givens):
    """Return a PropDefiniteKB encoding this n x n Sudoku's constraints plus
    the given cells, using elimination + last-candidate reasoning.

    Parameters
    ----------
    n, box_h, box_w : int
    givens : dict[(int, int), int] -- {(row, col): value}, 1-indexed

    Returns
    -------
    PropDefiniteKB
    """
    # Create an empty definite-clause knowledge base.
    kb = PropDefiniteKB()

    # Rule 6: Add each given cell as a known fact. Ex: (1, 1): 5 becomes Is1_1_5.
    for (r, c), v in givens.items():
        kb.tell(atom('Is', r, c, v))

    # Rules 2-5: elimination rules, generated for EVERY cell and EVERY value
    # (not only for the given cells), so that a value inferred later can
    # itself eliminate candidates in its row / column / box.
    for r in range(1, n + 1):
        for c in range(1, n + 1):
            for v in range(1, n + 1):

                # Collect every other cell in the same row, column or box.
                # A set is used so a cell that is both in the same row and
                # the same box is only added once.
                others = set()

                for other_c in range(1, n + 1):
                    if other_c != c:
                        others.add((r, other_c))

                for other_r in range(1, n + 1):
                    if other_r != r:
                        others.add((other_r, c))

                box_start_r = ((r - 1) // box_h) * box_h + 1
                box_start_c = ((c - 1) // box_w) * box_w + 1
                for other_r in range(box_start_r, box_start_r + box_h):
                    for other_c in range(box_start_c, box_start_c + box_w):
                        if other_r != r or other_c != c:
                            others.add((other_r, other_c))

                # Rules 3, 4, 5: if (r, c) is v, no other cell in the same
                # row / column / box can be v.
                for other_r, other_c in others:
                    kb.tell(
                        expr(
                            f'Is{r}_{c}_{v} ==> Not{other_r}_{other_c}_{v}'
                        )
                    )

                # Rule 2: if (r, c) is v, it is not any other value.
                for other_v in range(1, n + 1):
                    if other_v != v:
                        kb.tell(
                            expr(
                                f'Is{r}_{c}_{v} ==> Not{r}_{c}_{other_v}'
                            )
                        )

    # Rule 1 (Horn form): last-candidate rules. If a cell cannot contain any
    # of the other values, then it must contain the remaining value.
    for r in range(1, n + 1):
        for c in range(1, n + 1):
            for value in range(1, n + 1):

                # Collect all values except the current value.
                premises = []

                for other_value in range(1, n + 1):
                    if other_value != value:
                        premises.append(
                            f'Not{r}_{c}_{other_value}'
                        )

                # Build the left-hand side of the rule.
                premise_text = ' & '.join(premises)

                # Build the complete rule:
                # Not_rc1 & ... & Not_rc8 ==> Is_rcv
                rule = expr(
                    f'{premise_text} ==> Is{r}_{c}_{value}'
                )

                # Add the rule to the definite knowledge base.
                kb.tell(rule)

    return kb


def solve_full_grid_fc(n, box_h, box_w, givens):
    """Solve the whole puzzle using build_definite_kb + pl_fc_entails.

    Returns
    -------
    dict[(int, int), int] -- {(row, col): value} for every cell
    """
    kb = build_definite_kb(n, box_h, box_w, givens)
    grid = dict(givens)

    for r in range(1, n + 1):
        for c in range(1, n + 1):
            if (r, c) in grid:
                continue
            for v in range(1, n + 1):
                if pl_fc_entails(kb, atom('Is', r, c, v)):
                    grid[(r, c)] = v
                    break

    return grid


def pl_bc_entails(kb, query, trace=None):
    """Your own backward-chaining implementation.

    Parameters
    ----------
    kb : PropDefiniteKB
    query : Expr
    trace : list or None -- optional. If a list is given, every rule that
        succeeds is appended to it as {'conclusion': Expr, 'premises': [Expr]}.
        A fact is recorded with premises == [].

    Returns
    -------
    bool
    """
    import sys
    sys.setrecursionlimit(10000)

    # Index: conclusion -> [premise list, premise list, ...].
    # Built once per KB and cached on the KB object.
    index = getattr(kb, '_bc_index', None)
    if index is None:
        index = {}
        for clause in kb.clauses:
            premises, conclusion = parse_definite_clause(clause)
            index.setdefault(conclusion, []).append(premises)
        kb._bc_index = index

    proven = set()   # goals proven True (kept for the whole query)

    def prove(goal, chain, failed):
        # chain  : goals currently being proved on this path (cycle guard)
        # failed : goals that could not be proved in this round
        if goal in proven:
            return True
        if goal in chain or goal in failed:
            return False

        deeper = chain | {goal}
        for premises in index.get(goal, []):
            # A fact has premises == [] and all([]) is True.
            if all(prove(p, deeper, failed) for p in premises):
                proven.add(goal)
                if trace is not None:
                    trace.append({'conclusion': goal, 'premises': list(premises)})
                return True

        failed.add(goal)
        return False

    # A goal may be marked failed only because a premise hit the cycle
    # guard, while that premise was proved later through another rule.
    # So: repeat with a fresh 'failed' set until either the query is proved
    # or a whole round adds nothing new to 'proven'.
    while True:
        before = len(proven)
        if prove(query, frozenset(), set()):
            return True
        if len(proven) == before:
            return False


def solve_full_grid_bc(n, box_h, box_w, givens):
    """Solve the whole puzzle using build_definite_kb + your own pl_bc_entails.

    For each cell, try each candidate value until pl_bc_entails confirms one
    -- the same per-cell strategy as solve_full_grid_fc, but backed by
    backward chaining instead of a single shared forward-chaining pass.

    Returns
    -------
    dict[(int, int), int] -- {(row, col): value} for every cell
    """
    kb = build_definite_kb(n, box_h, box_w, givens)
    grid = dict(givens)

    for r in range(1, n + 1):
        for c in range(1, n + 1):
            if (r, c) in grid:
                continue
            for v in range(1, n + 1):
                if pl_bc_entails(kb, atom('Is', r, c, v)):
                    grid[(r, c)] = v
                    break

    return grid