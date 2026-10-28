"use strict";
/* Проверка ответа ученика. Та же логика, что в Python-версии (builder/engine/checker.py);
   совпадение результатов проверяется автотестом tests/test_parity.py. */
function gcd(a, b) { a = Math.abs(a); b = Math.abs(b); while (b) [a, b] = [b, a % b]; return a || 1; }
function frac(p, q) { if (q < 0) { p = -p; q = -q; } const g = gcd(p, q); return [p / g, q / g]; }
function parseFracString(s) { const [p, q] = s.split("/").map(Number); return frac(p, q || 1); }
const eq = (a, b) => a[0] === b[0] && a[1] === b[1];
const fkey = (f) => f[0] + "/" + f[1];

function clean(raw) {
  let s = String(raw || "").trim().toLowerCase();
  s = s.replace(/[−–—]/g, "-").replace(/ /g, " ");
  s = s.replace(/^(x\s*=|икс\s*равно|ответ\s*:?)\s*/, "");
  return s.trim().replace(/\.$/, "");
}
function parseNumber(raw) {
  const s = clean(raw).replace(/\s+/g, "");
  if (!s || !/^[+-]?(\d+([.,]\d+)?|\d+\/\d+|[.,]\d+)$/.test(s)) return null;
  if (s.includes("/")) {
    const [p, q] = s.split("/").map(Number);
    return q === 0 ? null : { value: frac(p, q), raw: [p, q] };
  }
  const neg = s.startsWith("-");
  const body = s.replace(/^[+-]/, "").replace(",", ".");
  const [ip, dp = ""] = body.split(".");
  const q = 10 ** dp.length;
  const p = Number(ip || "0") * q + Number(dp || "0");
  return { value: frac(neg ? -p : p, q), raw: null };
}
function parseSet(raw) {
  const s = clean(raw);
  if (["нет", "нет корней", "корней нет", "нет решений", "∅", "пусто"].includes(s)) return [];
  let parts;
  if (s.includes(";")) parts = s.split(";");
  else if (/\d\s*,\s+[-\d]/.test(s)) parts = s.split(/,\s+/);
  else if (s.includes(" и ")) parts = s.split(" и ");
  else parts = s.split(/\s+/);
  const out = new Map();
  for (const p of parts) {
    if (!p.trim()) continue;
    const n = parseNumber(p);
    if (!n) return null;
    out.set(fkey(n.value), n.value);
  }
  return [...out.values()];
}
const setEq = (a, b) => a.length === b.length && a.every((x) => b.some((y) => eq(x, y)));
const subset = (a, b) => a.every((x) => b.some((y) => eq(x, y)));

function check(task, raw, errors = {}) {
  const res = (correct, error) => ({ correct, error, label: error ? (errors[error] || "") : "" });
  if (!String(raw || "").trim()) return res(false, "no_answer");
  if (task.answer.kind === "set") {
    const s = parseSet(raw);
    if (s === null) return res(false, "format");
    const c = task.answer.value.map(parseFracString);
    if (setEq(s, c)) return res(true, null);
    for (const d of task.distractors) if (setEq(s, d.value.map(parseFracString))) return res(false, d.error);
    if (s.length && s.length < c.length && subset(s, c)) return res(false, "lost_root");
    if (s.length > c.length && subset(c, s)) return res(false, "extra_root");
    if (setEq(s.map((x) => [-x[0], x[1]]), c)) return res(false, "sign");
    return res(false, "other");
  }
  const n = parseNumber(raw);
  if (!n) return res(false, "format");
  const v = n.value, c = parseFracString(task.answer.value);
  if (eq(v, c)) {
    if (task.strict && n.raw && (Math.abs(n.raw[0]) !== Math.abs(c[0]) || n.raw[1] !== c[1])) return res(false, "not_simplified");
    return res(true, null);
  }
  for (const d of task.distractors) if (eq(v, parseFracString(d.value))) return res(false, d.error);
  if (c[0] !== 0 && eq(v, [-c[0], c[1]])) return res(false, "sign");
  if (c[0] !== 0) {
    for (const [mp, mq] of [[10, 1], [100, 1], [1, 10], [1, 100]]) if (eq(v, frac(c[0] * mp, c[1] * mq))) return res(false, "decimal_point");
    const rel = Math.abs(v[0] / v[1] - c[0] / c[1]) / Math.abs(c[0] / c[1]);
    if (rel <= 0.15 + 1e-12) return res(false, "computation");
  }
  return res(false, "other");
}


if (typeof module !== "undefined") module.exports = { check, parseNumber, parseSet };
