import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.capstone_contract import new_game, apply_action
from src.thought import get_contemplation_lines


def _grow_one_night(state):
    """Crop stage only advances inside the start_night handler (once per
    day->night transition), not via plain "tick" -- so simulate a full,
    quick night to get back to day and be able to call start_night again."""
    state = apply_action(state, "start_night")
    for _ in range(65):
        state = apply_action(state, "tick")
        if state["phase"] == "day":
            break
    return state


def _skip_beginner_intros(state):
    """Tier-2 "haven't learned this yet" entries (move / shop / zone
    switch) are unconditional the moment a fresh game starts, and Tier 2
    outranks Tier 3 by design (an unlearned mechanic matters more than an
    ambient description of something nearby) -- exactly like a real player
    who's already panned the camera and opened the shop once. Directly
    marking these learned isolates the Tier-3 scenario under test instead
    of incidentally re-testing Tier-2-beats-Tier-3 (covered separately by
    TestThoughtPriorityTiers)."""
    state["tutorial"] = {"unlocked": {"move": True, "shop_sell": True, "zone_switch": True}, "flags": {}}


class TestThoughtScenarios(unittest.TestCase):
    """The six situations requested for manual testing, exercised directly
    against the Thought engine (no pygame needed -- main.py just computes
    hover_pos from the mouse and forwards everything else unchanged)."""

    def test_A_hovering_a_growing_crop(self):
        state = new_game()
        _skip_beginner_intros(state)
        state = apply_action(state, "use_hoe_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        state = apply_action(state, "plant_crop_radish_5_5")
        for _ in range(3):  # building_tasks "crop" needs 3 ticks to materialize
            state = apply_action(state, "tick")
        data = state["farm"]["crop_data"][(5, 5)]
        self.assertLess(data["stage"], data["max_stage"])

        state["money"] = 0  # otherwise "afford defenses" (Tier 1) outranks this Tier 3 info
        lines = get_contemplation_lines(state, "farm", None, False, hover_pos=(5, 5))
        self.assertEqual(lines, ["作物正在生長，可能還需要一點時間才會成熟。"])

    def test_B_hovering_a_mature_crop(self):
        state = new_game()
        state = apply_action(state, "use_hoe_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        state = apply_action(state, "plant_crop_radish_5_5")
        for _ in range(3):
            state = apply_action(state, "tick")
        data = state["farm"]["crop_data"][(5, 5)]
        # radish's growth_time is 5; stage only advances inside start_night
        # (once per day->night transition), never via plain "tick".
        while data["stage"] < data["max_stage"]:
            state = _grow_one_night(state)
            data = state["farm"]["crop_data"][(5, 5)]
        self.assertGreaterEqual(data["stage"], data["max_stage"])

        lines = get_contemplation_lines(state, "farm", "scythe", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["這株作物似乎已經成熟了，也許可以收割。"])

    def test_C_hoe_over_untilled_ground(self):
        state = new_game()
        lines = get_contemplation_lines(state, "farm", "hoe", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["這裡似乎可以開墾成農田。"])

    def test_D_seed_over_tilled_farmland(self):
        state = new_game()
        state = apply_action(state, "use_hoe_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        self.assertIn((5, 5), state["farm"]["farmland"])

        lines = get_contemplation_lines(state, "farm", "radish", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["這塊土地應該可以種下種子。"])

    def test_E_thief_appears_at_night(self):
        state = new_game()
        state["phase"] = "night"
        state["farm"]["thief_pos"] = (10, 10)

        lines = get_contemplation_lines(state, "farm", None, False, hover_pos=None)
        self.assertEqual(lines, ["有小偷正在靠近農田，直接點擊他可以攻擊。"])

    def test_F_hovering_near_a_fence(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0  # otherwise "afford defenses" (Tier 1) outranks this Tier 3 info
        state["farm"]["fences"].append((20, 20, 3))

        lines = get_contemplation_lines(state, "farm", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["圍欄可以擋住敵人的行動路線，替作物或造景爭取時間。"])


class TestThoughtPriorityTiers(unittest.TestCase):
    def test_danger_outranks_everything_else(self):
        # Stack a Tier-1 actionable condition (hovering tillable ground
        # with the hoe out), a Tier-2 unlearned-mechanic condition (fresh
        # game, "move" not learned), and a Tier-0 danger condition (thief
        # present at night) all at once -- danger must win.
        state = new_game()
        state["phase"] = "night"
        state["farm"]["thief_pos"] = (10, 10)

        lines = get_contemplation_lines(state, "farm", "hoe", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["有小偷正在靠近農田，直接點擊他可以攻擊。"])

    def test_unlearned_mechanic_outranks_ambient_fallback(self):
        state = new_game()
        # Below the $20 threshold so "you could afford defenses" (Tier 1)
        # doesn't also fire and legitimately outrank this (per the spec,
        # Tier 1 actionable > Tier 2 unlearned mechanic > Tier 4 ambient --
        # this test isolates Tier 2 vs Tier 4 specifically).
        state["money"] = 0
        # Nothing hovered, no danger, no immediate action -- but "move"
        # hasn't been learned yet, so it should win over the status fallback.
        lines = get_contemplation_lines(state, "farm", None, False, hover_pos=None)
        self.assertEqual(lines, ["按住滑鼠右鍵拖曳，或用 WASD/方向鍵，可以看看農場其他地方。"])

    def test_fallback_status_line_when_nothing_else_applies(self):
        state = new_game()
        state["money"] = 0  # otherwise "afford defenses" (demoted Tier 1) still beats Tier 4
        from src.tutorial import TUTORIAL_STEPS
        state["tutorial"] = {"unlocked": {s["id"]: True for s in TUTORIAL_STEPS}, "flags": {}}

        lines = get_contemplation_lines(state, "farm", None, False, hover_pos=None)
        self.assertTrue(lines[0].startswith(f"第 {state['day_count']} 天"))


class TestDecorThoughts(unittest.TestCase):
    """Coverage for the four landscape/decor items that previously had no
    dedicated Thought at all (stone_path/flower/bench/fountain) -- each gets
    an "about to place" hint (tool equipped, hovering) and an "already
    placed, hovering it" hint, mirroring the existing fence/trap/dog pattern
    one-for-one."""

    def test_stone_path_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "stone_path", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["在這裡鋪一段石板路，也許能讓農場的動線更清楚一點。"])

    def test_stone_path_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "stone_path", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這條石板路讓農場走起來更有規劃感。"])

    def test_flower_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "flower", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["擺一盆花在這裡，能替農場添點生氣，也對繁榮度有幫助。"])

    def test_flower_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "flower", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這盆花替周圍添了點生氣，也貢獻了一些繁榮度。"])

    def test_bench_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "bench", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["放一張長椅在這裡，讓農場多一個可以停下來坐坐的角落。"])

    def test_bench_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "bench", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這張長椅讓農場多了一處可以喘口氣的角落。"])

    def test_fountain_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "fountain", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["立一座風車在這裡，能替農場添點鄉村風景，也對繁榮度有幫助。"])

    def test_fountain_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "fountain", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這座風車讓農場多了一點悠閒的鄉村氣息。"])

    def test_fountain_thoughts_never_say_noquan(self):
        """Internal id "fountain" keeps its display name "風車" (renamed
        from 小型噴泉 in an earlier pass) -- neither Thought for it should
        ever regress back to talking about a "噴泉"."""
        state = new_game()
        place_lines = get_contemplation_lines(state, "decor", "fountain", False, hover_pos=(5, 5))
        self.assertNotIn("噴泉", "".join(place_lines))

        state2 = new_game()
        _skip_beginner_intros(state2)
        state2["money"] = 0
        state2["decor"]["decorations"].append((20, 20, "fountain", 100))
        nearby_lines = get_contemplation_lines(state2, "decor", None, False, hover_pos=(22, 22))
        self.assertNotIn("噴泉", "".join(nearby_lines))

    def test_decor_thought_does_not_leak_into_farm_zone(self):
        """required_map="decor" on all eight new entries -- equipping e.g.
        "flower" while standing in the farm zone (which can't actually build
        decor there per capstone_contract.py's build_decor_ zone check)
        should not surface the decor-specific hint."""
        state = new_game()
        lines = get_contemplation_lines(state, "farm", "flower", False, hover_pos=(5, 5))
        self.assertNotEqual(lines, ["擺一盆花在這裡，能替農場添點生氣，也對繁榮度有幫助。"])


class TestLandscapeExpansionThoughts(unittest.TestCase):
    """Coverage for the 7 landscape-expansion decor items added on top of
    the original 4 (scarecrow/crate/bush/rock/sunflower/pine_tree/big_tree)
    -- same "about to place" / "hovering it, already placed" pairing,
    mirroring TestDecorThoughts one-for-one."""

    def test_scarecrow_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "scarecrow", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["立一個稻草人在這裡，能替農場添點田園氣氛，雖然它不會真的嚇跑什麼。"])

    def test_scarecrow_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "scarecrow", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這個稻草人靜靜站在田邊，替農場增添了一點田園味。"])

    def test_crate_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "crate", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["放一個木箱在這裡，讓農場看起來更有生活感。"])

    def test_crate_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "crate", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這個木箱堆在角落，替農場添了點生活痕跡。"])

    def test_bush_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "bush", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["種一叢灌木在這裡，讓農場的綠意更豐富一些。"])

    def test_bush_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "bush", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這叢灌木讓周圍多了一點自然的綠意。"])

    def test_rock_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "rock", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["放一塊石頭在這裡，替農場增添一點自然的庭院感。"])

    def test_rock_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "rock", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這塊石頭安靜地待在這裡，替庭院增添了一點自然感。"])

    def test_sunflower_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "sunflower", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["種一株向日葵在這裡，鮮豔的花朵能讓農場更有生氣。"])

    def test_sunflower_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "sunflower", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這株向日葵迎著陽光綻放，讓農場看起來更有生氣。"])

    def test_pine_tree_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "pine_tree", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["在這裡種一棵松樹，能讓農場多一點綠蔭與層次感。"])

    def test_pine_tree_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "pine_tree", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這棵松樹替農場添了一片綠蔭，也讓景觀更有層次。"])

    def test_big_tree_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "big_tree", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["在這裡種一棵大樹，會是農場裡相當顯眼的核心景觀。"])

    def test_big_tree_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "big_tree", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這棵大樹枝葉茂密，是農場裡相當醒目的核心景觀。"])

    def test_new_decor_thoughts_do_not_leak_into_farm_zone(self):
        """Same required_map="decor" guard as the original 4 -- spot-check
        one of the 7 new items."""
        state = new_game()
        lines = get_contemplation_lines(state, "farm", "sunflower", False, hover_pos=(5, 5))
        self.assertNotEqual(lines, ["種一株向日葵在這裡，鮮豔的花朵能讓農場更有生氣。"])

    def test_all_seven_ids_have_distinct_place_and_nearby_text(self):
        """No copy/paste collisions across the 14 new entries (7 place + 7
        nearby) -- every string should be unique."""
        from src.thought import THOUGHT_ENTRIES
        new_ids = [
            "action_scarecrow_place", "action_crate_place", "action_bush_place",
            "action_rock_place", "action_sunflower_place", "action_pine_tree_place",
            "action_big_tree_place",
            "info_scarecrow_nearby", "info_crate_nearby", "info_bush_nearby",
            "info_rock_nearby", "info_sunflower_nearby", "info_pine_tree_nearby",
            "info_big_tree_nearby",
        ]
        by_id = {e["id"]: e for e in THOUGHT_ENTRIES}
        for eid in new_ids:
            self.assertIn(eid, by_id, f"missing THOUGHT_ENTRIES id: {eid}")
        texts = [by_id[eid]["text"] for eid in new_ids]
        self.assertEqual(len(texts), len(set(texts)), "duplicate Thought text across new decor entries")


class TestLandscapeExpansionRound2Thoughts(unittest.TestCase):
    """Coverage for the 8 round-2 landscape items (stump/mushroom/
    picnic_basket/woodpile/picnic_blanket/beehive/garden_table/fruit_tree),
    mirroring TestLandscapeExpansionThoughts one-for-one."""

    def test_stump_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "stump", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["在這裡留一段樹墩，能替農場添點原始自然的味道。"])

    def test_stump_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "stump", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這段樹墩透出一點原始自然的味道，也是農場裡小小的休憩點。"])

    def test_mushroom_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "mushroom", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["在這裡種一朵蘑菇，替農場角落添點野趣。"])

    def test_mushroom_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "mushroom", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這朵蘑菇靜靜長在角落，替農場增添了一點野趣。"])

    def test_picnic_basket_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "picnic_basket", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["放一個野餐籃在這裡，讓農場多一點悠閒的生活氣息。"])

    def test_picnic_basket_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "picnic_basket", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這個野餐籃擺在這裡，讓農場多了一點悠閒的生活氣息。"])

    def test_woodpile_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "woodpile", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["在這裡堆一疊柴薪，讓農場更有生活感。"])

    def test_woodpile_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "woodpile", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這疊柴薪堆在這裡，替農場添了點樸實的生活感。"])

    def test_picnic_blanket_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "picnic_blanket", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["鋪一張野餐墊在這裡，適合當作農場裡休息放鬆的角落。"])

    def test_picnic_blanket_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "picnic_blanket", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這張野餐墊鋪在這裡，是農場裡一個適合休息放鬆的角落。"])

    def test_beehive_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "beehive", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["在這裡放一個蜂箱，能替農場增添一點養蜂的田園氣息。"])

    def test_beehive_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "beehive", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這個蜂箱安靜地放在這裡，替農場增添了一點養蜂的田園氣息。"])

    def test_garden_table_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "garden_table", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["放一張庭院桌在這裡，能跟長椅搭配成休息的角落。"])

    def test_garden_table_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "garden_table", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這張庭院桌擺在這裡，是農場裡一個適合坐下來的角落。"])

    def test_fruit_tree_place_hint(self):
        state = new_game()
        lines = get_contemplation_lines(state, "decor", "fruit_tree", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["在這裡種一棵果樹，能替農場增添真正的農家風景。"])

    def test_fruit_tree_nearby_hint(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["decor"]["decorations"].append((20, 20, "fruit_tree", 100))
        lines = get_contemplation_lines(state, "decor", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["這棵果樹結實纍纍，是農場裡最有農家氣息的風景之一。"])

    def test_new_decor_thoughts_do_not_leak_into_farm_zone(self):
        state = new_game()
        lines = get_contemplation_lines(state, "farm", "fruit_tree", False, hover_pos=(5, 5))
        self.assertNotEqual(lines, ["在這裡種一棵果樹，能替農場增添真正的農家風景。"])

    def test_all_eight_ids_have_distinct_place_and_nearby_text(self):
        from src.thought import THOUGHT_ENTRIES
        new_ids = [
            "action_stump_place", "action_mushroom_place", "action_picnic_basket_place",
            "action_woodpile_place", "action_picnic_blanket_place", "action_beehive_place",
            "action_garden_table_place", "action_fruit_tree_place",
            "info_stump_nearby", "info_mushroom_nearby", "info_picnic_basket_nearby",
            "info_woodpile_nearby", "info_picnic_blanket_nearby", "info_beehive_nearby",
            "info_garden_table_nearby", "info_fruit_tree_nearby",
        ]
        by_id = {e["id"]: e for e in THOUGHT_ENTRIES}
        for eid in new_ids:
            self.assertIn(eid, by_id, f"missing THOUGHT_ENTRIES id: {eid}")
        texts = [by_id[eid]["text"] for eid in new_ids]
        self.assertEqual(len(texts), len(set(texts)), "duplicate Thought text across round-2 decor entries")


class TestRegressionAfterDecorThoughts(unittest.TestCase):
    """Confirms the eight new entries didn't shift priority/fallback
    behavior for anything that already worked -- crops, tools, and the
    other two defense items (trap/dog) that weren't already covered by
    TestThoughtScenarios above (only fence was)."""

    def test_trap_place_hint_still_works(self):
        state = new_game()
        lines = get_contemplation_lines(state, "farm", "trap", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["陷阱會對踩到的敵人造成傷害，適合放在必經之路上。"])

    def test_dog_place_hint_still_works(self):
        state = new_game()
        lines = get_contemplation_lines(state, "farm", "dog", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["狗會主動攻擊靠近的敵人，適合放在容易被入侵的地方。"])

    def test_trap_nearby_hint_still_works(self):
        state = new_game()
        _skip_beginner_intros(state)
        state["money"] = 0
        state["farm"]["traps"].append((20, 20))
        lines = get_contemplation_lines(state, "farm", None, False, hover_pos=(22, 22))
        self.assertEqual(lines, ["地刺陷阱會對踩到的敵人造成傷害。"])

    def test_carrot_seed_hint_still_works(self):
        state = new_game()
        state = apply_action(state, "use_hoe_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        lines = get_contemplation_lines(state, "farm", "carrot", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["這塊土地應該可以種下種子。"])

    def test_pumpkin_seed_hint_still_works(self):
        state = new_game()
        state = apply_action(state, "use_hoe_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        lines = get_contemplation_lines(state, "farm", "pumpkin", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["這塊土地應該可以種下種子。"])


class TestThoughtDemotion(unittest.TestCase):
    def test_action_till_demotes_in_priority_once_hoe_is_learned(self):
        state = new_game()
        # Give the player something else Tier-1-actionable to compete with:
        # a sellable crop in inventory (action_sell_crops).
        state["inventory"]["radish"]["normal"] = 1

        # Before "hoe" is learned: hovering tillable ground with the hoe
        # out (priority 10) should still beat "you have crops to sell"
        # (priority 15).
        lines = get_contemplation_lines(state, "farm", "hoe", False, hover_pos=(5, 5))
        self.assertEqual(lines, ["這裡似乎可以開墾成農田。"])

        # Learn "hoe" (till something once), which also happens to leave
        # (5, 5) itself tilled -- hover a different untilled cell instead
        # so the till-hint's *condition* is still true, only its learned
        # status changed.
        state = apply_action(state, "use_hoe_5_5")
        state = apply_action(state, "tick")
        state = apply_action(state, "tick")
        self.assertGreater(len(state["farm"]["farmland"]), 0)

        # Now action_till should be demoted below action_sell_crops.
        lines = get_contemplation_lines(state, "farm", "hoe", False, hover_pos=(8, 8))
        self.assertEqual(lines, ["背包裡有收成了，按 B 打開商店可以賣掉換錢。"])


if __name__ == '__main__':
    unittest.main()
