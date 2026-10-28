"""Проверка ответа ученика и определение типа ошибки."""
from __future__ import annotations

import re
from fractions import Fraction as F
from typing import Optional

ERRORS = {
    "no_answer": "нет ответа",
    "format": "ответ не удалось прочитать",
    "other": "ошибка без явного шаблона",
    "computation": "вычислительная ошибка (ответ близок к верному)",
    "sign": "ошибка в знаке",
    "decimal_point": "ошибка в положении запятой",
    "not_simplified": "дробь не сокращена до конца",
    "lost_root": "потерян корень",
    "extra_root": "лишний (посторонний) корень",
    "order_of_operations": "нарушен порядок действий",
    "lcm_product": "НОК найден как произведение чисел",
    "gcd_lcm_confused": "перепутаны НОД и НОК",
    "add_num_den": "сложены числители и знаменатели",
    "common_denominator": "ошибка при приведении к общему знаменателю",
    "division_no_flip": "деление дробей без «переворота» делителя",
    "double_negative": "ошибка с «минус на минус»",
    "percent_part_only": "найден процент, но не прибавлен к исходной величине",
    "percent_wrong_base": "процент взят не от той величины",
    "proportion_rule": "неверно применено основное свойство пропорции",
    "minus_before_bracket": "минус перед скобкой не применён ко всем слагаемым",
    "powers_multiply_exponents": "показатели перемножены вместо сложения",
    "bracket_partial": "при раскрытии скобки умножено не всё",
    "slope_inverted": "перевёрнуто отношение приращений",
    "sfm_double_product": "потеряно удвоенное произведение",
    "sfm_square_sum": "(a + b)² записано как a² + b²",
    "factor_order": "перепутаны множители",
    "factor_partial": "общий множитель вынесен не полностью",
    "variables_swapped": "перепутаны переменные",
    "closing_speed": "неверно найдена скорость сближения",
    "work_average_time": "взято среднее время вместо сложения производительностей",
    "work_add_time": "сложено время вместо производительностей",
    "cancel_wrong_factor": "сокращён не тот множитель",
    "sqrt_of_sum": "корень из суммы извлечён почленно",
    "lost_root_division": "деление на x — потерян корень 0",
    "vieta_square_sum": "x₁² + x₂² посчитано как (x₁ + x₂)²",
    "inequality_no_flip": "знак неравенства не изменён при делении на отрицательное",
    "strict_boundary": "перепутаны строгое и нестрогое неравенство",
    "pythagoras_sum": "гипотенуза найдена как сумма катетов",
    "pythagoras_leg_add": "квадраты сложены вместо вычитания",
    "area_half": "забыт множитель ½",
    "progression_n_index": "в формуле n-го члена взято n вместо n − 1",
    "vertex_no_2": "в формуле вершины забыта двойка",
    "probability_wrong_total": "деление на число остальных исходов, а не всех",
    "extraneous_root": "не исключён посторонний корень (ОДЗ)",
    "trig_sign": "неверный знак тригонометрической функции",
    "trig_one_minus": "cos α найден как 1 − sin α",
    "log_definition": "неверно раскрыт логарифм (aᶜ заменено на a·c)",
    "derivative_value_of_f": "точка подставлена в функцию, а не в производную",
}

EMPTY_SET = {"нет", "нет корней", "нет решений", "∅", "пусто", "корней нет"}
_NUM = re.compile(r"^[+-]?(\d+([.,]\d+)?|\d+/\d+|[.,]\d+)$")


def _clean(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("−", "-").replace("–", "-").replace("—", "-").replace(" ", " ")
    s = re.sub(r"^(x\s*=|ответ\s*:?)\s*", "", s)
    return s.strip().rstrip(".")


def parse_number(s: str) -> Optional[F]:
    s = _clean(s).replace(" ", "")
    if not s or not _NUM.match(s):
        return None
    if "/" in s:
        p, q = s.split("/")
        if int(q) == 0:
            return None
        return F(int(p), int(q))
    return F(s.replace(",", "."))


def raw_fraction(s: str) -> Optional[tuple[int, int]]:
    s = _clean(s).replace(" ", "")
    m = re.fullmatch(r"([+-]?\d+)/(\d+)", s)
    return (int(m.group(1)), int(m.group(2))) if m else None


def parse_set(s: str) -> Optional[set[F]]:
    s = _clean(s)
    if s in EMPTY_SET:
        return set()
    if ";" in s:
        parts = s.split(";")
    elif re.search(r"\d\s*,\s+[-\d]", s):      # «2, 3» — запятая с пробелом разделяет числа
        parts = re.split(r",\s+", s)
    elif " и " in s:
        parts = s.split(" и ")
    else:
        parts = s.split()
    out = set()
    for p in parts:
        if not p.strip():
            continue
        v = parse_number(p)
        if v is None:
            return None
        out.add(v)
    return out


def check(task: dict, raw: str) -> dict:
    """Возвращает {"correct": bool, "error": код|None, "label": текст, "given": нормализованный ответ}."""
    ans = task["answer"]
    if not (raw or "").strip():
        return _r(False, "no_answer", raw)
    if ans["kind"] == "set":
        return _check_set(task, raw)
    return _check_number(task, raw)


def _r(correct: bool, error: Optional[str], raw: str) -> dict:
    return {"correct": correct, "error": error, "label": ERRORS.get(error, "") if error else "", "given": (raw or "").strip()}


def _check_number(task: dict, raw: str) -> dict:
    v = parse_number(raw)
    if v is None:
        return _r(False, "format", raw)
    c = F(task["answer"]["value"])
    if v == c:
        if task.get("strict_simplified"):
            fr = raw_fraction(raw)
            if fr and F(*fr) == c and (abs(fr[0]), fr[1]) != (abs(c.numerator), c.denominator):
                return _r(False, "not_simplified", raw)
        return _r(True, None, raw)
    for d in task.get("distractors", []):
        if F(d["value"]) == v:
            return _r(False, d["error"], raw)
    if c != 0 and v == -c:
        return _r(False, "sign", raw)
    if c != 0:
        for k in (10, 100, F(1, 10), F(1, 100)):
            if v == c * k:
                return _r(False, "decimal_point", raw)
        if abs(v - c) / abs(c) <= F(15, 100):
            return _r(False, "computation", raw)
    return _r(False, "other", raw)


def _check_set(task: dict, raw: str) -> dict:
    s = parse_set(raw)
    if s is None:
        return _r(False, "format", raw)
    c = {F(x) for x in task["answer"]["value"]}
    if s == c:
        return _r(True, None, raw)
    for d in task.get("distractors", []):
        if {F(x) for x in d["value"]} == s:
            return _r(False, d["error"], raw)
    if s and s < c:
        return _r(False, "lost_root", raw)
    if s > c:
        return _r(False, "extra_root", raw)
    if {-x for x in s} == c:
        return _r(False, "sign", raw)
    return _r(False, "other", raw)


def format_answer(task: dict) -> str:
    """Ответ для ключа: десятичная дробь, если она конечная, иначе a/b."""
    from .generators import num
    a = task["answer"]
    if a["kind"] == "set":
        vals = [num(F(x)) for x in a["value"]]
        return "; ".join(vals) if vals else "нет корней"
    v = F(a["value"])
    if task.get("strict_simplified") or "a/b" in task.get("answer_format", "") and "десятич" not in task.get("answer_format", ""):
        return num(v) if v.denominator == 1 else f"{'−' if v < 0 else ''}{abs(v.numerator)}/{v.denominator}"
    return num(v)
