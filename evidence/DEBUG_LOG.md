# Genuine Red-to-Green Debug Record

## Context

- Version/branch: V2 (Test-driven implementation)
- Failing command: `python -m pytest tests/`
- Exact failing test or observable behavior: All 7 tests failed immediately with `NameError: name 'random' is not defined` during the `new_game(seed=42)` call.
- First project-owned file/line to inspect: `src/capstone_contract.py` line 22 (`random.seed(seed)`).

## Evidence before repair

- Observed fact: The Python interpreter crashed because the `random` module was used but never imported at the top of the file.
- Contract expectation: `new_game` must deterministically initialize the game state without throwing syntax or import errors.
- Unsupported explanation rejected: The game logic itself wasn't flawed; it was strictly a Python environment/import issue.
- Smallest current hypothesis: Adding `import random` to the top of `src/capstone_contract.py` will resolve the `NameError`.
- Observation that would disprove the hypothesis: The error persists even after adding the import statement, which would imply shadowing or a corrupted environment.

## Repair

- Smallest changed files/lines: Added `import random` at line 1 of `src/capstone_contract.py`.
- Why the repair stays inside the contract: It strictly fulfills the requirement for predictable random behavior without altering any state transition rules.
- AI assistance used, if any: Yes, AI identified the missing import from the traceback and provided the corrected file.

## Verification

- Focused rerun command: `python -m pytest tests/`
- Focused observation: The `NameError` disappeared.
- Full regression command: `python -m pytest tests/`
- Full regression observation: `7 passed in 0.02s` [100%].
- Git diff reviewed by: Team
- Commit/PR: (待填寫)
- Remaining limitation: None.