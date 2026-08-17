# Focused Test Plan

Write the expectation before running the test. At least six meaningful tests must be implemented and green by V2; V3 adds or updates a regression check for the playtest-driven change when feasible.

| ID | Contract/rule | Starting state/input | Expected observation | What failure would mean | Author | Status |
|---|---|---|---|---|---|---|
| T01 | Fresh state | | | | | Planned |
| T02 | Normal action | | | | | Planned |
| T03 | Boundary/invalid action | | | | | Planned |
| T04 | Success/failure | | | | | Planned |
| T05 | Invariant | | | | | Planned |
| T06 | Restart | | | | | Planned |
| T07 | Regression | | | | | Planned |

## Test quality check

- [ ] Every test names one observable rule.
- [ ] At least one test can fail for a realistic defect.
- [ ] Boundary expectations are exact.
- [ ] Tests do not depend on display, audio, wall-clock time, or network unless the contract explicitly requires them.
- [ ] No required test remains skipped.
- [ ] Every member can explain at least one test.

