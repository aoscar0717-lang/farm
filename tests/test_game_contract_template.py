"""Replace each skipped template with a real project-specific focused test.

The templates are intentionally skipped so this kit does not invent the team's
game rules. V2 acceptance requires at least six meaningful tests and zero
required skips.
"""

import pytest


@pytest.mark.skip(reason="Replace with the team's fresh-state expectation")
def test_new_game_has_expected_stable_snapshot():
    # Arrange: choose a fixed seed.
    # Act: create a fresh state and take a stable snapshot.
    # Assert: write the exact expected observation.
    pass


@pytest.mark.skip(reason="Replace with one normal player-action contract")
def test_one_player_action_changes_exactly_the_owned_state():
    # Arrange: create the smallest useful starting state.
    # Act: apply one documented action.
    # Assert: name the exact changed field and one invariant that remains true.
    pass


@pytest.mark.skip(reason="Replace with one boundary or invalid-action contract")
def test_boundary_or_invalid_action_has_documented_behavior():
    # Arrange: use the last legal and first illegal values when possible.
    # Act: apply the boundary input.
    # Assert: name the exact expected state or exception.
    pass


@pytest.mark.skip(reason="Replace with the terminal-state contract")
def test_terminal_rule_changes_only_at_the_documented_condition():
    pass


@pytest.mark.skip(reason="Replace with the restart/fresh-state contract")
def test_restart_matches_a_fresh_same_seed_state():
    pass


@pytest.mark.skip(reason="Replace after observing a genuine defect")
def test_regression_for_the_recorded_debug_story():
    pass

