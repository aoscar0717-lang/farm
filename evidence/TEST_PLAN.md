# Focused Test Plan

Write the expectation before running the test. At least six meaningful tests must be implemented and green by V2; V3 adds or updates a regression check for the playtest-driven change when feasible.[cite: 28]

| ID | Contract/rule | Starting state/input | Expected observation | What failure would mean | Author | Status |
|---|---|---|---|---|---|---|
| T01 | Fresh state (Contract 1) | Call `reset_game()`. Map 5x5. | `crop.is_alive == True`, 0 fences on map, thief at edge. | Initialization logic is broken; game cannot start properly. | Team | Planned |
| T02 | Normal action (Contract 2.1 - Place Fence) | Day phase. Input: `place_fence(1, 1)` on empty tile. | Grid (1,1) state changes to `Fence`. | Player cannot build defenses, breaking the core mechanic. | Team | Planned |
| T03 | Boundary/invalid action (Contract 2.1 - Invalid Placement) | Day phase. Input: `place_fence` on the Crop's coordinate. | Returns `InvalidPlacement`. Grid state unchanged. | Players could overwrite objectives or break the map constraints. | Team | Planned |
| T04 | Normal action (Contract 2 - Whack-a-mole attempt) | Day phase. Input: Click exactly on the Thief's current coordinate. | Returns `Evaded`. Thief moves to an adjacent empty tile. | The intended "friction" is missing; players might successfully kill the thief by clicking. | Team | Planned |
| T05 | Success/failure (Contract 3 - Win Condition) | Night phase starts. Crop is fully surrounded by fences. | Thief pathfinding returns False. Game state changes to `Win`. | Win condition cannot trigger; game is unwinnable even with correct strategy. | Team | Planned |
| T06 | Success/failure (Contract 3 - Lose Condition) | Night phase starts. Clear path exists to the crop. | Thief reaches crop. Game state changes to `Lose`. | Failure state is broken; there's no consequence for not building defenses. | Team | Planned |
| T07 | Stable snapshot (Contract 4) | Load specific level layout file twice sequentially. | Output grid layouts and entity coordinates match exactly both times. | Randomness is bleeding into initialization, making tests flaky. | Team | Planned |

## Test quality check

- [x] Every test names one observable rule.[cite: 28]
- [x] At least one test can fail for a realistic defect.[cite: 28]
- [x] Boundary expectations are exact.[cite: 28]
- [x] Tests do not depend on display, audio, wall-clock time, or network unless the contract explicitly requires them.[cite: 28]
- [ ] No required test remains skipped.[cite: 28]
- [ ] Every member can explain at least one test.[cite: 28]