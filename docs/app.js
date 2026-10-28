"use strict";
/* Эхо — доступный тренажёр ОГЭ по математике.
   Работает целиком в браузере: задания, проверка и прогресс не покидают устройство. */

/* ================================================================ утилиты */
const $ = (s, r = document) => r.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const main = () => $("#main");
function shuffle(a, rnd = Math.random) {
  a = a.slice();
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}
const lcFirst = (s) => s.charAt(0).toLowerCase() + s.slice(1);   // «Делимость, НОД и НОК» → «делимость, НОД и НОК»
function plural(n, one, few, many) {
  const k = n % 100, d = n % 10;
  return `${n} ${k >= 11 && k <= 14 ? many : d === 1 ? one : d >= 2 && d <= 4 ? few : many}`;
}

/* ================================================================ хранилище (только на этом устройстве) */
const store = {
  get(key, def) { try { const v = localStorage.getItem("echo:" + key); return v === null ? def : JSON.parse(v); } catch (_) { return def; } },
  set(key, val) { try { localStorage.setItem("echo:" + key, JSON.stringify(val)); } catch (_) { /* приватный режим */ } },
};
const DEFAULTS = { voice: true, rate: 1, voiceName: "", scale: 1, contrast: "normal", onboarded: false };
let settings = Object.assign({}, DEFAULTS, store.get("settings", {}));
function saveSettings() { store.set("settings", settings); applySettings(); }
function applySettings() {
  document.documentElement.style.setProperty("--scale", settings.scale);
  document.documentElement.dataset.contrast = settings.contrast;
}
applySettings();

/* ================================================================ речь */
const speech = {
  supported: "speechSynthesis" in window,
  voices: [],
  loadVoices() {
    if (!this.supported) return;
    this.voices = speechSynthesis.getVoices().filter((v) => /^ru/i.test(v.lang));
  },
  voice() {
    return this.voices.find((v) => v.name === settings.voiceName) || this.voices.find((v) => /ru-RU/i.test(v.lang)) || this.voices[0] || null;
  },
  say(text, { interrupt = true } = {}) {
    if (!settings.voice || !this.supported || !text) return;
    if (interrupt) speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "ru-RU";
    const v = this.voice();
    if (v) u.voice = v;
    u.rate = settings.rate;
    u.onstart = () => ($("#speaking").hidden = false);
    u.onend = u.onerror = () => { if (!speechSynthesis.speaking) $("#speaking").hidden = true; };
    speechSynthesis.speak(u);
  },
  stop() { if (this.supported) speechSynthesis.cancel(); $("#speaking").hidden = true; },
};
if (speech.supported) {
  speech.loadVoices();
  speechSynthesis.onvoiceschanged = () => speech.loadVoices();
}

/* объявление для экранного диктора (и голосом, если озвучка включена) */
function announce(text, { voice = true } = {}) {
  const a = $("#announcer");
  a.textContent = "";
  setTimeout(() => (a.textContent = text), 60);
  if (voice) speech.say(text);
}

/* ================================================================ данные */
let BANK = null;
const byTopic = {};
async function loadBank() {
  const r = await fetch("bank.json");
  BANK = await r.json();
  for (const t of BANK.tasks) (byTopic[t.topic] ||= []).push(t);
}
const progress = store.get("progress", {});           // { topic: { n, correct } }
function record(topic, ok) {
  const p = (progress[topic] ||= { n: 0, correct: 0 });
  p.n += 1; if (ok) p.correct += 1;
  store.set("progress", progress);
}

/* ================================================================ сессия решения */
let session = null;   // { mode: "exam"|"topic", tasks, i, results, checked, topic }

function pickTask(topic, exclude = new Set()) {
  const pool = byTopic[topic].filter((t) => !exclude.has(t.id));
  return (pool.length ? pool : byTopic[topic])[Math.floor(Math.random() * (pool.length || byTopic[topic].length))];
}

function startExam() {
  const topics = shuffle(BANK.order).slice(0, 15).sort((a, b) => BANK.order.indexOf(a) - BANK.order.indexOf(b));
  session = { mode: "exam", tasks: topics.map((t) => pickTask(t)), i: 0, results: [], checked: false };
  location.hash = "#/task";
}

function startTopic(topic) {
  session = { mode: "topic", topic, tasks: [pickTask(topic)], i: 0, results: [], checked: false, streak: 0, used: new Set() };
  location.hash = "#/task";
}

/* ================================================================ экраны */
function setTitle(t) { document.title = `${t} — Эхо`; }

function focusHeading() {
  const h = $("[data-focus]", main()) || $("h1", main());
  if (h) { h.setAttribute("tabindex", "-1"); h.focus(); }
}

function viewHome() {
  setTitle("Главная");
  const done = Object.values(progress).reduce((s, p) => s + p.n, 0);
  let h = `<h1 data-focus>ОГЭ по математике, который можно слушать</h1>
    <p class="lead">Эхо читает задания вслух — вместе с формулами, — проверяет ответ, объясняет ошибку и подсказывает, какие темы повторить. Подходит для незрячих и слабовидящих школьников и работает без интернета после первого открытия.</p>`;
  if (!settings.onboarded) {
    h += `<section class="card" aria-labelledby="mode-title"><h2 id="mode-title">Как вам удобнее заниматься?</h2>
      <div class="big-choices">
        <button class="btn" data-mode="voice">Эхо читает задания вслух<small>Встроенный голос. Подходит, если вы не пользуетесь экранным диктором.</small></button>
        <button class="btn" data-mode="sr">Я пользуюсь экранным диктором<small>VoiceOver, NVDA, JAWS, TalkBack. Встроенный голос выключится, диктор прочитает формулы словами.</small></button>
        <button class="btn" data-mode="large">Крупный текст, без звука<small>Увеличенный шрифт и высокий контраст.</small></button>
      </div><p class="muted">Это можно изменить в любой момент в настройках.</p></section>`;
  }
  h += `<div class="big-choices">
      <a class="btn primary" href="#/exam">Пробный вариант<small>15 заданий по разным темам ОГЭ и разбор, что повторить</small></a>
      <a class="btn" href="#/topics">Тренировка по теме<small>${BANK.order.length} тем: от действий с дробями до квадратных неравенств</small></a>
    </div>`;
  if (done) h += `<p class="muted">Вы решили ${plural(done, "задание", "задания", "заданий")}. Прогресс хранится только на этом устройстве.</p>`;
  main().innerHTML = h;
  main().querySelectorAll("[data-mode]").forEach((b) => b.addEventListener("click", () => {
    const m = b.dataset.mode;
    if (m === "voice") Object.assign(settings, { voice: true });
    if (m === "sr") Object.assign(settings, { voice: false });
    if (m === "large") Object.assign(settings, { voice: false, scale: 1.4, contrast: "high" });
    settings.onboarded = true;
    saveSettings();
    announce(m === "voice" ? "Озвучка включена." : m === "sr" ? "Встроенный голос выключен. Формулы будут доступны экранному диктору словами." : "Включены крупный шрифт и высокий контраст.");
    viewHome();
  }));
  focusHeading();
}

function viewExamIntro() {
  setTitle("Пробный вариант");
  main().innerHTML = `<h1 data-focus>Пробный вариант</h1>
    <p class="lead">15 заданий по разным темам ОГЭ, от простых к сложным. После каждого ответа вы сразу узнаете, верно ли, а в конце — какие темы стоит повторить в первую очередь.</p>
    <div class="actions"><button class="btn primary" id="go">Начать</button>
    <button class="btn" id="print">Распечатать крупным шрифтом</button></div>
    <p class="muted">Печатная версия — шрифт 20 пунктов, ответы на отдельной странице.</p>`;
  $("#go").addEventListener("click", startExam);
  $("#print").addEventListener("click", printExam);
  focusHeading();
}

function printExam() {
  const topics = shuffle(BANK.order).slice(0, 15).sort((a, b) => BANK.order.indexOf(a) - BANK.order.indexOf(b));
  const tasks = topics.map((t) => pickTask(t));
  $("#print-area").innerHTML = `<h1>ОГЭ по математике — тренировочный вариант</h1>
    <ol>${tasks.map((t) => `<li>${esc(t.text)}<span class="line"></span></li>`).join("")}</ol>
    <div class="key"><h1>Ответы</h1><ol>${tasks.map((t) => `<li>${esc(t.key)}</li>`).join("")}</ol></div>`;
  window.print();
}

function viewTopics() {
  setTitle("Тренировка по теме");
  let h = `<h1 data-focus>Тренировка по теме</h1><p class="lead">Выберите тему. Задания идут без ограничения: после трёх верных ответов подряд Эхо предложит перейти дальше.</p><ul class="topics">`;
  let grade = null;
  for (const id of BANK.order) {
    const t = BANK.topics[id];
    if (t.grade !== grade) { grade = t.grade; h += `</ul><h2>${grade} класс</h2><ul class="topics">`; }
    const p = progress[id];
    const meta = p ? `решено ${p.correct} из ${p.n}` : "ещё не решали";
    h += `<li><a href="#/topic/${id}"><span>${esc(t.name)}</span><span class="meta">${meta}</span></a></li>`;
  }
  h += `</ul>`;
  main().innerHTML = h.replace('<ul class="topics"></ul>', "");
  focusHeading();
}

function currentTask() { return session.tasks[session.i]; }

function viewTask() {
  if (!session) { location.hash = "#/"; return; }
  const t = currentTask();
  const topic = BANK.topics[t.topic];
  const exam = session.mode === "exam";
  const pos = exam ? `Задание ${session.i + 1} из ${session.tasks.length}` : `Задание ${session.i + 1}`;
  setTitle(pos);
  const hint = BANK.hints[t.answer.kind];
  main().innerHTML = `
    <div class="task-head"><span>${pos}</span><span>Тема: ${esc(topic.name)}</span></div>
    ${exam ? `<div class="progressbar" aria-hidden="true"><span style="width:${(session.i / session.tasks.length) * 100}%"></span></div>` : ""}
    <h1 class="sr-only">${pos}. ${esc(topic.name)}</h1>
    <p class="task-text" data-focus>
      <span aria-hidden="true">${esc(t.text)}</span>
      <span class="sr-only">${esc(t.speech)}</span>
    </p>
    <div class="actions">
      <button class="btn" id="read">Прочитать задание <span class="kbd">Alt+1</span></button>
    </div>
    <form id="answer-form" autocomplete="off" novalidate>
      <div class="answer-row">
        <label class="field">Ваш ответ
          <input type="text" id="answer" inputmode="text" aria-describedby="answer-hint" autocapitalize="off" spellcheck="false">
        </label>
        <button class="btn primary" type="submit" id="submit">Проверить <span class="kbd">Enter</span></button>
      </div>
      <p class="hint" id="answer-hint">${esc(hint)}</p>
    </form>
    <div id="feedback"></div>
    <div class="actions">
      ${!exam ? `<a class="btn" href="#/topics">Другая тема</a>` : ""}
      <a class="btn" href="#/" id="quit">Завершить</a>
    </div>`;
  $("#read").addEventListener("click", () => speech.say(t.speech));
  $("#answer-form").addEventListener("submit", (e) => { e.preventDefault(); session.checked ? next() : submit(); });
  $("#quit").addEventListener("click", (e) => {
    speech.stop();
    if (exam && session.results.length) { e.preventDefault(); location.hash = "#/result"; }
  });
  const input = $("#answer");
  input.focus();
  // озвучиваем задание сразу, если включён встроенный голос
  speech.say(`${pos}. ${t.speech}`);
}

function submit() {
  const t = currentTask();
  const raw = $("#answer").value;
  const r = check(t, raw, BANK.errors);
  if (r.error === "no_answer" || r.error === "format") {
    const msg = r.error === "no_answer" ? "Введите ответ." : "Не удалось прочитать ответ. " + BANK.hints[t.answer.kind];
    renderFeedback(null, msg, null);
    announce(msg);
    return;
  }
  session.checked = true;
  session.results.push({ task: t, raw, ...r });
  record(t.topic, r.correct);
  let spoken, visual;
  if (r.correct) {
    spoken = visual = "Верно!";
    if (session.mode === "topic") {
      session.streak = (session.streak || 0) + 1;
      if (session.streak >= 3) {
        const more = " Три верных ответа подряд — тема держится. Можно перейти к другой теме или продолжить.";
        spoken += more; visual += more;
      }
    }
  } else {
    session.streak = 0;
    const why = r.error === "computation" ? " Ответ близок к верному — проверьте вычисления."
      : r.error && r.error !== "other" ? ` Похоже, ${r.label}.` : "";
    spoken = `Неверно.${why} Правильный ответ: ${t.key_speech}.`;
    visual = `Неверно.${why} Правильный ответ: ${t.key}.`;
  }
  renderFeedback(r.correct, visual, t);
  $("#submit").innerHTML = `Дальше <span class="kbd">Enter</span>`;
  $("#answer").setAttribute("readonly", "");
  announce(spoken);
}

function renderFeedback(ok, text, t) {
  const fb = $("#feedback");
  const body = text.replace(/^(Верно!|Неверно\.)\s*/, "");
  fb.innerHTML = `<div class="feedback ${ok === true ? "ok" : ok === false ? "bad" : ""}">
      <p class="verdict">${esc(ok === true ? "Верно" : ok === false ? "Неверно" : "Внимание")}</p>
      ${body ? `<p>${esc(body)}</p>` : ""}
      ${t ? `<button class="btn" id="explain" type="button">Объяснение <span class="kbd">Alt+2</span></button>
      <div class="solution" id="solution" hidden><p><span aria-hidden="true">${esc(t.solution)}</span><span class="sr-only">${esc(t.solution_speech)}</span></p></div>` : ""}
    </div>`;
  const ex = $("#explain");
  if (ex) ex.addEventListener("click", explain);
}

function explain() {
  const t = currentTask();
  const sol = $("#solution");
  if (!sol) return;
  sol.hidden = false;
  speech.say("Решение. " + t.solution_speech);
  $("#announcer").textContent = "Решение показано ниже.";
}

function next() {
  speech.stop();
  session.checked = false;
  if (session.mode === "exam") {
    if (session.i + 1 >= session.tasks.length) { location.hash = "#/result"; return; }
    session.i += 1;
  } else {
    session.used.add(currentTask().id);
    session.tasks.push(pickTask(session.topic, session.used));
    session.i += 1;
  }
  viewTask();
}

/* С чего начать: проваленная тема, все базовые темы которой (из проверенных) решены, — «корень»;
   проваленная тема с проваленной базовой — «следствие». */
function analyzeExam(results) {
  const failed = new Set(results.filter((r) => !r.correct).map((r) => r.task.topic));
  const roots = [], symptoms = [];
  for (const t of failed) {
    const anc = BANK.topics[t].ancestors;
    (anc.some((a) => failed.has(a)) ? symptoms : roots).push(t);
  }
  return { roots, symptoms };
}

function viewResult() {
  if (!session || !session.results.length) { location.hash = "#/"; return; }
  setTitle("Результат");
  const res = session.results;
  const correct = res.filter((r) => r.correct).length;
  const { roots, symptoms } = analyzeExam(res);
  const name = (id) => BANK.topics[id].name;
  let summary = `Решено ${correct} из ${plural(res.length, "задания", "заданий", "заданий")}.`;
  if (roots.length) summary += ` Начните с тем: ${roots.map((r) => lcFirst(name(r))).join(", ")}.`;
  if (symptoms.length) summary += ` Ошибки в темах ${symptoms.map((r) => lcFirst(name(r))).join(", ")} могут уйти сами, когда закроете базу.`;
  if (!roots.length && !symptoms.length) summary += " Отличный результат!";
  let h = `<h1 data-focus>Результат</h1>
    <p class="result-score" aria-hidden="true">${correct} / ${res.length}</p>
    <p class="lead">${esc(summary)}</p>`;
  if (roots.length) {
    h += `<h2>С чего начать</h2><div class="actions">${roots.map((r) => `<button class="btn primary" data-topic="${r}">Тренировать: ${esc(name(r))}</button>`).join("")}</div>`;
  }
  h += `<h2>Все задания</h2><ol class="result-list">${res.map((r) => `<li><span class="mark ${r.correct ? "ok" : "bad"}">${r.correct ? "Верно" : "Нет"}</span>
      <span>${esc(name(r.task.topic))}${r.correct ? "" : ` — ваш ответ ${esc(r.raw)}, верный ${esc(r.task.key)}${r.label && r.error !== "other" ? `; ${esc(r.label)}` : ""}`}</span></li>`).join("")}</ol>
    <div class="actions"><button class="btn" id="again">Новый вариант</button><a class="btn" href="#/">На главную</a></div>`;
  main().innerHTML = h;
  main().querySelectorAll("[data-topic]").forEach((b) => b.addEventListener("click", () => startTopic(b.dataset.topic)));
  $("#again").addEventListener("click", startExam);
  focusHeading();
  speech.say(summary);
}

function viewSettings() {
  setTitle("Настройки");
  const voices = speech.voices;
  main().innerHTML = `<h1 data-focus>Настройки</h1><div class="settings">
    <label class="toggle"><input type="checkbox" id="s-voice" ${settings.voice ? "checked" : ""}> Читать задания встроенным голосом</label>
    <p class="hint">Если вы пользуетесь экранным диктором, выключите — диктор сам прочитает формулы словами.</p>
    ${!speech.supported ? `<p class="hint">Ваш браузер не поддерживает синтез речи — используйте экранный диктор.</p>` :
      !voices.length ? `<p class="hint">Русский голос в системе не найден. Установите его в настройках речи устройства или используйте экранный диктор.</p>` :
      `<label class="setting"><span>Голос</span><select id="s-voicename">${voices.map((v) => `<option ${v.name === (speech.voice() || {}).name ? "selected" : ""}>${esc(v.name)}</option>`).join("")}</select></label>`}
    <label class="setting"><span>Скорость речи: <output id="rate-out">${settings.rate}</output></span>
      <input type="range" id="s-rate" min="0.6" max="1.8" step="0.1" value="${settings.rate}"></label>
    <div class="setting"><span id="size-label">Размер текста</span><div class="seg" role="group" aria-labelledby="size-label">
      ${[[1, "обычный"], [1.25, "крупный"], [1.5, "очень крупный"], [1.8, "максимальный"]].map(([v, n]) => `<button class="btn" data-scale="${v}" aria-pressed="${settings.scale == v}">${n}</button>`).join("")}</div></div>
    <div class="setting"><span id="contrast-label">Цветовая схема</span><div class="seg" role="group" aria-labelledby="contrast-label">
      <button class="btn" data-contrast="normal" aria-pressed="${settings.contrast === "normal"}">Обычная</button>
      <button class="btn" data-contrast="high" aria-pressed="${settings.contrast === "high"}">Высокий контраст: жёлтый на чёрном</button></div></div>
    <div class="actions"><button class="btn" id="s-test">Проверить голос</button><button class="btn" id="s-reset">Сбросить прогресс</button></div>
  </div>`;
  $("#s-voice").addEventListener("change", (e) => { settings.voice = e.target.checked; saveSettings(); announce(settings.voice ? "Озвучка включена" : "Озвучка выключена", { voice: settings.voice }); });
  const vn = $("#s-voicename");
  if (vn) vn.addEventListener("change", (e) => { settings.voiceName = e.target.value; saveSettings(); });
  $("#s-rate").addEventListener("input", (e) => { settings.rate = +e.target.value; $("#rate-out").textContent = settings.rate; saveSettings(); });
  main().querySelectorAll("[data-scale]").forEach((b) => b.addEventListener("click", () => { settings.scale = +b.dataset.scale; saveSettings(); viewSettings(); $(`[data-scale="${b.dataset.scale}"]`).focus(); }));
  main().querySelectorAll("[data-contrast]").forEach((b) => b.addEventListener("click", () => { settings.contrast = b.dataset.contrast; saveSettings(); viewSettings(); $(`[data-contrast="${b.dataset.contrast}"]`).focus(); }));
  $("#s-test").addEventListener("click", () => { const v = settings.voice; settings.voice = true; speech.say("Икс в квадрате минус пять икс плюс шесть равно нулю."); settings.voice = v; });
  $("#s-reset").addEventListener("click", () => {
    for (const k of Object.keys(progress)) delete progress[k];
    store.set("progress", progress);
    announce("Прогресс сброшен.");
  });
  focusHeading();
}

function viewHelp() {
  setTitle("Как пользоваться");
  main().innerHTML = `<h1 data-focus>Как пользоваться</h1>
    <h2>Ответы</h2>
    <p>Целое число вводите как обычно, отрицательное — со знаком минус. Дробь — через косую черту (3/4) или десятичной дробью через запятую (0,75). Несколько корней — через точку с запятой. Если корней нет — слово «нет».</p>
    <h2>Клавиши</h2>
    <dl class="keys">
      <dt><kbd>Enter</kbd></dt><dd>проверить ответ, затем — перейти к следующему заданию</dd>
      <dt><kbd>Alt</kbd> + <kbd>1</kbd></dt><dd>прочитать задание ещё раз</dd>
      <dt><kbd>Alt</kbd> + <kbd>2</kbd></dt><dd>объяснение решения (после проверки)</dd>
      <dt><kbd>Alt</kbd> + <kbd>3</kbd></dt><dd>повторить подсказку о формате ответа</dd>
      <dt><kbd>Esc</kbd></dt><dd>остановить речь</dd>
    </dl>
    <h2>Как читаются формулы</h2>
    <p>Эхо проговаривает математику словами, как учитель у доски: «икс в квадрате минус пять икс», «дробь: числитель три, знаменатель четыре», «квадратный корень из выражения…, конец корня». Экранный диктор получает тот же текст.</p>
    <h2>Без интернета</h2>
    <p>После первого открытия Эхо сохраняется в браузере и работает без подключения. Ответы и прогресс никуда не отправляются.</p>
    <h2>Для учителя</h2>
    <p>Задания создаются программой, а ответы вычисляются автоматически, поэтому ключ гарантированно верный. Вариант можно распечатать крупным шрифтом (20 пт) с ответами на отдельной странице.</p>`;
  focusHeading();
}

/* ================================================================ клавиши и роутинг */
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") { speech.stop(); return; }
  if (!e.altKey || !session || !location.hash.startsWith("#/task")) return;
  const t = currentTask();
  if (e.code === "Digit1") { e.preventDefault(); speech.say(t.speech); $("#announcer").textContent = t.speech; }
  if (e.code === "Digit2") { e.preventDefault(); if (session.checked) explain(); }
  if (e.code === "Digit3") { e.preventDefault(); announce(BANK.hints[t.answer.kind]); }
});

function route() {
  const h = location.hash || "#/";
  speech.stop();
  if (h === "#/" || h === "") return viewHome();
  if (h === "#/exam") return viewExamIntro();
  if (h === "#/topics") return viewTopics();
  if (h.startsWith("#/topic/")) {
    const id = h.slice(8);
    if (BANK.topics[id]) { startTopic(id); return; }
    return viewTopics();
  }
  if (h === "#/task") return viewTask();
  if (h === "#/result") return viewResult();
  if (h === "#/settings") return viewSettings();
  if (h === "#/help") return viewHelp();
  viewHome();
}

(async function init() {
  main().innerHTML = `<p>Загрузка заданий…</p>`;
  try {
    await loadBank();
  } catch (e) {
    main().innerHTML = `<h1>Не удалось загрузить задания</h1><p>Проверьте подключение к интернету и обновите страницу.</p>`;
    return;
  }
  window.addEventListener("hashchange", route);
  route();
  if ("serviceWorker" in navigator && location.protocol === "https:") navigator.serviceWorker.register("sw.js").catch(() => {});
})();
