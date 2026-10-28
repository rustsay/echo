"""Перевод математической записи в русскую речь.

Экранные дикторы и синтезаторы речи читают «x² − 5x + 6 = 0» плохо или
неоднозначно («икс два минус пять икс…»). Здесь запись разбирается и
превращается в однозначную фразу так, как её продиктовал бы учитель:
«икс в квадрате минус 5 икс плюс 6 равно 0».

Правила:
  • дроби — «дробь: числитель 3, знаменатель 4»; составные — «в числителе …, в знаменателе …, конец дроби»
  • корни — «квадратный корень из …», для выражений — «…, конец корня»
  • степени — «в квадрате», «в кубе», «в степени 6»
  • индексы — «икс первое», «а двенадцатое»
  • скобки в формулах — «скобка открывается … скобка закрывается»
  • точки на плоскости — «икс равно 2, игрек равно 4»
  • латинские буквы — «икс», «игрек», «ка», «бэ»…
"""
from __future__ import annotations

import re

LATIN = {"S": "эс", "P": "пэ", "D": "дискриминант", "x": "икс", "y": "игрек", "k": "ка", "b": "бэ", "m": "эм", "n": "эн", "d": "дэ", "q": "ку",
         "a": "а", "c": "цэ", "p": "пэ", "f": "эф", "h": "аш", "t": "тэ", "s": "эс", "v": "вэ"}
SUP = dict(zip("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789"))
SUB = dict(zip("₀₁₂₃₄₅₆₇₈₉", "0123456789"))
ORD_NEUT = ["нулевое", "первое", "второе", "третье", "четвёртое", "пятое", "шестое", "седьмое", "восьмое",
            "девятое", "десятое", "одиннадцатое", "двенадцатое", "тринадцатое", "четырнадцатое",
            "пятнадцатое", "шестнадцатое", "семнадцатое", "восемнадцатое", "девятнадцатое", "двадцатое"]

TOKEN_CHARS = set("0123456789,abcdefghijklmnopqrstuvwxyz⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉")
CYR = re.compile(r"[а-яё]", re.I)
# слова, которые сами вставляем при озвучке: скобки с ними — всё ещё формула
MATH_WORDS = set(ORD_NEUT) | {"энное", "в", "квадрате", "кубе", "степени", "квадратный", "корень", "из", "выражения",
                              "конец", "корня", "дробь", "числитель", "знаменатель", "числителе", "знаменателе",
                              "дроби", "запятая", "разделить", "на", "делённое", "чисел", "скобка", "открывается",
                              "закрывается", "плюс", "минус", "эм", "эн"}


def _is_formula(content: str) -> bool:
    words = re.findall(r"[а-яё]+", content.lower())
    return all(w in MATH_WORDS for w in words)


def _match_close(s: str, i: int) -> int:
    """Индекс закрывающей скобки для s[i] == '('."""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "(":
            depth += 1
        elif s[j] == ")":
            depth -= 1
            if depth == 0:
                return j
    return -1


def _match_open(s: str, i: int) -> int:
    depth = 0
    for j in range(i, -1, -1):
        if s[j] == ")":
            depth += 1
        elif s[j] == "(":
            depth -= 1
            if depth == 0:
                return j
    return -1


def _sqrt(s: str) -> str:
    while "√" in s:
        i = s.index("√")
        if i + 1 < len(s) and s[i + 1] == "(":
            j = _match_close(s, i + 1)
            if j == -1:
                break
            inner = s[i + 2:j]
            s = s[:i] + f"квадратный корень из выражения {inner}, конец корня" + s[j + 1:]
        else:
            m = re.match(r"√([\d,]+|[a-z])", s[i:])
            if not m:
                s = s[:i] + "квадратный корень" + s[i + 1:]
                continue
            s = s[:i] + f"квадратный корень из {m.group(1)}" + s[i + len(m.group(0)):]
    return s


def _fractions(s: str) -> str:
    """Находит «/» и заменяет a/b на словесную дробь (с учётом скобок)."""
    guard = 0
    while "/" in s and guard < 50:
        guard += 1
        i = s.index("/")
        # числитель
        if i > 0 and s[i - 1] == ")":
            a0 = _match_open(s, i - 1)
            num, num_complex = s[a0 + 1:i - 1], True
        else:
            a0 = i
            while a0 > 0 and s[a0 - 1] in TOKEN_CHARS:
                a0 -= 1
            num, num_complex = s[a0:i], False
        # знаменатель
        if i + 1 < len(s) and s[i + 1] == "(":
            b1 = _match_close(s, i + 1)
            den, den_complex = s[i + 2:b1], True
            end = b1 + 1
        else:
            b1 = i + 1
            if b1 < len(s) and s[b1] == "−":         # знаменатель со знаком: 12/−4
                b1 += 1
            while b1 < len(s) and s[b1] in TOKEN_CHARS:
                b1 += 1
            den, den_complex = s[i + 1:b1], False
            end = b1
        if not num or not den:
            s = s[:i] + " делённое на " + s[i + 1:]
            continue
        if num_complex or den_complex:
            words = f"дробь: в числителе {num}, в знаменателе {den}, конец дроби"
        else:
            words = f"дробь: числитель {num}, знаменатель {den}"
        s = s[:a0] + words + s[end:]
    return s


def _parens(s: str) -> str:
    """Скобки внутри формул проговариваем, скобки в обычном тексте оставляем."""
    out, i = [], 0
    while i < len(s):
        if s[i] == "(":
            j = _match_close(s, i)
            if j != -1 and _is_formula(s[i + 1:j]):
                out.append(" скобка открывается, " + _parens(s[i + 1:j]) + ", скобка закрывается ")
                i = j + 1
                continue
        out.append(s[i])
        i += 1
    return "".join(out)


def _ordinal(n: int) -> str:
    return ORD_NEUT[n] if 0 <= n < len(ORD_NEUT) else f"номер {n}"


def _latin(m: re.Match) -> str:
    return " ".join(LATIN.get(ch, ch) for ch in m.group(0))


def to_speech(text: str) -> str:
    s = text
    s = s.replace("через «;»", "через точку с запятой")
    s = s.replace("«;»", "точка с запятой").replace("«/»", "косая черта")
    s = s.replace("км/ч", "километров в час")
    s = re.sub(r"(НОД|НОК)\((\d+), (\d+)\)", r"\1 чисел \2 и \3", s)
    s = s.replace("^", " в степени ")
    s = s.replace("−b/(2a)", "минус бэ, делённое на два а")
    # точки на плоскости: (2; 4) → икс равно 2, игрек равно 4
    s = re.sub(r"\((−?\d+(?:,\d+)?); (−?\d+(?:,\d+)?)\)", r"(икс равно \1, игрек равно \2)", s)
    # индексы: x₁ → икс первое, a₁₂ → а двенадцатое
    s = re.sub(r"([a-z])([₀₁₂₃₄₅₆₇₈₉]+)",
               lambda m: f"{m.group(1)} {_ordinal(int(''.join(SUB[c] for c in m.group(2))))} ", s)
    # буквенные показатели: aᵐ⁺ⁿ → а в степени эм плюс эн; индекс ₙ → энное
    s = re.sub(r"([a-z])ₙ", r"\1 энное ", s)
    s = re.sub(r"([ᵐⁿ⁺⁻⁰¹²³⁴⁵⁶⁷⁸⁹]*[ᵐⁿ][ᵐⁿ⁺⁻⁰¹²³⁴⁵⁶⁷⁸⁹]*)",
               lambda m: " в степени " + m.group(1).translate(str.maketrans("ᵐⁿ⁺⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "mn+−0123456789"))
               .replace("+", " плюс ").replace("−", " минус ") + " ", s)
    # десятичная запятая
    s = re.sub(r"(\d),(\d)", r"\1 запятая \2", s)
    # деление «:» между числами/выражениями (а не двоеточие после слова)
    s = re.sub(r"(?<=[\d)a-z²³⁰¹⁴⁵⁶⁷⁸⁹ᵐⁿ])\s?:\s?(?=[\d(a-z−])", " разделить на ", s)
    s = s.replace("±", " плюс-минус ").replace("½", " одна вторая ").replace("≠", " не равно ")
    s = s.replace("Oy", "О-игрек").replace("Ox", "О-икс")
    s = _sqrt(s)
    s = _fractions(s)
    # степени
    s = re.sub(r"([⁰¹²³⁴⁵⁶⁷⁸⁹]+)", lambda m: {"2": " в квадрате ", "3": " в кубе "}.get(
        "".join(SUP[c] for c in m.group(1)), " в степени " + "".join(SUP[c] for c in m.group(1)) + " "), s)
    s = _parens(s)
    # операции и отношения
    for sym, word in (("≤", " меньше или равно "), ("≥", " больше или равно "), ("<", " меньше "), (">", " больше "),
                      ("⇒", ", следовательно, "), ("·", " умножить на "), ("+", " плюс "), ("=", " равно "),
                      ("°", " градусов"), ("∈", " принадлежит ")):
        s = s.replace(sym, word)
    s = re.sub(r"−\s*", " минус ", s)
    s = s.replace("′", " штрих")
    # число, слитое с буквой: 5x → 5 x
    s = re.sub(r"(\d)([a-z])", r"\1 \2", s)
    # латинские буквы (только вне русских слов)
    s = re.sub(r"(?<![а-яёА-ЯЁ])\b(?:[a-z]{1,3}|[SPD])\b(?![а-яё])", _latin, s)
    s = re.sub(r"\bдробь\s+дробь:", "дробь:", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+([,.;:?!])", r"\1", s)
    s = re.sub(r",\s*,", ",", s)
    s = re.sub(r"\(\s+", "(", s)
    return s.strip()


def answer_to_speech(key: str) -> str:
    if key == "нет корней":
        return key
    parts = [p.strip() for p in key.split(";")]
    spoken = [to_speech(p) for p in parts]
    return " и ".join(spoken) if len(spoken) > 1 else spoken[0]
