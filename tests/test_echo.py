"""Тесты «Эха»: озвучка формул, банк заданий и совпадение проверки ответов в JS и Python."""
import json
import random
import re
import shutil
import subprocess
import unittest
from fractions import Fraction as F
from pathlib import Path

from builder.build_bank import build
from builder.engine.checker import check as py_check
from builder.speech import answer_to_speech, to_speech

ROOT = Path(__file__).resolve().parents[1]


class SpeechTests(unittest.TestCase):
    CASES = {
        "x² − 5x + 6 = 0": "икс в квадрате минус 5 икс плюс 6 равно 0",
        "Сократите дробь 18/24.": "Сократите дробь: числитель 18, знаменатель 24.",
        "Вычислите: √(9 + 16)": "Вычислите: квадратный корень из выражения 9 плюс 16, конец корня",
        "Вычислите: √3 · √48": "Вычислите: квадратный корень из 3 умножить на квадратный корень из 48",
        "Вычислите: 2⁶ · 2³ : 2⁵": "Вычислите: 2 в степени 6 умножить на 2 в кубе разделить на 2 в степени 5",
        "Вычислите: 2,4 · 0,15": "Вычислите: 2 запятая 4 умножить на 0 запятая 15",
        "x₁ и x₂ — корни": "икс первое и икс второе — корни",
        "Найдите a₁₂.": "Найдите а двенадцатое.",
        "Прямая y = kx + b проходит через точки (0; 4) и (2; 8).":
            "Прямая игрек равно ка икс плюс бэ проходит через точки (икс равно 0, игрек равно 4) и (икс равно 2, игрек равно 8).",
        "(x² + 7x + 10)/(x + 2)": "дробь: в числителе икс в квадрате плюс 7 икс плюс 10, в знаменателе икс плюс 2, конец дроби",
        "−7 − (−12)": "минус 7 минус скобка открывается, минус 12, скобка закрывается",
        "x − 8 > 9x − 3": "икс минус 8 больше 9 икс минус 3",
        "x² + x − 12 ≤ 0": "икс в квадрате плюс икс минус 12 меньше или равно 0",
        "Найдите наибольший общий делитель (НОД) чисел 12 и 15.": "Найдите наибольший общий делитель (НОД) чисел 12 и 15.",
        "скоростями 55 км/ч": "скоростями 55 километров в час",
    }

    def test_cases(self):
        for src, want in self.CASES.items():
            self.assertEqual(to_speech(src), want, src)

    def test_answers(self):
        self.assertEqual(answer_to_speech("−1; 0"), "минус 1 и 0")
        self.assertEqual(answer_to_speech("3/4"), "дробь: числитель 3, знаменатель 4")
        self.assertEqual(answer_to_speech("нет корней"), "нет корней")


class BankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bank = build()

    def test_size_and_uniqueness(self):
        tasks = self.bank["tasks"]
        self.assertGreater(len(tasks), 1200)
        self.assertEqual(len({t["text"] for t in tasks}), len(tasks))
        self.assertEqual(len({t["id"] for t in tasks}), len(tasks))
        for topic, meta in self.bank["topics"].items():
            self.assertGreaterEqual(meta["count"], 20, topic)

    def test_everything_is_spoken(self):
        """В озвучке не должно остаться символов, которые синтезатор прочитает неверно или пропустит."""
        for t in self.bank["tasks"]:
            for field in ("speech", "solution_speech", "key_speech"):
                s = t[field]
                self.assertIsNone(re.search(r"[²³⁰¹⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉√/·−=<>≤≥^]", s), f"{field}: {s}")
                self.assertIsNone(re.search(r"\b[a-z]\b", s), f"латинская буква в {field}: {s}")
                self.assertIsNone(re.search(r"\d[a-zа-я]", s), f"{field}: {s}")

    def test_keys_are_correct(self):
        for t in self.bank["tasks"]:
            self.assertTrue(py_check(t | {"strict_simplified": t["strict"]}, t["key"])["correct"], t["text"])


@unittest.skipUnless(shutil.which("node"), "нужен Node.js")
class ParityTests(unittest.TestCase):
    """JS-проверка в браузере должна давать тот же результат, что и протестированная Python-версия."""

    def test_js_matches_python(self):
        bank = build()
        rng = random.Random(1)
        cases = []
        for t in rng.sample(bank["tasks"], 400):
            inputs = [t["key"], t["key"].replace("−", "-"), "", "абв", "нет", "12345", "0"]
            inputs += [d["value"] if isinstance(d["value"], str) else "; ".join(d["value"]) for d in t["distractors"]]
            if t["answer"]["kind"] == "number":
                v = F(t["answer"]["value"])
                inputs += [str(-v), str(v * 10), str(v + 1), f"{v.numerator * 2}/{v.denominator * 2}",
                           str(float(v)).replace(".", ","), f"Ответ: {t['key']}"]
            else:
                vals = t["answer"]["value"]
                inputs += [vals[0] if vals else "1", "; ".join(vals + ["99"]), "; ".join(str(-F(x)) for x in vals) or "1",
                           ", ".join(vals) or "нет", " и ".join(vals) or "нет"]
            for raw in inputs:
                py = py_check(t | {"strict_simplified": t["strict"]}, raw)
                cases.append({"task": t, "raw": raw, "want": [py["correct"], py["error"]]})
        script = ROOT / "docs" / "checker.js"
        js = ("const {check}=require(" + json.dumps(str(script)) + ");"
              "const cases=JSON.parse(require('fs').readFileSync(0,'utf8'));"
              "const out=cases.map(c=>{const r=check(c.task,c.raw,{});return [r.correct,r.error];});"
              "process.stdout.write(JSON.stringify(out));")
        res = subprocess.run(["node", "-e", js], input=json.dumps(cases), capture_output=True, text=True, timeout=60)
        self.assertEqual(res.returncode, 0, res.stderr)
        got = json.loads(res.stdout)
        mismatches = [(c["task"]["text"], c["raw"], c["want"], g) for c, g in zip(cases, got) if list(c["want"]) != g]
        self.assertFalse(mismatches, f"{len(mismatches)} расхождений, например: {mismatches[:5]}")
        self.assertGreater(len(cases), 4000)


if __name__ == "__main__":
    unittest.main()
