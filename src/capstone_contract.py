"""Optional game-neutral contract boundary for a beginner Capstone.

Keep an existing working prototype. Adapt these names to the project instead of
rewriting the game merely to match this file. Each TODO has comments that define
the responsibility without supplying a game-specific answer.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

GameState = dict[str, Any]


def new_game(seed: int = 0) -> GameState:
    """Return one fresh, device-free state.

    TODO for the trio:
    - validate or document the accepted seed;
    - include only state needed by the game rules;
    - keep display, audio, clock, and network objects outside this state; and
    - make the initial snapshot predictable for a fixed seed.
    """
    raise NotImplementedError("Map new_game to the team's real game state")


def apply_action(state: GameState, action: str) -> GameState:
    """Return the next state for one documented action.

    TODO for the trio:
    - copy or reconstruct state so the supplied object is not silently changed;
    - handle one normal action and one boundary/invalid action explicitly;
    - update only fields owned by this rule; and
    - preserve invariants named in evidence/CONTRACTS.md.
    """
    _working_copy = deepcopy(state)
    del _working_copy, action
    raise NotImplementedError("Map apply_action to one real player rule")


def is_terminal(state: GameState) -> bool:
    """Return whether the documented success/failure rule has been reached."""
    del state
    raise NotImplementedError("Map is_terminal to the team's end condition")


def snapshot(state: GameState) -> tuple[tuple[str, object], ...]:
    """Return stable evidence that focused tests can compare.

    TODO for the trio:
    - choose stable rule-owned fields;
    - exclude display surfaces, audio devices, object IDs, and wall-clock time;
    - convert mutable/nested values to a stable comparable form as needed.
    """
    return tuple(sorted(state.items()))

