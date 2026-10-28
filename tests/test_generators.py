"""Независимая проверка генераторов: ответ проверяется подстановкой в ТЕКСТ задания.

Тест не пользуется формулами генератора — он разбирает условие так, как
его прочитал бы ученик, и проверяет ответ перебором или подстановкой.
Это гарантирует, что в ключах нет ошибок.
"""
import math
import random
import re
import unittest
from fractions import Fraction as F

from builder.engine.curriculum import TOPICS
from builder.engine.generators import GENERATORS, generate

SEEDS = range(300)
SUP = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9"}


def to_py(expr: str) -> str:
    s = expr.replace("−", "-").replace("·", "*").replace(":", "/")
    s = re.sub(r"(\d),(\d)", r"\1.\2", s)
    s = re.sub(r"([⁰¹²³⁴⁵⁶⁷⁸⁹]+)", lambda m: "**" + "".join(SUP[c] for c in m.group(1)), s)
    s = re.sub(r"√\(", "sqrt(", s)
    s = re.sub(r"√(\d+)", r"sqrt(\1)", s)
    s = re.sub(r"(\d)\s*([xy(])", r"\1*\2", s)
    s = re.sub(r"\)\s*([xy(])", r")*\1", s)
    s = re.sub(r"([xy])(?=[xy(])", r"\1*", s)
    s = s.replace("^", "**")
    return s


def ev(expr: str, x=None) -> float:
    return eval(to_py(expr), {"sqrt": math.sqrt, "x": x})


def ans(t):
    a = t["answer"]
    return [F(v) for v in a["value"]] if a["kind"] == "set" else F(a["value"])


def tasks(topic):
    for s in SEEDS:
        yield generate(topic, random.Random(s))


class CoverageTests(unittest.TestCase):
    def test_every_topic_has_generator(self):
        self.assertEqual(set(TOPICS), set(GENERATORS))

    def test_answers_and_distractors_differ(self):
        for topic in GENERATORS:
            for t in tasks(topic):
                for d in t["distractors"]:
                    self.assertNotEqual(d["value"], t["answer"]["value"], (topic, t["text"]))

    def test_variety(self):
        for topic in GENERATORS:
            texts = {t["text"] for t in tasks(topic)}
            self.assertGreaterEqual(len(texts), 15, f"{topic}: слишком мало разных заданий")


class IndependentCheckTests(unittest.TestCase):
    def test_arithmetic(self):
        for topic in ("nat_ops", "negatives", "decimals", "powers"):
            for t in tasks(topic):
                expr = t["text"].split("Вычислите:")[1].strip()
                self.assertAlmostEqual(ev(expr), float(ans(t)), places=9, msg=t["text"])

    def test_linear_equation(self):
        for t in tasks("linear_eq"):
            lhs, rhs = t["text"].split(":", 1)[1].split("=")
            x = float(ans(t))
            self.assertAlmostEqual(ev(lhs, x), ev(rhs, x), places=9, msg=t["text"])

    def test_quadratic_roots(self):
        for t in tasks("quadratic"):
            poly = t["text"].split(":", 1)[1].split("=")[0]
            roots = ans(t)
            for r in roots:
                self.assertAlmostEqual(ev(poly, float(r)), 0, places=9, msg=t["text"])
            # других корней нет: проверяем целые точки в широком диапазоне
            others = [x for x in range(-50, 51) if abs(ev(poly, x)) < 1e-9]
            self.assertEqual(sorted(others), sorted(int(r) for r in roots), t["text"])

    def test_rational_equation_excludes_extraneous(self):
        for t in tasks("rational_eq"):
            m = re.search(r"\((.+)\)/\((.+)\) = 0", t["text"])
            num, den = m.group(1), m.group(2)
            sols = [x for x in range(-50, 51) if abs(ev(num, x)) < 1e-9 and abs(ev(den, x)) > 1e-9]
            self.assertEqual(sols, [int(r) for r in ans(t)], t["text"])

    def test_linear_inequality(self):
        for t in tasks("lin_ineq"):
            lhs, rhs = t["text"].split("неравенства ")[1].rstrip(".").split(" > ")
            sols = [x for x in range(-200, 201) if ev(lhs, x) > ev(rhs, x)]
            self.assertEqual(max(sols), ans(t), t["text"])

    def test_quadratic_inequality(self):
        for t in tasks("quad_ineq"):
            m = re.search(r"неравенство (.+) (≤|<) 0", t["text"])
            f = lambda x: ev(m.group(1), x)
            sols = [x for x in range(-100, 101) if (f(x) <= 0 if m.group(2) == "≤" else f(x) < 0)]
            self.assertEqual(len(sols), ans(t), t["text"])

    def test_derivative(self):
        for t in tasks("derivative"):
            m = re.search(r"f\(x\) = (.+) в точке x₀ = (.+)\.", t["text"])
            x0 = float(ev(m.group(2)))
            h = 1e-5
            d = (ev(m.group(1), x0 + h) - ev(m.group(1), x0 - h)) / (2 * h)
            self.assertAlmostEqual(d, float(ans(t)), places=4, msg=t["text"])

    def test_vertex(self):
        for t in tasks("quad_func"):
            poly = t["text"].split("y = ")[1].rstrip(".")
            y = lambda x: ev(poly, x)
            # по трём точкам находим a и b
            a = (y(1) + y(-1) - 2 * y(0)) / 2
            b = (y(1) - y(-1)) / 2
            self.assertAlmostEqual(-b / (2 * a), float(ans(t)), places=9, msg=t["text"])

    def test_vieta(self):
        for t in tasks("vieta"):
            poly = t["text"].split("уравнения ")[1].split(" = 0")[0]
            c = ev(poly, 0)
            p = ev(poly, 1) - 1 - c
            disc = p * p - 4 * c
            x1, x2 = (-p + math.sqrt(disc)) / 2, (-p - math.sqrt(disc)) / 2
            self.assertAlmostEqual(x1 ** 2 + x2 ** 2, float(ans(t)), places=6, msg=t["text"])

    def test_systems(self):
        for t in tasks("systems"):
            eqs = t["text"].split(":", 1)[1].split(". В ответе")[0].split(";")
            coef = []
            for e in eqs:
                lhs, rhs = e.split("=")
                f = lambda x, y, lhs=lhs: eval(to_py(lhs), {"x": x, "y": y})
                c = f(0, 0)
                coef.append((f(1, 0) - c, f(0, 1) - c, ev(rhs) - c))
            (a1, b1, c1), (a2, b2, c2) = coef
            x = (c1 * b2 - c2 * b1) / (a1 * b2 - a2 * b1)
            self.assertAlmostEqual(x, float(ans(t)), places=9, msg=t["text"])

    def test_log_and_exp_equations(self):
        for t in tasks("log_eq"):
            m = re.search(r"log(\S+)\(x \+ (\d+)\) = (\d+)", t["text"])
            base = int("".join("0123456789"["₀₁₂₃₄₅₆₇₈₉".index(c)] for c in m.group(1)))
            self.assertAlmostEqual(math.log(float(ans(t)) + int(m.group(2)), base), int(m.group(3)), msg=t["text"])
        for t in tasks("exp_eq"):
            m = re.search(r"(\d+)\^\(2x − (\d+)\) = (\d+)", t["text"])
            a, mm, rhs = map(int, m.groups())
            self.assertAlmostEqual(a ** (2 * float(ans(t)) - mm), rhs, places=6, msg=t["text"])

    def test_geometry_and_word_problems(self):
        for t in tasks("pythagoras"):
            a, b = map(int, re.findall(r"\d+", t["text"])[:2])
            x = float(ans(t))
            self.assertTrue(math.isclose(x * x, a * a + b * b) or math.isclose(x * x + a * a, b * b) or
                            math.isclose(x * x + b * b, a * a), t["text"])
        for t in tasks("word_problems"):
            nums = [F(n.replace(",", ".")) for n in re.findall(r"\d+(?:,\d+)?", t["text"])]
            if "навстречу" in t["text"]:
                s, v1, v2 = nums[:3]
                self.assertEqual(ans(t) * (v1 + v2), s, t["text"])
            else:
                a, b = nums[:2]
                self.assertEqual(ans(t) * (1 / a + 1 / b), 1, t["text"])


if __name__ == "__main__":
    unittest.main()


class TrigLogTests(unittest.TestCase):
    def test_trig_identity_and_sign(self):
        quarter_signs = {"острый": (1, 1), "(90°; 180°)": (1, -1), "(180°; 270°)": (-1, -1), "(270°; 360°)": (-1, 1)}
        for t in tasks("trig_values"):
            m = re.search(r"Найдите (sin|cos) α, если (sin|cos) α = (−?\d+/\d+)", t["text"])
            given = F(m.group(3).replace("−", "-"))
            a = ans(t)
            self.assertEqual(a * a + given * given, 1, t["text"])
            s_sign, c_sign = next(v for k, v in quarter_signs.items() if k in t["text"])
            want = s_sign if m.group(1) == "sin" else c_sign
            self.assertEqual(1 if a > 0 else -1, want, t["text"])

    def test_logs(self):
        sub = "₀₁₂₃₄₅₆₇₈₉"
        for t in tasks("log"):
            m = re.search(r"log(\S+) (\S+) ([+−]) log\S+ (\S+)$", t["text"])
            base = int("".join(str(sub.index(c)) for c in m.group(1)))
            x, y = float(F(m.group(2).replace(",", "."))), float(F(m.group(4).replace(",", ".")))
            v = math.log(x, base) + (1 if m.group(3) == "+" else -1) * math.log(y, base)
            self.assertAlmostEqual(v, float(ans(t)), places=9, msg=t["text"])


def fr(s):
    return F(s.replace("−", "-").replace(",", "."))


class RemainingTopicsTests(unittest.TestCase):
    def test_expressions_and_alg_fractions(self):
        for t in tasks("expressions"):
            m = re.search(r"выражение (.+) и найдите его значение при x = (\S+)\.", t["text"])
            self.assertAlmostEqual(ev(m.group(1), float(fr(m.group(2)))), float(ans(t)), msg=t["text"])
        for t in tasks("alg_fractions"):
            m = re.search(r"дробь \((.+)\)/\((.+)\) и .+ при x = (\S+)\.", t["text"])
            x = float(fr(m.group(3)))
            self.assertAlmostEqual(ev(m.group(1), x) / ev(m.group(2), x), float(ans(t)), msg=t["text"])

    def test_sfm_and_factoring(self):
        for t in tasks("sfm"):
            expr = re.search(r"выражении (\(.+\)²)", t["text"]).group(1)
            self.assertAlmostEqual((ev(expr, 1) - ev(expr, -1)) / 2, float(ans(t)), msg=t["text"])
        for t in tasks("factoring"):
            if "общий множитель" in t["text"]:
                lhs, rhs = t["text"].split(": ", 1)[1].split(" = ")
                rhs = rhs.split(". Найдите")[0].replace("k·", f"{ans(t)}*")
                for x, y in ((1, 2), (3, -1), (2, 5)):
                    f = lambda e: eval(to_py(e), {"x": x, "y": y})
                    self.assertAlmostEqual(f(lhs), f(rhs), msg=t["text"])
            else:
                poly = re.search(r"множители: (.+) = \(x \+ m\)", t["text"]).group(1)
                m = int(ans(t))
                n = int(ev(poly, 0)) // m
                for x in (-3, 0, 2, 5):
                    self.assertAlmostEqual(ev(poly, x), (x + m) * (x + n), msg=t["text"])
                self.assertGreater(m, n)

    def test_number_sense(self):
        for t in tasks("divisibility"):
            a, b = map(int, re.findall(r"\d+", t["text"])[-2:])
            want = math.lcm(a, b) if "НОК" in t["text"].split("чисел")[0] and "наименьшее" in t["text"] else math.gcd(a, b)
            self.assertEqual(ans(t), want, t["text"])
        for t in tasks("fractions_basic"):
            p, q = map(int, re.search(r"(\d+)/(\d+)", t["text"]).groups())
            self.assertEqual(ans(t), F(p, q), t["text"])
            self.assertEqual(math.gcd(ans(t).numerator, ans(t).denominator), 1)
        for t in tasks("fractions_ops"):
            expr = t["text"].split("Вычислите: ")[1].split(". Ответ")[0]
            a, op, b = re.match(r"(\d+/\d+) ([+:]) (\d+/\d+)", expr).groups()
            self.assertEqual(ans(t), F(a) + F(b) if op == "+" else F(a) / F(b), t["text"])
        for t in tasks("proportion"):
            a, b, c = map(int, re.search(r"x/(\d+) = (\d+)/(\d+)", t["text"]).groups())
            self.assertEqual(ans(t) * c, a * b, t["text"])
        for t in tasks("sqrt"):
            self.assertAlmostEqual(ev(t["text"].split("Вычислите: ")[1]), float(ans(t)), msg=t["text"])

    def test_percent_probability_areas(self):
        for t in tasks("percent"):
            nums = [int(x) for x in re.findall(r"\d+", t["text"])]
            if "До снижения" in t["text"] or "до снижения" in t["text"]:
                p, new = nums[0], nums[1]
                self.assertEqual(ans(t) * (100 - p), new * 100, t["text"])
            else:
                base, p = nums[0], nums[1]
                k = 100 + p if "повысилась" in t["text"] else 100 - p
                self.assertEqual(ans(t) * 100, base * k, t["text"])
        for t in tasks("probability"):
            r, b, g = map(int, re.findall(r"(\d+) (?:красных|синих|зелёных)", t["text"]))
            self.assertEqual(ans(t), F(b, r + b + g), t["text"])
        for t in tasks("areas"):
            nums = [int(x) for x in re.findall(r"\d+", t["text"])]
            want = F((nums[0] + nums[1]) * nums[2], 2) if "трапеции" in t["text"] else F(nums[0] * nums[1], 2)
            self.assertEqual(ans(t), want, t["text"])

    def test_progressions_and_linear_function(self):
        for t in tasks("progressions"):
            m = re.search(r"[ab]₁ = (\S+), [dq] = (\S+)\. Найдите [ab](\S+)\.", t["text"])
            first, step = fr(m.group(1)), fr(m.group(2))
            n = int("".join(str("₀₁₂₃₄₅₆₇₈₉".index(c)) for c in m.group(3)))
            want = first + (n - 1) * step if "Арифметическая" in t["text"] else first * step ** (n - 1)
            self.assertEqual(ans(t), want, t["text"])
        for t in tasks("linear_func"):
            (x1, y1), (x2, y2) = [(fr(a), fr(b)) for a, b in re.findall(r"\((\S+); (\S+)\)", t["text"])]
            self.assertEqual(ans(t), (y2 - y1) / (x2 - x1), t["text"])
