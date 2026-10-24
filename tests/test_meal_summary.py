import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("meal_summary", ROOT / "scripts" / "meal_summary.py")
meal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(meal)


def item(name="麦香鸡", quantity=1, energy=100, unit="kcal", spec="1个", is_burger=True):
    return {"name": name, "spec": spec, "quantity": quantity, "is_burger": is_burger,
            "nutrition": None if energy is None else {"energy": energy, "unit": unit, "serving": spec}}


def selection(items, price="24.00"):
    return {"label": "当前选择", "items": items,
            "quote": None if price is None else {"source": "calculate-price", "total_cny": price,
                                                 "queried_at": "2026-10-24T15:00:00+08:00"}}


def report(data):
    return meal.render_report({"mode": "demo", "store": "测试门店", "budget_cny": "25", "selections": [data]})


class MealSummaryTests(unittest.TestCase):
    def test_kj_conversion_and_selected_quantities(self):
        result = meal.summarize_selection(selection([
            item(quantity=2, energy="836.8", unit="kJ"),
            item(name="饮品", energy=100, is_burger=False),
        ]))
        self.assertEqual(result["known_kcal"], 500)
        self.assertEqual(result["items"][0]["per_kcal"], 200)
        self.assertEqual(result["items"][0]["total_kcal"], 400)

    def test_round_only_after_adding_original_values(self):
        result = meal.summarize_selection(selection([item(energy="0.49"), item(energy="0.49")]))
        self.assertEqual(result["known_kcal"], 1)
        self.assertEqual(result["items"][0]["per_kcal"], 0)

    def test_half_up(self):
        self.assertEqual(meal.summarize_selection(selection([item(energy="100.5")]))["known_kcal"], 101)

    def test_partial_nutrition_is_not_a_complete_meal_total(self):
        data = selection([item(energy=200), item(name="新品小食", energy=None, is_burger=False)])
        result = meal.summarize_selection(data)
        self.assertEqual(result["known_kcal"], 200)
        self.assertEqual(len(result["missing"]), 1)
        output = report(data)
        self.assertIn("已知热量合计：200 kcal", output)
        self.assertNotIn("整餐总热量", output)
        self.assertIn("新品小食", output)

    def test_all_missing_and_genuine_zero_are_different(self):
        missing = meal.summarize_selection(selection([item(energy=None)]))
        zero = meal.summarize_selection(selection([item(energy=0)]))
        self.assertTrue(missing["missing"])
        self.assertEqual(zero["missing"], [])

    def test_nutrition_size_mismatch_is_not_extrapolated(self):
        drink = item(name="饮品", spec="中杯", energy=100, is_burger=False)
        drink["nutrition"]["serving"] = "小杯"
        result = meal.summarize_selection(selection([drink]))
        self.assertIsNone(result["items"][0]["per_kcal"])
        self.assertTrue(result["missing"])

    def test_three_grade_groups_and_known_aliases(self):
        for name, level in [("麦香鸡", 1), ("原味板烧鸡腿堡", 2), ("板烧鸡腿堡", 2),
                            ("培根安格斯厚牛堡", 3), ("安格斯MAX厚牛芝士堡", 3)]:
            with self.subTest(name=name):
                grade = meal.grade_for(name)
                self.assertEqual(grade["level"], level)
                self.assertTrue(grade["source_url"].startswith("https://www.mcdonalds.com.cn/"))
                self.assertEqual(grade["checked_on"], "2026-10-24")

    def test_new_products_and_bundle_names_do_not_inherit_grade(self):
        for name in ["高级厚牛堡", "麦香鸡套餐", "板烧鸡腿堡双人餐", "安格斯风味鸡腿堡", "巨无霸"]:
            with self.subTest(name=name):
                self.assertIsNone(meal.grade_for(name))

    def test_non_burger_is_not_graded(self):
        result = meal.summarize_selection(selection([item(is_burger=False)]))
        self.assertIsNone(result["items"][0]["grade"])

    def test_replacement_and_quantity_are_recomputed(self):
        original = selection([item(name="板烧鸡腿堡", energy=400),
                              item(name="饮品", energy=100, is_burger=False)])
        changed = copy.deepcopy(original)
        changed["items"][0] = item(name="麦香鸡", quantity=2, energy=350)
        changed["items"][1] = item(name="饮品", energy=0, is_burger=False)
        self.assertEqual(meal.summarize_selection(original)["known_kcal"], 500)
        new_result = meal.summarize_selection(changed)
        self.assertEqual(new_result["known_kcal"], 700)
        self.assertEqual(new_result["items"][0]["grade"]["level"], 1)

    def test_selections_are_summed_separately(self):
        output = meal.render_report({"mode": "demo", "store": "测试门店", "selections": [
            {**selection([item(energy=200)]), "label": "主推"},
            {**selection([item(energy=350)]), "label": "备选"},
        ]})
        self.assertIn("整餐总热量：200 kcal", output)
        self.assertIn("整餐总热量：350 kcal", output)
        self.assertNotIn("550 kcal", output)

    def test_pending_quote_does_not_invent_price(self):
        output = report(selection([item()], price=None))
        self.assertIn("待核价", output)
        self.assertNotIn("当前核价", output)

    def test_over_budget_is_explicit(self):
        output = report(selection([item()], price="26.50"))
        self.assertIn("超预算 ¥1.50", output)
        self.assertIn("不作为满足预算的推荐", output)

    def test_invalid_quantities_and_energies_are_rejected(self):
        for quantity in [0, -1, 1.5, True]:
            with self.subTest(quantity=quantity), self.assertRaises(ValueError):
                meal.summarize_selection(selection([item(quantity=quantity)]))
        for energy in [-1, "NaN", "Infinity", True]:
            with self.subTest(energy=energy), self.assertRaises(ValueError):
                meal.summarize_selection(selection([item(energy=energy)]))

    def test_unknown_units_and_non_mcp_quote_sources_are_rejected(self):
        with self.assertRaises(ValueError):
            meal.summarize_selection(selection([item(unit="cal")]))
        data = selection([item()])
        data["quote"]["source"] = "估计"
        with self.assertRaises(ValueError):
            meal.summarize_selection(data)

    def test_actual_mcp_snapshot_prices_nutrition_and_grade_matching(self):
        data = json.loads((ROOT / "examples" / "live-2026-10-24.json").read_text(encoding="utf-8"))
        summaries = [meal.summarize_selection(value, data["budget_cny"]) for value in data["selections"]]
        self.assertEqual([row["known_kcal"] for row in summaries[:5]], [369, 391, 516, 738, 696])
        self.assertEqual([str(row["price"]) for row in summaries[:5]], ["13.90", "23.50", "13.90", "27.80", "31.50"])
        self.assertEqual([row["items"][0]["grade"]["level"] for row in summaries[:5]], [1, 2, 1, 1, 3])
        self.assertEqual(str(summaries[3]["over_budget"]), "2.80")
        self.assertEqual(str(summaries[4]["over_budget"]), "6.50")
        self.assertIsNone(summaries[5]["price"])
        self.assertIsNone(summaries[5]["items"][0]["grade"])
        self.assertTrue(summaries[5]["missing"])


if __name__ == "__main__":
    unittest.main()
