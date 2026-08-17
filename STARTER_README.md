# Capstone Iteration Studio Starter

This pack does **not** replace your game. Copy its planning, evidence, test, and GitHub templates into the private repository that already contains your V0 prototype.

## Safe merge route

1. Preserve and tag the working V0 prototype before copying anything.
2. Copy `GROUP_CONTRACT.md`, `GAME_BRIEF.md`, `FINAL_REPORT_OUTLINE.md`, `.github/`, and `evidence/` into the repository root.
3. Read `src/capstone_contract.py`; adapt the four interface ideas to your game instead of overwriting working code.
4. Read `tests/test_game_contract_template.py`; replace every skipped example with a project-specific test.
5. Review the copied files with `git status --short` and `git diff` before committing.

If the destination already has a file with the same name, compare it first. Do not overwrite team work blindly.

## First verification

```bash
git status --short
python -m pytest -q
```

The template tests are intentionally skipped until the trio maps them to the actual game. A final V2 or V3 submission must contain at least six meaningful green tests and zero required skips.

## Keep private

Use one private GitHub repository. Never commit passwords, personal access tokens, `.env` files, private student data, or fabricated test/playtest output.
