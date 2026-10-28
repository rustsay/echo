"""Параметрические генераторы заданий.

Задания создаёт не нейросеть, а код: числа подбираются случайно, а ответ
ВЫЧИСЛЯЕТСЯ, поэтому он гарантированно верный (LLM регулярно ошибаются в
ответах к сгенерированным задачам). Каждый вариант уникален.

Кроме ответа, генератор возвращает «дистракторы» — ответы, к которым
приводит конкретная типичная ошибка. Если ответ ученика совпал с
дистрактором, мы знаем не только что он ошибся, но и КАК.
"""
from __future__ import annotations

import math
import random
import re
from fractions import Fraction as F
from typing import Callable

GENERATORS: dict[str, Callable[[random.Random], dict]] = {}

SUP = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")
SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def gen(topic: str):
    def deco(fn):
        GENERATORS[topic] = fn
        return fn
    return deco


# ---------------------------------------------------------------- форматирование

def num(x, decimal: bool = False) -> str:
    """Число для текста задания: −3, 3/4, 0,75."""
    x = F(x)
    sign = "−" if x < 0 else ""
    x = abs(x)
    if x.denominator == 1:
        return f"{sign}{x.numerator}"
    if _terminating(x) and x.denominator <= 10_000:
        s = f"{float(x):.6f}".rstrip("0").rstrip(".").replace(".", ",")
        return f"{sign}{s}"
    return f"{sign}{x.numerator}/{x.denominator}"


def _terminating(x: F) -> bool:
    d = x.denominator
    for p in (2, 5):
        while d % p == 0:
            d //= p
    return d == 1


def par(x) -> str:
    """Отрицательное число в скобках: (−3)."""
    s = num(x)
    return f"({s})" if F(x) < 0 else s


def term(coef, var: str = "x", first: bool = False) -> str:
    """Слагаемое с коэффициентом: +3x, −x, 5."""
    coef = F(coef)
    if coef == 0:
        return ""
    sign = "−" if coef < 0 else ("" if first else "+")
    a = abs(coef)
    body = ("" if (a == 1 and var) else num(a)) + var
    if first:
        return f"{sign}{body}"
    return f" {sign} {body}"


def poly(*coefs_vars) -> str:
    """poly((1,'x²'), (-5,'x'), (6,'')) → 'x² − 5x + 6'."""
    parts, first = [], True
    for c, v in coefs_vars:
        t = term(c, v, first)
        if t:
            parts.append(t)
            first = False
    return "".join(parts) or "0"


_ASCII_MINUS = re.compile(r"(^|[\s(=;:,·/^])-(?=\d)")


def task(text: str, answer, kind: str = "number", distractors=None, solution: str = "",
         answer_format: str = "", strict_simplified: bool = False) -> dict:
    # единый вид минуса «−» в тексте и решении
    text, solution = _ASCII_MINUS.sub(r"\1−", text), _ASCII_MINUS.sub(r"\1−", solution)
    if kind == "set":
        ans = sorted({F(a) for a in answer})
        value = [str(a) for a in ans]
    else:
        value = str(F(answer))
    dis = []
    for v, code in (distractors or []):
        if kind == "set":
            dv = sorted({F(a) for a in v})
            if dv != sorted(F(a) for a in value):
                dis.append({"value": [str(a) for a in dv], "error": code})
        else:
            if F(v) != F(answer):
                dis.append({"value": str(F(v)), "error": code})
    return {"text": text, "answer": {"kind": kind, "value": value}, "distractors": dis,
            "solution": solution, "answer_format": answer_format, "strict_simplified": strict_simplified}


def nz(rng: random.Random, lo: int, hi: int, exclude=(0,)) -> int:
    while True:
        v = rng.randint(lo, hi)
        if v not in exclude:
            return v


# ---------------------------------------------------------------- 5 класс

@gen("nat_ops")
def _(rng):
    a, b, c, d = rng.randint(20, 90), rng.randint(2, 9), rng.randint(3, 9), rng.randint(2, 30)
    a = max(a, b * c + 5)
    ans = a - b * c + d
    wrong = (a - b) * c + d
    return task(f"Вычислите: {a} − {b} · {c} + {d}", ans, distractors=[(wrong, "order_of_operations")],
                solution=f"Сначала умножение: {b}·{c} = {b * c}; {a} − {b * c} + {d} = {ans}")


@gen("divisibility")
def _(rng):
    g = rng.choice([2, 3, 4, 5, 6])
    m, n = rng.choice([(2, 3), (3, 4), (2, 5), (3, 5), (4, 5), (5, 6), (3, 7)])
    a, b = g * m, g * n
    if rng.random() < 0.5:
        ans = a * b // math.gcd(a, b)
        return task(f"Найдите наименьшее общее кратное (НОК) чисел {a} и {b}.", ans,
                    distractors=[(a * b, "lcm_product"), (g, "gcd_lcm_confused")],
                    solution=f"{a} = {g}·{m}, {b} = {g}·{n}; НОК = {g}·{m}·{n} = {ans}")
    return task(f"Найдите наибольший общий делитель (НОД) чисел {a} и {b}.", g,
                distractors=[(a * b // g, "gcd_lcm_confused")],
                solution=f"{a} = {g}·{m}, {b} = {g}·{n}; НОД = {g}")


@gen("fractions_basic")
def _(rng):
    p, q = rng.choice([(1, 2), (2, 3), (3, 4), (2, 5), (3, 5), (4, 7), (5, 6), (3, 8), (5, 9)])
    k = rng.choice([4, 6, 8, 9, 12])
    half = k // 2 if k % 2 == 0 else k
    return task(f"Сократите дробь {p * k}/{q * k}. Ответ запишите несократимой дробью.", F(p, q),
                answer_format="дробь вида a/b", strict_simplified=True,
                distractors=[(F(p * half, q * half), "not_simplified")] if half != k else [],
                solution=f"НОД({p * k}, {q * k}) = {k}; {p * k}/{q * k} = {p}/{q}")


@gen("decimals")
def _(rng):
    a = F(rng.randint(12, 49), 10)
    b = F(rng.randint(11, 35), 100)
    c = F(rng.randint(101, 499), 100)
    ans = a * b + c
    return task(f"Вычислите: {num(a)} · {num(b)} + {num(c)}", ans,
                distractors=[(a * b * 10 + c, "decimal_point"), (a * b / 10 + c, "decimal_point")],
                solution=f"{num(a)}·{num(b)} = {num(a * b)}; + {num(c)} = {num(ans)}")


# ---------------------------------------------------------------- 6 класс

@gen("fractions_ops")
def _(rng):
    while True:
        a, b, c, d = rng.randint(1, 5), rng.randint(2, 9), rng.randint(1, 5), rng.randint(2, 9)
        if b != d and a < b and c < d and math.gcd(a, b) == 1 and math.gcd(c, d) == 1:
            break
    if rng.random() < 0.5:
        ans = F(a, b) + F(c, d)
        return task(f"Вычислите: {a}/{b} + {c}/{d}. Ответ запишите несократимой дробью.", ans,
                    answer_format="дробь вида a/b",
                    distractors=[(F(a + c, b + d), "add_num_den"), (F(a + c, b * d), "common_denominator")],
                    solution=f"Общий знаменатель {b * d // math.gcd(b, d)}: ответ {num(ans)}")
    ans = F(a, b) / F(c, d)
    return task(f"Вычислите: {a}/{b} : {c}/{d}. Ответ запишите несократимой дробью.", ans,
                answer_format="дробь вида a/b",
                distractors=[(F(a, b) * F(c, d), "division_no_flip")],
                solution=f"{a}/{b} · {d}/{c} = {num(ans)}")


@gen("negatives")
def _(rng):
    a, b, c, d = rng.randint(3, 15), rng.randint(5, 20), rng.randint(2, 9), rng.randint(2, 6)
    ans = -a - (-b) + (-c) * d
    return task(f"Вычислите: −{a} − (−{b}) + (−{c}) · {d}", ans,
                distractors=[(-a - b - c * d, "double_negative"), (-ans, "sign")],
                solution=f"−{a} + {b} − {c * d} = {num(ans)}")


@gen("percent")
def _(rng):
    p = rng.choice([10, 20, 25, 40, 50])
    base = rng.choice([400, 600, 800, 1200, 1500, 2000, 2400])
    if rng.random() < 0.5:
        up = rng.random() < 0.5
        ans = base * (100 + p) // 100 if up else base * (100 - p) // 100
        verb = "повысилась" if up else "снизилась"
        return task(f"Товар стоил {base} рублей. Цена {verb} на {p}%. Сколько рублей стоит товар теперь?", ans,
                    distractors=[(base * p // 100, "percent_part_only")],
                    solution=f"{p}% от {base} = {base * p // 100}; ответ {ans}")
    new = base * (100 - p) // 100
    return task(f"После снижения цены на {p}% товар стоит {new} рублей. Сколько рублей он стоил до снижения?", base,
                distractors=[(new * (100 + p) // 100, "percent_wrong_base")],
                solution=f"{new} — это {100 - p}% от исходной цены: {new} : {num(F(100 - p, 100))} = {base}")


@gen("proportion")
def _(rng):
    b, c = rng.choice([(2, 3), (3, 4), (4, 5), (2, 5), (3, 7), (5, 6)])
    # x/a = b/c ⇒ x = a·b/c; подбираем a кратным c, чтобы ответ был целым
    a = c * rng.randint(2, 6)
    x = F(a * b, c)
    return task(f"Решите пропорцию: x/{a} = {b}/{c}", x,
                distractors=[(F(a * c, b), "proportion_rule")],
                solution=f"x = {a}·{b}/{c} = {num(x)}")


# ---------------------------------------------------------------- 7 класс

@gen("expressions")
def _(rng):
    a, b, c, d, k = rng.randint(2, 6), rng.randint(1, 9), rng.randint(2, 6), rng.randint(1, 9), rng.randint(-5, 5)
    ans = a * (k + b) - c * (k - d)
    wrong = a * (k + b) - c * k - c * d
    return task(f"Упростите выражение {a}(x + {b}) − {c}(x − {d}) и найдите его значение при x = {num(k)}.", ans,
                distractors=[(wrong, "minus_before_bracket")],
                solution=f"{a}x + {a * b} − {c}x + {c * d} = {poly((a - c, 'x'), (a * b + c * d, ''))}; при x = {num(k)}: {ans}")


@gen("powers")
def _(rng):
    a = rng.choice([2, 3, 5])
    m, n = rng.randint(2, 6), rng.randint(2, 5)
    k = m + n - rng.randint(1, 3) if a != 2 else m + n - rng.randint(1, 4)
    ans = F(a) ** (m + n - k)
    wrong = F(a) ** (m * n - k)
    return task(f"Вычислите: {a}{str(m).translate(SUP)} · {a}{str(n).translate(SUP)} : {a}{str(k).translate(SUP)}", ans,
                distractors=[(wrong, "powers_multiply_exponents")],
                solution=f"{a}^({m}+{n}−{k}) = {a}^{m + n - k} = {num(ans)}")


@gen("linear_eq")
def _(rng):
    while True:
        x0 = rng.randint(-6, 8)
        a, b, c, d = rng.randint(2, 7), rng.randint(1, 6), rng.randint(-9, 9), rng.randint(1, 9)
        if a != d:
            break
    e = a * (x0 - b) + c - d * x0
    wrong = F(e + b - c, a - d)
    return task(f"Решите уравнение: {a}(x − {b}){term(c, '')} = {term(d, 'x', True)}{term(e, '')}", x0,
                distractors=[(wrong, "bracket_partial"), (-x0, "sign")],
                solution=f"{a}x − {a * b}{term(c, '')} = {term(d, 'x', True)}{term(e, '')} ⇒ {term(a - d, 'x', True)} = {num(e + a * b - c)} ⇒ x = {num(x0)}")


@gen("linear_func")
def _(rng):
    k = rng.choice([-3, -2, -1, 2, 3, 4, F(1, 2), F(-1, 2)])
    b = rng.randint(-5, 5)
    x1 = rng.randint(-4, 2)
    x2 = x1 + rng.choice([2, 4])
    y1, y2 = k * x1 + b, k * x2 + b
    return task(f"Прямая y = kx + b проходит через точки ({num(x1)}; {num(y1)}) и ({num(x2)}; {num(y2)}). Найдите k.", k,
                distractors=[(F(x2 - x1) / (y2 - y1), "slope_inverted"), (-k, "sign")],
                solution=f"k = ({num(y2)} − {par(y1)})/({num(x2)} − {par(x1)}) = {num(k)}")


@gen("sfm")
def _(rng):
    a, b = rng.randint(2, 7), rng.randint(1, 9)
    return task(f"Раскройте скобки в выражении ({a}x + {b})². Найдите коэффициент при x.", 2 * a * b,
                distractors=[(a * b, "sfm_double_product"), (0, "sfm_square_sum")],
                solution=f"({a}x + {b})² = {a * a}x² + {2 * a * b}x + {b * b}")


@gen("factoring")
def _(rng):
    if rng.random() < 0.4:
        k = rng.choice([2, 3, 4, 5, 6])
        a, b = rng.choice([(2, 3), (3, 2), (1, 4), (3, 4), (2, 5), (5, 3)])
        return task(f"Вынесите общий множитель за скобки: {k * a}x²y − {k * b}xy² = k·xy({term(a, 'x', True)} − {term(b, 'y', True)}). "
                    f"Найдите k.", k,
                    distractors=[(k * a, "factor_partial"), (k * a * k * b, "factor_partial")],
                    solution=f"Общий множитель коэффициентов НОД({k * a}, {k * b}) = {k}, общая буквенная часть xy; k = {k}")
    while True:
        m, n = rng.randint(-7, 7), rng.randint(-7, 7)
        if m > n and m != 0 and n != 0 and m != -n:
            break
    return task(f"Разложите на множители: x²{term(m + n, 'x')}{term(m * n, '')} = (x + m)(x + n), где m > n. Найдите m.", m,
                distractors=[(-n, "sign"), (n, "factor_order")],
                solution=f"Корни трёхчлена {-m} и {-n}, поэтому x²{term(m + n, 'x')}{term(m * n, '')} = (x{term(m, '')})(x{term(n, '')}); m = {m}")


@gen("systems")
def _(rng):
    while True:
        x, y = rng.randint(-5, 6), rng.randint(-5, 6)
        a1, b1, a2, b2 = rng.randint(1, 4), rng.randint(1, 4), rng.randint(1, 4), rng.randint(-4, -1)
        if a1 * b2 - a2 * b1 != 0 and x != y:
            break
    c1, c2 = a1 * x + b1 * y, a2 * x + b2 * y
    return task(f"Решите систему уравнений: {poly((a1, 'x'), (b1, 'y'))} = {num(c1)};  {poly((a2, 'x'), (b2, 'y'))} = {num(c2)}. "
                f"В ответе запишите значение x.", x,
                distractors=[(y, "variables_swapped")],
                solution=f"x = {x}, y = {y}")


@gen("word_problems")
def _(rng):
    if rng.random() < 0.5:
        v1, v2 = rng.choice([(40, 60), (50, 70), (60, 80), (45, 75), (55, 65)])
        t = rng.choice([2, 3, F(3, 2), F(5, 2)])
        s = (v1 + v2) * t
        return task(f"Из двух городов, расстояние между которыми {num(s)} км, одновременно навстречу друг другу выехали "
                    f"два автомобиля со скоростями {v1} км/ч и {v2} км/ч. Через сколько часов они встретятся?", t,
                    distractors=[(F(s, v2 - v1), "closing_speed")],
                    solution=f"Скорость сближения {v1 + v2} км/ч; t = {num(s)}/{v1 + v2} = {num(t)} ч")
    a, b = rng.choice([(3, 6), (4, 12), (6, 12), (10, 15), (12, 24), (20, 30), (2, 3)])
    ans = F(a * b, a + b)
    return task(f"Первый рабочий выполняет заказ за {a} ч, второй — за {b} ч. За сколько часов они выполнят заказ, "
                f"работая вместе?", ans,
                distractors=[(F(a + b, 2), "work_average_time"), (a + b, "work_add_time")],
                solution=f"Производительности 1/{a} и 1/{b}; вместе {num(F(1, a) + F(1, b))} заказа в час; t = {num(ans)} ч")


# ---------------------------------------------------------------- 8 класс

@gen("alg_fractions")
def _(rng):
    a, b = rng.randint(1, 6), rng.randint(1, 6)
    k = rng.randint(2, 9)
    ans = k + b
    return task(f"Сократите дробь (x²{term(a + b, 'x')}{term(a * b, '')})/(x + {a}) и найдите значение полученного "
                f"выражения при x = {k}.", ans,
                distractors=[(k + a, "cancel_wrong_factor")],
                solution=f"x²{term(a + b, 'x')}{term(a * b, '')} = (x + {a})(x + {b}); после сокращения x + {b} = {ans}")


@gen("sqrt")
def _(rng):
    if rng.random() < 0.5:
        a, b, c = rng.choice([(3, 4, 5), (6, 8, 10), (5, 12, 13), (8, 15, 17), (9, 12, 15), (12, 16, 20),
                              (15, 20, 25), (10, 24, 26), (7, 24, 25), (20, 21, 29)])
        return task(f"Вычислите: √({a * a} + {b * b})", c, distractors=[(a + b, "sqrt_of_sum")],
                    solution=f"√{a * a + b * b} = {c}")
    a, b = rng.choice([(2, 8), (3, 12), (2, 18), (5, 20), (3, 27), (2, 32), (6, 24), (2, 50), (3, 48),
                       (5, 45), (7, 28), (2, 72), (3, 75), (6, 54), (10, 40)])
    ans = int(math.isqrt(a * b))
    return task(f"Вычислите: √{a} · √{b}", ans, solution=f"√({a}·{b}) = √{a * b} = {ans}")


@gen("quadratic")
def _(rng):
    if rng.random() < 0.35:
        a, r = rng.randint(1, 4), nz(rng, -6, 6)
        return task(f"Решите уравнение: {poly((a, 'x²'), (-a * r, 'x'))} = 0. Если корней несколько, запишите их через «;».",
                    [0, r], kind="set", distractors=[([r], "lost_root_division")],
                    answer_format="числа через «;»",
                    solution=f"x({term(a, 'x', True)}{term(-a * r, '')}) = 0 ⇒ x = 0 или x = {r}")
    while True:
        r1, r2 = rng.randint(-7, 7), rng.randint(-7, 7)
        if r1 != r2 and r1 != -r2 and r1 * r2 != 0:
            break
    p, q = -(r1 + r2), r1 * r2
    return task(f"Решите уравнение: x²{term(p, 'x')}{term(q, '')} = 0. Если корней несколько, запишите их через «;».",
                [r1, r2], kind="set", distractors=[([-r1, -r2], "sign")], answer_format="числа через «;»",
                solution=f"D = {p * p - 4 * q}; x = {min(r1, r2)} и x = {max(r1, r2)}")


@gen("vieta")
def _(rng):
    s, p = rng.randint(-6, 8), rng.randint(-8, 6)
    while s * s - 4 * p < 0:
        p -= 3
    ans = s * s - 2 * p
    return task(f"x₁ и x₂ — корни уравнения x²{term(-s, 'x')}{term(p, '')} = 0. Найдите x₁² + x₂².", ans,
                distractors=[(s * s, "vieta_square_sum"), (s * s + 2 * p, "sign")],
                solution=f"x₁ + x₂ = {num(s)}, x₁x₂ = {num(p)}; x₁² + x₂² = {par(s)}² − 2·{par(p)} = {num(ans)}")


@gen("lin_ineq")
def _(rng):
    while True:
        a, c = rng.randint(1, 4), rng.randint(5, 9)
        b, d = rng.randint(-9, 9), rng.randint(-9, 9)
        if a < c:
            break
    # a x + b > c x + d ⇒ (a − c) x > d − b ⇒ x < (d − b)/(a − c)
    v = F(d - b, a - c)
    largest = math.ceil(v) - 1
    wrong_flip = math.floor(v) + 1
    dis = [(wrong_flip, "inequality_no_flip")]
    if v.denominator == 1:
        dis.append((int(v), "strict_boundary"))
    return task(f"Найдите наибольшее целое решение неравенства {term(a, 'x', True)}{term(b, '')} > {c}x{term(d, '')}.", largest,
                distractors=dis,
                solution=f"{term(a - c, 'x', True)} > {num(d - b)} ⇒ x < {num(v)} (знак меняется при делении на {num(a - c)}); ответ {num(largest)}")


@gen("pythagoras")
def _(rng):
    a, b, c = rng.choice([(3, 4, 5), (6, 8, 10), (5, 12, 13), (8, 15, 17), (9, 12, 15), (7, 24, 25), (20, 21, 29),
                          (12, 16, 20), (15, 20, 25), (10, 24, 26), (9, 40, 41), (12, 35, 37)])
    if rng.random() < 0.5:
        a, b = (a, b) if rng.random() < 0.5 else (b, a)
        return task(f"Катеты прямоугольного треугольника равны {a} и {b}. Найдите гипотенузу.", c,
                    distractors=[(a + b, "pythagoras_sum")], solution=f"c = √({a}² + {b}²) = {c}")
    return task(f"Гипотенуза прямоугольного треугольника равна {c}, один из катетов равен {a}. Найдите другой катет.", b,
                distractors=[(math.isqrt(c * c + a * a), "pythagoras_leg_add")]
                if math.isqrt(c * c + a * a) ** 2 == c * c + a * a else [],
                solution=f"b = √({c}² − {a}²) = {b}")


@gen("areas")
def _(rng):
    if rng.random() < 0.5:
        a, b, h = rng.randint(3, 12), rng.randint(13, 24), rng.randint(2, 10)
        ans = F((a + b) * h, 2)
        return task(f"Основания трапеции равны {a} и {b}, высота равна {h}. Найдите площадь трапеции.", ans,
                    distractors=[((a + b) * h, "area_half")], solution=f"S = ({a} + {b})/2 · {h} = {num(ans)}")
    a, h = rng.randint(4, 20), rng.randint(3, 14)
    ans = F(a * h, 2)
    return task(f"Сторона треугольника равна {a}, а высота, проведённая к ней, равна {h}. Найдите площадь треугольника.",
                ans, distractors=[(a * h, "area_half")], solution=f"S = ½·{a}·{h} = {num(ans)}")


# ---------------------------------------------------------------- 9 класс

@gen("quad_ineq")
def _(rng):
    r1 = rng.randint(-6, 2)
    r2 = r1 + rng.randint(3, 8)
    p, q = -(r1 + r2), r1 * r2
    if rng.random() < 0.5:
        ans, wrong, sign = r2 - r1 + 1, r2 - r1 - 1, "≤"
    else:
        ans, wrong, sign = r2 - r1 - 1, r2 - r1 + 1, "<"
    return task(f"Сколько целых решений имеет неравенство x²{term(p, 'x')}{term(q, '')} {sign} 0?", ans,
                distractors=[(wrong, "strict_boundary")],
                solution=f"Корни {r1} и {r2}; решение — отрезок между корнями ({'включая' if sign == '≤' else 'не включая'} концы); целых: {ans}")


@gen("progressions")
def _(rng):
    n = rng.randint(6, 12)
    if rng.random() < 0.5:
        a1, d = rng.randint(-10, 10), nz(rng, -5, 6)
        ans = a1 + (n - 1) * d
        return task(f"Арифметическая прогрессия: a₁ = {num(a1)}, d = {num(d)}. Найдите a{str(n).translate(SUB)}.", ans,
                    distractors=[(a1 + n * d, "progression_n_index")],
                    solution=f"a{str(n).translate(SUB)} = {num(a1)} + {n - 1}·{par(d)} = {ans}")
    b1, q = rng.choice([1, 2, 3, -2]), rng.choice([2, -2, 3])
    n = rng.randint(4, 6)
    ans = b1 * q ** (n - 1)
    return task(f"Геометрическая прогрессия: b₁ = {num(b1)}, q = {num(q)}. Найдите b{str(n).translate(SUB)}.", ans,
                distractors=[(b1 * q ** n, "progression_n_index")],
                solution=f"b{str(n).translate(SUB)} = {num(b1)}·{par(q)}{str(n - 1).translate(SUP)} = {ans}")


@gen("quad_func")
def _(rng):
    a = nz(rng, -3, 3)
    x0 = F(rng.randint(-8, 8), rng.choice([1, 2]))
    b = -2 * a * x0          # целое при любом x0 вида k/2
    c = rng.randint(-9, 9)
    return task(f"Найдите абсциссу вершины параболы y = {poly((a, 'x²'), (b, 'x'), (c, ''))}.", x0,
                distractors=[(-b / a, "vertex_no_2"), (b / (2 * a), "sign")],
                solution=f"x₀ = −b/(2a) = {num(-b)}/{par(2 * a)} = {num(x0)}")


@gen("probability")
def _(rng):
    total = rng.choice([10, 20, 25, 40, 50])
    b = rng.randint(2, total // 2)
    r = rng.randint(1, total - b - 1)
    g = total - b - r
    ans = F(b, total)
    return task(f"В коробке {r} красных, {b} синих и {g} зелёных шаров. Наугад вынимают один шар. "
                f"Найдите вероятность того, что он синий.", ans,
                distractors=[(F(b, r + g), "probability_wrong_total")], answer_format="десятичная дробь",
                solution=f"P = {b}/{total} = {num(ans, decimal=True)}")


@gen("rational_eq")
def _(rng):
    while True:
        r1, r2 = rng.randint(-6, 6), rng.randint(-6, 6)
        if r1 != r2 and r1 != -r2 and r1 * r2 != 0:
            break
    p, q = -(r1 + r2), r1 * r2
    return task(f"Решите уравнение: (x²{term(p, 'x')}{term(q, '')})/(x{term(-r1, '')}) = 0. "
                f"Если корней несколько, запишите их через «;».", [r2], kind="set",
                distractors=[([r1, r2], "extraneous_root")], answer_format="числа через «;»",
                solution=f"Числитель равен 0 при x = {r1} и x = {r2}, но x = {r1} обращает знаменатель в 0. Ответ: {r2}")


# ---------------------------------------------------------------- 10–11 класс

@gen("trig_values")
def _(rng):
    a, b, c = rng.choice([(3, 4, 5), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29), (9, 40, 41), (12, 35, 37)])
    a, b = (a, b) if rng.random() < 0.5 else (b, a)
    # четверть задаёт знаки: I (+,+), II (sin+, cos−), III (−,−), IV (sin−, cos+)
    quarter = rng.choice([1, 2, 3, 4])
    s_sign = 1 if quarter in (1, 2) else -1
    c_sign = 1 if quarter in (1, 4) else -1
    where = {1: "α — острый угол", 2: "α ∈ (90°; 180°)", 3: "α ∈ (180°; 270°)", 4: "α ∈ (270°; 360°)"}[quarter]
    if rng.random() < 0.5:
        given, ans, gname, aname = F(s_sign * a, c), F(c_sign * b, c), "sin", "cos"
    else:
        given, ans, gname, aname = F(c_sign * a, c), F(s_sign * b, c), "cos", "sin"
    one_minus = (1 - abs(given)) * (1 if ans > 0 else -1)
    return task(f"Найдите {aname} α, если {gname} α = {_frac(given)} и {where}.", ans,
                distractors=[(-ans, "trig_sign"), (one_minus, "trig_one_minus")],
                answer_format="десятичная дробь или a/b",
                solution=f"{aname}²α = 1 − {gname}²α = 1 − {a * a}/{c * c} = {b * b}/{c * c}; "
                         f"с учётом четверти {aname} α = {_frac(ans)}")


def _frac(x: F) -> str:
    return f"{'−' if x < 0 else ''}{abs(x.numerator)}/{x.denominator}" if x.denominator != 1 else num(x)


@gen("log")
def _(rng):
    if rng.random() < 0.5:
        base, b, c = rng.choice([(6, 4, 9), (10, 4, 25), (2, 6, F(4, 3)), (3, 6, F(3, 2)), (12, 3, 48), (5, 2, F(25, 2)),
                                 (10, 2, 50), (10, 5, 20), (6, 2, 18), (3, 2, F(9, 2)), (2, 12, F(2, 3)), (15, 3, 75)])
        ans = round(math.log(float(b * c), base))
        sub = str(base).translate(SUB)
        return task(f"Вычислите: log{sub} {num(b)} + log{sub} {num(c)}", ans,
                    solution=f"log{sub}({num(b)}·{num(c)}) = log{sub} {num(b * c)} = {ans}")
    base = rng.choice([2, 3, 5])
    k = rng.randint(2, 4)
    m = rng.randint(2, 5)
    sub = str(base).translate(SUB)
    big = base ** (k + 1) * m
    return task(f"Вычислите: log{sub} {big} − log{sub} {m}", k + 1,
                solution=f"log{sub}({big}/{m}) = log{sub} {base ** (k + 1)} = {k + 1}")


@gen("exp_eq")
def _(rng):
    a = rng.choice([2, 3, 5])
    k = rng.randint(2, 5 if a == 2 else 3) + (2 if a == 2 else 0)
    m = rng.randint(1, 4)
    x0 = F(k + m, 2)
    return task(f"Решите уравнение: {a}^(2x − {m}) = {a ** k}", x0,
                distractors=[(F(k - m, 2), "sign")], solution=f"{a ** k} = {a}^{k}; 2x − {m} = {k}; x = {num(x0)}")


@gen("log_eq")
def _(rng):
    a = rng.choice([2, 3, 5])
    k = rng.randint(2, 4)
    m = rng.randint(1, 9)
    ans = a ** k - m
    return task(f"Решите уравнение: log{str(a).translate(SUB)}(x + {m}) = {k}", ans,
                distractors=[(a * k - m, "log_definition")],
                solution=f"x + {m} = {a}^{k} = {a ** k}; x = {ans}")


@gen("derivative")
def _(rng):
    a, b, c, d = nz(rng, -3, 3), rng.randint(-5, 5), rng.randint(-9, 9), rng.randint(-9, 9)
    x0 = nz(rng, -3, 3)
    ans = 3 * a * x0 ** 2 + 2 * b * x0 + c
    fval = a * x0 ** 3 + b * x0 ** 2 + c * x0 + d
    return task(f"Найдите значение производной функции f(x) = {poly((a, 'x³'), (b, 'x²'), (c, 'x'), (d, ''))} "
                f"в точке x₀ = {num(x0)}.", ans,
                distractors=[(fval, "derivative_value_of_f")],
                solution=f"f′(x) = {poly((3 * a, 'x²'), (2 * b, 'x'), (c, ''))}; f′({num(x0)}) = {ans}")


def generate(topic: str, rng: random.Random) -> dict:
    t = GENERATORS[topic](rng)
    t["topic"] = topic
    return t
