"""Tutorial Quest / Sidebar layer -- built ON TOP of tutorial.py's existing
one-way latch table (TUTORIAL_STEPS / is_unlocked), never replacing it.
tutorial.py answers "has the player ever demonstrated understanding of X"
for a flat bag of individual concepts; this module groups a curated subset
of those same concepts into an ordered, chaptered checklist a player can
visually track ("what should I do next"), and is the single source of truth
the Tutorial Sidebar (src/ui.py::draw_tutorial_sidebar) renders from.

Design rules (matching the rest of this project's Tutorial/Thought split):

- A TutorialTask's `done_check` is a plain (state) -> bool. Nearly every
  task here just wraps tutorial.is_unlocked(state, step_id) for a step
  already defined in tutorial.py (including several added specifically for
  this module -- see tutorial.py's "Added for the Tutorial Quest / Sidebar
  system" section). Nothing here re-implements its own detection logic;
  this module *reads* tutorial.py, it doesn't compete with it. There is
  exactly one shared progress store (state["tutorial"]) -- Thought
  (src/thought.py) reads the exact same is_unlocked()/seen_counts data this
  module does, so the Sidebar, F 思索, and this module's own quest state can
  never disagree about whether something has been learned.

- A chapter is "done" once every task in it is done. Chapters are ordered
  (TUTORIAL_CHAPTERS is a plain list); get_quest_progress() reports the
  *first* not-yet-done task across all chapters, in that order, as
  "current_task" -- so the Sidebar always has exactly one thing to show as
  "what's next", never an empty list and never everything at once.

- Nothing here is a gate. Every task's done_check reads real, already-
  achievable state -- a player who already knows how to farm and does
  everything "out of order" (e.g. builds a fence before ever opening the
  shop) still gets every earlier box ticked automatically the moment
  update_unlocks() next runs (main.py calls it every frame now, not just
  while F is held -- see main.py). There is no code path anywhere in this
  module, or in capstone_contract.py, that blocks an action because an
  earlier quest task isn't done yet.

Extending this: add a new TutorialTask to an existing chapter's `tasks`
list, or a whole new TutorialChapter to TUTORIAL_CHAPTERS. If the task
needs a detection signal that doesn't exist yet, add one step to
tutorial.py's TUTORIAL_STEPS (not here) and wrap it with `_step(...)` below,
keeping tutorial.py as the single place real game-state detection lives.
"""

from src import tutorial as _tutorial


def _step(step_id):
    """The overwhelmingly common case: a done_check that just asks
    tutorial.py whether `step_id` has ever latched true."""
    return lambda state: _tutorial.is_unlocked(state, step_id)


class TutorialTask:
    """One checklist item. `thought_entry_id` (optional) names the
    src.thought THOUGHT_ENTRIES id most closely associated with this task,
    for traceability and for anything that wants to cross-reference the two
    (purely informational, like tutorial.py's `required_tutorial` field --
    nothing enforces it stays in sync beyond convention). `priority` is
    unused by get_quest_progress() itself (task order within a chapter's
    list is what determines "current task"); it's exposed for any future
    caller that wants to re-sort or weight tasks without changing this
    module's own ordering-by-list-position behavior."""

    __slots__ = ("id", "chapter_id", "title", "hint", "done_check", "thought_entry_id", "priority")

    def __init__(self, id, chapter_id, title, hint, done_check, thought_entry_id=None, priority=0):
        self.id = id
        self.chapter_id = chapter_id
        self.title = title
        self.hint = hint
        self.done_check = done_check
        self.thought_entry_id = thought_entry_id
        self.priority = priority

    def is_done(self, state):
        return bool(self.done_check(state))


class TutorialChapter:
    __slots__ = ("id", "title", "subtitle", "tasks")

    def __init__(self, id, title, subtitle, tasks):
        self.id = id
        self.title = title
        self.subtitle = subtitle
        self.tasks = tasks

    def completed_count(self, state):
        return sum(1 for t in self.tasks if t.is_done(state))

    def is_done(self, state):
        return all(t.is_done(state) for t in self.tasks)


# ---------------------------------------------------------------------------
# Chapter 1 -- 開始農場. Maps to section 三 of the design request: move / F
# thought / till / seed / plant / wait-for-maturity / harvest / shop /
# sell. "選擇一種種子" deliberately does NOT pretend a "purchase seed" event
# exists -- see tutorial.py's "seed_selected" step comment for why (the shop
# click only equips a tool; money is spent later, at plant time).
# ---------------------------------------------------------------------------
_CH_START_FARM = TutorialChapter(
    id="start_farm",
    title="開始農場",
    subtitle="從零開始的第一步",
    tasks=[
        TutorialTask("move", "start_farm", "認識移動",
                     "使用 WASD 或方向鍵，或按住滑鼠右鍵拖曳，探索農場。",
                     _step("move"), thought_entry_id="learn_move"),
        TutorialTask("f_thought", "start_farm", "認識 F 思索",
                     "按住 F，我會根據你現在看到的事物給你一些想法。",
                     _step("f_thought_used")),
        TutorialTask("hoe", "start_farm", "開墾農田",
                     "選擇鋤頭，找一塊空地開墾。",
                     _step("hoe"), thought_entry_id="action_till"),
        TutorialTask("seed", "start_farm", "選擇一種種子",
                     "在商店裡選擇一種種子（白蘿蔔／胡蘿蔔／魔法南瓜）。",
                     _step("seed_selected")),
        TutorialTask("plant", "start_farm", "種下作物",
                     "把種子種在已經開墾好的土地上。",
                     _step("plant"), thought_entry_id="action_plant"),
        TutorialTask("crop_matured", "start_farm", "等待作物成熟",
                     "作物需要一些時間生長，可以先去做別的事，之後再回來看看。",
                     _step("crop_matured"), thought_entry_id="info_growing_crop"),
        TutorialTask("harvest", "start_farm", "收割作物",
                     "作物成熟後，使用鐮刀收割。",
                     _step("harvest"), thought_entry_id="action_harvest"),
        TutorialTask("shop", "start_farm", "認識商店",
                     "按 B 可以打開商店，購買種子、防禦道具與景觀，或出售收成。",
                     _step("shop_sell")),
        TutorialTask("sell", "start_farm", "出售收成",
                     "在商店的出售頁籤，把收成換成資金。",
                     _step("crop_sold"), thought_entry_id="action_sell_crops"),
    ],
)

# ---------------------------------------------------------------------------
# Chapter 2 -- 守護農場. Maps to section 四: night/day, enemy awareness,
# fence, trap awareness + build, dog awareness, first defeat. All done_check
# read real farm/decor state (fences/traps/dogs lists, enemies_defeated) --
# never "did the player click a specific button".
# ---------------------------------------------------------------------------
_CH_DEFEND_FARM = TutorialChapter(
    id="defend_farm",
    title="守護農場",
    subtitle="夜晚不再無力",
    tasks=[
        TutorialTask("night", "defend_farm", "認識白天/夜晚",
                     "白天適合整理與建設，夜晚則會出現威脅。",
                     _step("night_start")),
        TutorialTask("enemy_seen", "defend_farm", "認識敵人",
                     "夜晚可能會有小偷入侵農田，或野豬闖入佈置區。",
                     _step("thief_seen"), thought_entry_id="danger_thief_present"),
        TutorialTask("fence", "defend_farm", "建造柵欄",
                     "柵欄可以擋住敵人的行動路線，替作物爭取時間。",
                     _step("fence"), thought_entry_id="action_fence_place"),
        TutorialTask("trap_aware", "defend_farm", "認識陷阱",
                     "地刺陷阱會對踩到的敵人造成傷害，是一次性的。",
                     _step("trap_aware"), thought_entry_id="action_trap_place"),
        TutorialTask("trap", "defend_farm", "建造地刺陷阱",
                     "把陷阱放在敵人的必經之路上。",
                     _step("trap"), thought_entry_id="action_trap_place"),
        TutorialTask("dog_aware", "defend_farm", "認識看門狗",
                     "狗會主動攻擊靠近的敵人，且不會陣亡。",
                     _step("dog_aware"), thought_entry_id="action_dog_place"),
        TutorialTask("enemy_defeated", "defend_farm", "擊退第一個敵人",
                     "用柵欄、陷阱、狗，或直接點擊攻擊，擊退入侵的敵人。",
                     _step("enemy_defeated"), thought_entry_id="danger_thief_present"),
    ],
)

# ---------------------------------------------------------------------------
# Chapter 3 -- 打造自己的農場. Maps to section 五: decor zone, first/second
# decoration, 風車 (never "噴泉" -- see fountain's naming history in
# capstone_contract.py / assets.py), prosperity, farm level.
# ---------------------------------------------------------------------------
_CH_DECORATE_FARM = TutorialChapter(
    id="decorate_farm",
    title="打造自己的農場",
    subtitle="讓農場更有自己的風格",
    tasks=[
        TutorialTask("zone", "decorate_farm", "認識佈置區",
                     "按 TAB 或畫面上方的按鈕，切換到佈置區。",
                     _step("zone_switch"), thought_entry_id="learn_zone_switch"),
        TutorialTask("decor1", "decorate_farm", "放置第一個景觀",
                     "在佈置區選一個景觀物，放在喜歡的地方。",
                     _step("decor_place"), thought_entry_id="learn_decor_place"),
        TutorialTask("decor2", "decorate_farm", "放置第二個景觀",
                     "再放一個景觀物，讓農場更完整。",
                     _step("decor_place_2")),
        TutorialTask("fountain", "decorate_farm", "認識風車",
                     "風車是農場景觀的一部分，也能提升繁榮度。",
                     _step("fountain_aware"), thought_entry_id="info_fountain_nearby"),
        TutorialTask("prosperity", "decorate_farm", "提升繁榮度",
                     "景觀物會提升農場的繁榮度。",
                     _step("prosperity"), thought_entry_id="learn_prosperity"),
        TutorialTask("farm_level", "decorate_farm", "提升農場等級",
                     "繁榮度提升到一定程度後，農場會逐步升級，解鎖新作物。",
                     _step("farm_level"), thought_entry_id="learn_farm_level"),
    ],
)

TUTORIAL_CHAPTERS = [_CH_START_FARM, _CH_DEFEND_FARM, _CH_DECORATE_FARM]


def get_quest_progress(state):
    """The single read function the Sidebar (and anything else that wants
    to know "what's the player's tutorial progress") needs.

    Returns a dict:
      current_chapter    the TutorialChapter containing the first not-yet-
                          done task, or the last chapter if everything is
                          done (never None as long as TUTORIAL_CHAPTERS is
                          non-empty).
      current_task       the first not-yet-done TutorialTask overall (in
                          chapter/task order), or None once every chapter is
                          complete.
      completed_task_ids set of every task id whose done_check is currently
                          True, across all chapters.
      chapter_progress   (done, total) int tuple for current_chapter.
      total_progress     (done, total) int tuple across every task in every
                          chapter.
    """
    completed_task_ids = set()
    current_chapter = None
    current_task = None
    total_done = 0
    total_count = 0

    for chapter in TUTORIAL_CHAPTERS:
        for task in chapter.tasks:
            total_count += 1
            if task.is_done(state):
                total_done += 1
                completed_task_ids.add(task.id)
            elif current_task is None:
                current_task = task
                current_chapter = chapter

    if current_chapter is None and TUTORIAL_CHAPTERS:
        # Every chapter complete -- report the last chapter so callers still
        # have something concrete to show progress for ("6/6"), not None.
        current_chapter = TUTORIAL_CHAPTERS[-1]

    chapter_progress = (0, 0)
    if current_chapter is not None:
        chapter_progress = (current_chapter.completed_count(state), len(current_chapter.tasks))

    return {
        "current_chapter": current_chapter,
        "current_task": current_task,
        "completed_task_ids": completed_task_ids,
        "chapter_progress": chapter_progress,
        "total_progress": (total_done, total_count),
    }
