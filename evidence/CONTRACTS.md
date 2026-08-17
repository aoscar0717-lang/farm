# Game Contracts

Complete at least four contracts. Use the project's actual names; the examples below are roles, not required names.

## Contract 1 - Fresh state / restart

- Function or rule: Initialize Game State (Start Day)[cite: 29]
- Accepted input: Player clicks "Start/Restart Game" button.[cite: 29]
- Returned/observable result: Farm grid is generated (e.g., 5x5). Crop is placed at a specific coordinate. Thief is spawned at a starting edge coordinate. Time is set to Day/Dusk. Inventory shows available fences.[cite: 29]
- Invariant: The crop exists on the map. The player starts with 0 fences placed on the map.[cite: 29]
- Boundary or failure behavior: If map size is too small (e.g., 1x1), the game throws an initialization error.[cite: 29]
- Example with expected observation: Call `reset_game()`. Observe: `crop.is_alive == True`, `len(placed_fences) == 0`.[cite: 29]

## Contract 2 - Player action

- Function or rule: Directly Click on Thief (Whack-a-mole attempt)[cite: 29]
- Accepted input: Mouse click coordinate matches the thief's current coordinate.[cite: 29]
- Returned/observable result: Thief evades the click (moves to an adjacent available tile immediately) and triggers a mocking animation/sound. The click does NOT eliminate the thief.[cite: 29]
- Invariant: The thief remains active on the board. The crop state remains unchanged by this action.[cite: 29]
- Boundary or failure behavior: If the thief is trapped by boundaries/fences and clicked, it remains in place but is still not eliminated (mocking triggers).[cite: 29]
- Example with expected observation: Thief is at (2,2). Player calls `click_at(2,2)`. Observe: Thief moves to e.g. (2,3), returns `Evaded`.[cite: 29]

## Contract 3 - Success or failure

- Function or rule: Night Phase Resolution (Thief Movement)[cite: 29]
- Accepted input: System advances turn (Night begins). Thief pathfinds towards the crop.[cite: 29]
- Returned/observable result: If thief reaches the crop coordinate: Game Over (Failure). If thief's path to the crop is completely blocked by fences: Game Win (Success).[cite: 29]
- Invariant: The game must reach either a Success or Failure state once the night phase concludes.[cite: 29]
- Boundary or failure behavior: If pathfinding algorithm fails or loops infinitely, force a timeout error.[cite: 29]
- Example with expected observation: Crop at (3,3). Fences placed surrounding it. Night starts. Observe: Thief `can_reach_crop == False`, Game State changes to `Win`.[cite: 29]

## Contract 4 - Stable snapshot

- Function or rule: Save/Load Level Layout[cite: 29]
- Stable fields: Grid dimensions, Crop coordinate, Starting Thief coordinate.[cite: 29]
- Excluded device/time fields: System clock time, frames per second (FPS), player mouse hover positions.[cite: 29]
- Expected repeated-run observation: Loading the same level layout file always results in the exact same starting grid state.[cite: 29]
- What a mismatch would mean: The serialization logic is faulty or random elements are incorrectly affecting the initial setup, breaking test reproducibility.[cite: 29]

## Additional contract

- Function or rule: Place Fence[cite: 29]
- Accepted input: Select "Fence" from UI, then click an empty grid coordinate during the "Day/Dusk" phase.[cite: 29]
- Returned/observable result: A fence is placed at the specified coordinate. Thief cannot move onto this coordinate.[cite: 29]
- Invariant: A fence cannot be placed on a coordinate already occupied by the crop, another fence, or the thief.[cite: 29]
- Boundary or failure behavior: Clicking an occupied tile returns `InvalidPlacement`. Placing a fence during the "Night" phase (when the thief is actively moving) returns `ActionNotAllowed`.[cite: 29]
- Example with expected observation: Call `place_fence(1,1)`. Observe: Grid at (1,1) changes state to `Fence`.[cite: 29]