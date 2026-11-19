import json, os, sys, unittest
HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import chartcheck as cc


def card(**kw):
    c = {"kind": "line", "title": "Revenue rose 50% from 2020 to 2024",
         "y": {"unit": "$m", "min": 0},
         "series": [{"name": "Revenue", "points": [["2020", 10], ["2021", 11], ["2022", 12], ["2023", 13], ["2024", 15]]}],
         "labels": "direct", "gridlines": "light", "source": "Annual reports",
         "alt": "Revenue grew from $10m in 2020 to $15m in 2024."}
    c.update(kw)
    return c


def codes(r):
    return {f["code"].split()[0] for f in r["findings"]}


class Claims(unittest.TestCase):
    def test_change_holds_and_ships(self):
        r = cc.run(card())
        self.assertEqual(r["claims"][0]["verdict"], "HOLDS")
        self.assertEqual(r["gate"], "SHIP")

    def test_overstated_change_is_stretch(self):
        r = cc.run(card(title="Revenue rose 80% from 2020 to 2024"))
        self.assertEqual(r["claims"][0]["verdict"], "STRETCH")
        self.assertEqual(r["gate"], "FIX")

    def test_wrong_direction_holds_the_chart(self):
        r = cc.run(card(title="Revenue fell 10% from 2020 to 2024"))
        self.assertEqual(r["claims"][0]["verdict"], "WRONG")
        self.assertEqual(r["gate"], "HOLD")

    def test_multiplier_words(self):
        r = cc.run(card(title="Revenue doubled since 2020"))
        self.assertEqual(r["claims"][0]["verdict"], "STRETCH")  # x1.5 is not x2
        r = cc.run(card(title="收入翻倍", series=[{"name": "收入", "points": [["2020", 5], ["2024", 10.2]]}]))
        self.assertEqual(r["claims"][0]["verdict"], "HOLDS")

    def test_window_missing_is_unchecked(self):
        r = cc.run(card(title="Revenue rose 50% since 2015"))
        self.assertEqual(r["claims"][0]["verdict"], "UNCHECKED")

    def test_ambiguous_series(self):
        two = [{"name": "North", "points": [["2020", 1], ["2021", 2]]}, {"name": "South", "points": [["2020", 2], ["2021", 1]]}]
        r = cc.run(card(title="Sales doubled", series=two, alt="Two lines, North 1 to 2, South 2 to 1."))
        self.assertEqual(r["claims"][0]["verdict"], "UNCHECKED")
        r = cc.run(card(title="North doubled", series=two, alt="North 1 to 2, South 2 to 1."))
        self.assertEqual(r["claims"][0]["verdict"], "HOLDS")

    def test_record_needs_latest_max(self):
        pts = [["2019", 5], ["2020", 9], ["2021", 7]]
        r = cc.run(card(title="Highest ever", series=[{"name": "A", "points": pts}], alt="A peaked at 9 in 2020."))
        self.assertEqual(r["claims"][0]["verdict"], "WRONG")

    def test_percent_axis_points_vs_percent(self):
        c = card(title="Share rose 10%", y={"unit": "%", "min": 0},
                 series=[{"name": "Share", "points": [["2020", 20], ["2024", 30]]}], alt="Share went from 20% to 30%.")
        r = cc.run(c)
        self.assertEqual(r["claims"][0]["verdict"], "HOLDS")
        self.assertIn("C13", codes(r))
        r = cc.run(dict(c, title="Share rose 10 percentage points"))
        self.assertNotIn("C13", codes(r))

    def test_chosen_start(self):
        pts = [["2018", 20], ["2019", 12], ["2020", 10], ["2021", 14], ["2022", 20]]
        r = cc.run(card(title="Users doubled since 2020", series=[{"name": "Users", "points": pts}], alt="Users 20, 12, 10, 14, 20."))
        self.assertIn("C14", codes(r))


class Lint(unittest.TestCase):
    def test_cut_baseline_on_bars_holds(self):
        r = cc.run(card(kind="bar", y={"unit": "$m", "min": 8}))
        self.assertIn("C10", codes(r)); self.assertEqual(r["gate"], "HOLD")

    def test_cut_baseline_ok_on_lines(self):
        r = cc.run(card(y={"unit": "$m", "min": 8}))
        self.assertNotIn("C10", codes(r))

    def test_names_the_chart_and_reading_instructions(self):
        r = cc.run(card(title="Line chart of revenue", subtitle="Hover each point for details"))
        self.assertTrue({"C02", "C04"} <= codes(r))

    def test_missing_unit_source_alt(self):
        r = cc.run(card(y={"unit": ""}, source="", alt=""))
        self.assertTrue({"C08", "C09", "C16"} <= codes(r))

    def test_legend_twin_axes_thin_trend(self):
        two = [{"name": "A", "points": [["2023", 1], ["2024", 3]]}, {"name": "B", "points": [["2023", 2], ["2024", 2]]}]
        r = cc.run(card(title="A surged past B", series=two, labels="legend", second_axis=True, alt="A 1 to 3, B flat at 2."))
        self.assertTrue({"C07", "C11", "C15"} <= codes(r))

    def test_pie_crowd(self):
        p = [{"name": "s", "points": [[str(i), 10] for i in range(7)]}]
        r = cc.run(card(kind="pie", title="Seven teams split the budget evenly", y={"unit": "%"}, series=p, alt="Seven slices of 10%."))
        self.assertIn("C12", codes(r)); self.assertEqual(r["gate"], "HOLD")

    def test_examples(self):
        ex = os.path.join(HERE, "..", "examples")
        got = {}
        for n in os.listdir(ex):
            if n.endswith(".json"):
                with open(os.path.join(ex, n), encoding="utf-8") as fh:
                    got[n] = cc.run(json.load(fh))["gate"]
        self.assertEqual(got, {"before.json": "HOLD", "after.json": "SHIP", "zh-share.json": "FIX"})

    def test_blank_card_is_valid_json(self):
        self.assertIn("series", json.loads(json.dumps(cc.BLANK)))


if __name__ == "__main__":
    unittest.main()
