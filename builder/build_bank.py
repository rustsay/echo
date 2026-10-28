"""Собирает банк заданий ОГЭ (docs/bank.json) для веб-приложения.

Задания создаются параметрическими генераторами из проекта «Маршрут»:
ответы вычисляются программно, поэтому гарантированно верны. Для каждого
задания заранее готовится озвучка условия, ответа и решения.

Запуск:  python -m builder.build_bank
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from .engine.checker import ERRORS, format_answer
from .engine.curriculum import TOPICS, ancestors
from .engine.generators import generate
from .speech import answer_to_speech, to_speech

ROOT = Path(__file__).resolve().parents[1]
PER_TOPIC = 60
SEED = 2026

OGE_TOPICS = [t.id for t in TOPICS.values() if "oge" in t.exams and t.grade <= 9]

FORMAT_HINTS = {
    "set": "Если корней несколько, введите их через точку с запятой. Если корней нет — слово «нет».",
    "number": "Дробь можно ввести через косую черту, например 3/4, или десятичной дробью через запятую.",
}


def build() -> dict:
    rng = random.Random(SEED)
    tasks = []
    for topic in OGE_TOPICS:
        seen = set()
        attempts = 0
        while len(seen) < PER_TOPIC and attempts < PER_TOPIC * 20:
            attempts += 1
            t = generate(topic, rng)
            if t["text"] in seen:
                continue
            seen.add(t["text"])
            key = format_answer(t)
            tasks.append({
                "id": f"{topic}-{len(seen)}",
                "topic": topic,
                "text": t["text"],
                "speech": to_speech(t["text"]),
                "answer": t["answer"],
                "key": key,
                "key_speech": answer_to_speech(key),
                "distractors": t["distractors"],
                "strict": t["strict_simplified"],
                "solution": t["solution"],
                "solution_speech": to_speech(t["solution"]),
            })
    topics = {}
    for tid in OGE_TOPICS:
        t = TOPICS[tid]
        topics[tid] = {
            "name": t.name, "grade": t.grade,
            "prereqs": [p for p in t.prereqs if p in OGE_TOPICS],
            "ancestors": sorted(a for a in ancestors(tid) if a in OGE_TOPICS),
            "ideas": [{"text": x, "speech": to_speech(x)} for x in t.ideas],
            "pitfalls": list(t.pitfalls),
            "count": sum(1 for x in tasks if x["topic"] == tid),
        }
    return {"version": 1, "topics": topics, "order": OGE_TOPICS, "errors": ERRORS,
            "hints": FORMAT_HINTS, "tasks": tasks}


def main():
    bank = build()
    out = ROOT / "docs" / "bank.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(bank, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Готово: {out} — {len(bank['tasks'])} заданий по {len(bank['topics'])} темам, "
          f"{out.stat().st_size // 1024} КБ")


if __name__ == "__main__":
    main()
