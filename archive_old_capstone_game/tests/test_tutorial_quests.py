import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.capstone_contract import new_game, apply_action
from src.tutorial import note_event, update_unlocks, is_unlocked
from src.tutorial_quests import (
    TUTORIAL_CHAPTERS, TutorialTask, TutorialChapter, get_quest_progress,
)


class TestTutorialTaskAndChapter(unittest.TestCase):
    """TutorialTask/TutorialChapter are plain wrappers -- is_done just
    forwards to done_check, completed_count/chapter.is_done aggregate over
    the task list."""

    def test_task_is_done_forwards_to_done_check(self):
        task = TutorialTask("t1", "ch1", "標題", "提示", lambda state: True)
        self.assertTrue(task.is_done(new_game()))

        task2 = TutorialTask("t2", "ch1", "標題2", "提示2", lambda state: False)
        self.assertFalse(task2.is_done(new_game()))

    def test_chapter_completed_count_and_is_done(self):
        tasks = [
            TutorialTask("a", "c", "A", "hintA", lambda state: True),
            TutorialTask("b", "c", "B", "hintB", lambda state: False),
        ]
        chapter = TutorialChapter("c", "Chapter", "sub", tasks)
        state = new_game()
        self.assertEqual(chapter.completed_count(state), 1)
        self.assertFalse(chapter.is_done(state))

        tasks[1].done_check = lambda state: True
        self.assertEqual(chapter.completed_count(state), 2)
        self.assertTrue(chapter.is_done(state))


class TestChapterStructure(unittest.TestCase):
    """Structural sanity on the real chapter table -- catches accidental
    duplicate ids or an empty chapter, which get_quest_progress silently
    tolerates but would make the Sidebar look broken."""

    def test_three_chapters_matching_section_three_four_five(self):
        self.assertEqual(len(TUTORIAL_CHAPTERS), 3)
        ids = [c.id for c in TUTORIAL_CHAPTERS]
        self.assertEqual(ids, ["start_farm", "defend_farm", "decorate_farm"])

    def test_chapter_one_has_nine_tasks(self):
        self.assertEqual(len(TUTORIAL_CHAPTERS[0].tasks), 9)

    def test_chapter_two_has_seven_tasks(self):
        self.assertEqual(len(TUTORIAL_CHAPTERS[1].tasks), 7)

    def test_chapter_three_has_six_tasks(self):
        self.assertEqual(len(TUTORIAL_CHAPTERS[2].tasks), 6)

    def test_all_task_ids_are_unique(self):
        all_ids = [t.id for c in TUTORIAL_CHAPTERS for t in c.tasks]
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_fountain_task_never_says_noquan(self):
        """風車 was renamed from 小型噴泉 -- the Chapter 3 task about it must
        never regress back to the old name."""
        fountain_task = next(t for t in TUTORIAL_CHAPTERS[2].tasks if t.id == "fountain")
        self.assertIn("風車", fountain_task.hint)
        self.assertNotIn("噴泉", fountain_task.title)
        self.assertNotIn("噴泉", fountain_task.hint)


class TestGetQuestProgress(unittest.TestCase):
    """get_quest_progress is the single function the Sidebar (and thought.py's
    quest_guidance entry) reads from -- this is the contract both of those
    depend on."""

    def test_fresh_game_current_task_is_first_task_of_first_chapter(self):
        state = new_game()
        progress = get_quest_progress(state)
        self.assertEqual(progress["current_chapter"].id, "start_farm")
        self.assertEqual(progress["current_task"].id, "move")
        self.assertEqual(progress["completed_task_ids"], set())
        self.assertEqual(progress["total_progress"][0], 0)

    def test_total_progress_denominator_matches_full_task_count(self):
        state = new_game()
        progress = get_quest_progress(state)
        total_tasks = sum(len(c.tasks) for c in TUTORIAL_CHAPTERS)
        self.assertEqual(progress["total_progress"][1], total_tasks)

    def test_current_task_advances_as_real_state_changes(self):
        """A player who does things "out of order" (e.g. moves the camera
        before anything else) still gets the move task ticked off the
        moment update_unlocks() next runs -- no code path here gates any
        action on quest order."""
        state = new_game()
        note_event(state, "camera_moved")
        update_unlocks(state)
        progress = get_quest_progress(state)
        self.assertIn("move", progress["completed_task_ids"])
        self.assertNotEqual(progress["current_task"].id, "move")

    def test_full_beginner_flow_ticks_every_chapter_one_task_in_order(self):
        """End-to-end walk through Chapter 1 exactly as a real new player
        would trigger each step, confirming get_quest_progress reports each
        task done in turn and finally reports chapter 1 fully complete."""
        state = new_game()

        # 1. move
        note_event(state, "camera_moved")
        update_unlocks(state)
        self.assertIn("move", get_quest_progress(state)["completed_task_ids"])

        # 2. f_thought
        note_event(state, "f_thought_used")
        update_unlocks(state)
        self.assertIn("f_thought", get_quest_progress(state)["completed_task_ids"])

        # 3. hoe (till) -- tilling is a two-tick building_task, not instant
        # (mirrors test_tutorial.py's own use_hoe_ + tick*2 pattern).
        state = apply_action(state, "use_hoe_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        update_unlocks(state)
        self.assertIn("hoe", get_quest_progress(state)["completed_task_ids"])

        # 4. seed selected
        note_event(state, "seed_selected")
        update_unlocks(state)
        self.assertIn("seed", get_quest_progress(state)["completed_task_ids"])

        # 5. plant -- also a multi-tick building_task (max_progress=3).
        state = apply_action(state, "plant_crop_radish_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        update_unlocks(state)
        self.assertIn("plant", get_quest_progress(state)["completed_task_ids"])

        # 6. wait for maturity
        data = state["farm"]["crop_data"][(5, 5)]
        data["stage"] = data["max_stage"]
        update_unlocks(state)
        self.assertIn("crop_matured", get_quest_progress(state)["completed_task_ids"])

        # 7. harvest (any inventory item)
        state["inventory"]["radish"]["normal"] = 1
        update_unlocks(state)
        self.assertIn("harvest", get_quest_progress(state)["completed_task_ids"])

        # 8. shop
        note_event(state, "shop_opened")
        update_unlocks(state)
        self.assertIn("shop", get_quest_progress(state)["completed_task_ids"])

        # 9. sell
        note_event(state, "crop_sold")
        update_unlocks(state)
        progress = get_quest_progress(state)
        self.assertIn("sell", progress["completed_task_ids"])

        chapter1 = TUTORIAL_CHAPTERS[0]
        self.assertTrue(chapter1.is_done(state))
        self.assertNotEqual(progress["current_chapter"].id, "start_farm")

    def test_current_chapter_is_last_chapter_once_everything_done(self):
        state = new_game()
        # Force every underlying tutorial.py step true via update_unlocks'
        # own latch table, mirroring test_thought.py's
        # _skip_beginner_intros-style approach.
        from src.tutorial import TUTORIAL_STEPS
        state["tutorial"] = {
            "unlocked": {s["id"]: True for s in TUTORIAL_STEPS},
            "flags": {}, "seen_counts": {},
        }
        progress = get_quest_progress(state)
        self.assertIsNone(progress["current_task"])
        self.assertEqual(progress["current_chapter"].id, TUTORIAL_CHAPTERS[-1].id)
        self.assertEqual(progress["total_progress"][0], progress["total_progress"][1])


if __name__ == "__main__":
    unittest.main()
