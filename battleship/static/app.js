/* Battleship Channel — browser front-end.
   The Python side owns the rules; this file draws the board in 3/4 view,
   animates the missiles, and turns speech into coordinates. */

const SIZE = 10;
const LETTERS = "ABCDEFGHIJ";
const CELL = 40;

const el = (id) => document.getElementById(id);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let state = null;
let busy = false;
let swarmOn = false;
let fusionArmed = false;

/* ---------- board drawing ---------- */

function buildGrid(node, clickable) {
  node.innerHTML = "";
  const rows = document.createElement("div");
  rows.className = "rowlabels";
  const cols = document.createElement("div");
  cols.className = "collabels";
  for (let i = 0; i < SIZE; i++) {
    rows.insertAdjacentHTML("beforeend", `<span>${LETTERS[i]}</span>`);
    cols.insertAdjacentHTML("beforeend", `<span>${i + 1}</span>`);
  }
  node.append(rows, cols);
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      const cell = document.createElement("div");
      cell.className = "cell";
      cell.dataset.row = r;
      cell.dataset.col = c;
      if (clickable) {
        cell.innerHTML = '<span class="odds"></span>';
        cell.addEventListener("click", () => fireAt(r, c));
      }
      node.append(cell);
    }
  }
}

function shipCells(ship) {
  return Array.from({ length: ship.size }, (_, i) => [
    ship.row + (ship.horizontal ? 0 : i),
    ship.col + (ship.horizontal ? i : 0),
  ]);
}

function shipNode(ship, team) {
  const node = document.createElement("div");
  node.className = `ship ${team} ${ship.horizontal ? "horizontal" : "vertical"}`;
  if (ship.sunk) node.classList.add("sunk");
  const w = (ship.horizontal ? ship.size : 1) * CELL;
  const h = (ship.horizontal ? 1 : ship.size) * CELL;
  Object.assign(node.style, {
    left: `${ship.col * CELL}px`,
    top: `${ship.row * CELL}px`,
    width: `${w}px`,
    height: `${h}px`,
  });

  const hull = document.createElement("div");
  hull.className = "hull";
  node.append(hull);

  // Superstructure: a deckhouse a third of the way back, plus a funnel.
  const deck = document.createElement("div");
  deck.className = "deck";
  if (ship.horizontal) {
    Object.assign(deck.style, {
      left: `${CELL * 0.9}px`, top: "26%", width: `${CELL * (ship.size - 2.1)}px`, height: "48%",
    });
  } else {
    Object.assign(deck.style, {
      top: `${CELL * 0.9}px`, left: "26%", height: `${CELL * (ship.size - 2.1)}px`, width: "48%",
    });
  }
  node.append(deck);

  const funnel = document.createElement("div");
  funnel.className = "funnel";
  funnel.style.left = `${w / 2 - 5}px`;
  funnel.style.top = `${h / 2 - 5}px`;
  node.append(funnel);

  const badge = document.createElement("div");
  badge.className = "badge";
  if (team === "devin") badge.innerHTML = '<span class="logo"></span>';
  else badge.textContent = "◆";
  badge.style.left = `${w / 2 - 6}px`;
  badge.style.top = `${h / 2 - 18}px`;
  node.append(badge);

  const hits = new Set((ship.hits || []).map(([r, c]) => `${r},${c}`));
  shipCells(ship).forEach(([r, c], i) => {
    if (!hits.has(`${r},${c}`)) return;
    const pip = document.createElement("div");
    pip.className = "pip";
    if (team === "cursor") pip.innerHTML = '<span class="logo"></span>';
    else pip.textContent = ship.sunk ? "#" : "✸";
    pip.style.left = `${ship.horizontal ? i * CELL : 0}px`;
    pip.style.top = `${ship.horizontal ? 0 : i * CELL}px`;
    node.append(pip);
  });
  return node;
}

function paintBoard(node, board, team) {
  node.querySelectorAll(".ship").forEach((s) => s.remove());
  node.querySelectorAll(".cell").forEach((cell) => {
    const mark = board.grid[cell.dataset.row][cell.dataset.col];
    cell.classList.toggle("miss", mark === "o");
    cell.classList.toggle("hit", mark === "x");
    cell.classList.toggle("sunk", mark === "#");
  });
  board.ships.forEach((ship) => node.append(shipNode(ship, team)));
}

function paintFleet(node, fleet) {
  node.innerHTML = fleet
    .map((s) => {
      const pips = Array.from({ length: s.size }, (_, i) =>
        i < s.hits ? '<span class="hit">✸</span>' : "▰"
      ).join("");
      return `<li class="${s.sunk ? "sunk" : ""}"><span>${s.name}</span><span class="pips">${pips}</span></li>`;
    })
    .join("");
}

function meterRow(label, left, right, total, color) {
  const pct = (v) => `${Math.min(100, (v / Math.max(1, total)) * 100)}%`;
  return `<div class="meter-row">
      <span class="count">${left}</span>
      <span class="bar left"><span style="width:${pct(left)};background:${color}"></span></span>
      <span class="label">${label}</span>
      <span class="bar"><span style="width:${pct(right)};background:${color}"></span></span>
      <span class="count">${right}</span>
    </div>`;
}

function paint() {
  const s = state.stats;
  el("big-score").textContent = `${s.devin_sunk} – ${s.cursor_sunk}`;
  el("round").textContent = state.turn;
  const shots = Math.max(1, s.devin_hits + s.devin_misses, s.cursor_hits + s.cursor_misses);
  el("meters").innerHTML =
    meterRow("HITS", s.devin_hits, s.cursor_hits, shots, "#d0342c") +
    meterRow("MISSES", s.devin_misses, s.cursor_misses, shots, "#1c8ad6") +
    meterRow("SHIPS SUNK", s.devin_sunk, s.cursor_sunk, 5, "#e2a11b") +
    meterRow("FLEET LEFT", s.devin_alive, s.cursor_alive, 5, "#2f9e44");

  paintBoard(el("home-grid"), state.home, "devin");
  paintBoard(el("away-grid"), state.away, "cursor");
  paintSwarm();
  paintFleet(el("home-fleet"), state.home.fleet);
  paintFleet(el("away-fleet"), state.away.fleet);
  el("log").innerHTML = state.log.map((line) => `<li>${line}</li>`).join("");
}

/* ---------- Devin Security Swarm ---------- */

/* Cold red for the unlikely squares, orange for the plausible ones, green where
   the density engine says a hull is hiding. */
function heatColour(score) {
  if (score >= 0.85) return "rgba(47, 174, 87, 0.75)";
  if (score >= 0.6) return "rgba(232, 137, 43, 0.6)";
  if (score >= 0.3) return "rgba(214, 96, 46, 0.45)";
  return "rgba(192, 57, 43, 0.3)";
}

function paintSwarm() {
  const grid = el("away-grid");
  grid.classList.toggle("swarm", swarmOn);
  const swarm = state && state.swarm;
  const best = swarmOn && swarm ? swarm.best : null;
  grid.querySelectorAll(".cell").forEach((cell) => {
    const row = Number(cell.dataset.row);
    const col = Number(cell.dataset.col);
    const score = swarm ? swarm.heat[row][col] : 0;
    const odds = swarm && swarm.probability ? swarm.probability[row][col] : 0;
    cell.style.setProperty("--heat", score > 0 ? heatColour(score) : "transparent");
    cell.classList.toggle("swarm-best", best === `${LETTERS[row]}${col + 1}`);
    const label = cell.querySelector(".odds");
    if (label) {
      const exact = swarm && swarm.method === "posterior";
      label.textContent = swarmOn && score > 0 && exact ? `${Math.round(odds * 100)}%` : "";
    }
  });

  if (!swarmOn) {
    el("swarm-note").textContent = "Devin team only — Cursor fires blind. Heat map off.";
    return;
  }
  if (!swarm || !swarm.best) {
    el("swarm-note").textContent = "Swarm intel: nothing left to model.";
    return;
  }
  const peak = swarm.probability
    ? Math.round(Math.max(...swarm.probability.flat()) * 100)
    : null;
  el("swarm-note").textContent =
    swarm.method === "posterior"
      ? `Swarm intel: ${swarm.best} holds a hull in ${peak}% of the layouts still `
        + `possible (${Math.round(swarm.ess)} effective samples).`
      : `Swarm intel: ${swarm.best} — too few layouts fit these hits to sample, `
        + "so this is the placement-density map.";
}

/* ---------- animation ---------- */

function centreOf(grid, row, col) {
  return { x: col * CELL + CELL / 2, y: row * CELL + CELL / 2 };
}

async function flyMissile(team, row, col) {
  const grid = el(team === "devin" ? "away-grid" : "home-grid");
  const target = centreOf(grid, row, col);
  const start = team === "devin"
    ? { x: -60, y: target.y }
    : { x: SIZE * CELL + 60, y: target.y };

  const missile = document.createElement("div");
  missile.className = `missile ${team}`;
  if (team === "devin") missile.innerHTML = '<span class="logo"></span>➤';
  else missile.textContent = "➤◆";
  grid.append(missile);

  const steps = 22;
  for (let i = 0; i <= steps; i++) {
    const t = i / steps;
    const x = start.x + (target.x - start.x) * t;
    const y = start.y + (target.y - start.y) * t - Math.sin(t * Math.PI) * 26;
    missile.style.left = `${x}px`;
    missile.style.top = `${y}px`;
    if (i % 2 === 0) {
      const puff = document.createElement("div");
      puff.className = "smoke";
      puff.textContent = "·";
      puff.style.left = `${x}px`;
      puff.style.top = `${y}px`;
      grid.append(puff);
      setTimeout(() => puff.remove(), 900);
    }
    await sleep(22);
  }
  missile.remove();
}

async function boom(team, row, col, glyph, size) {
  const grid = el(team === "devin" ? "away-grid" : "home-grid");
  const at = centreOf(grid, row, col);
  const node = document.createElement("div");
  node.className = glyph === "logo" ? "boom logo" : "boom";
  if (glyph !== "logo") node.textContent = glyph;
  node.style.left = `${at.x}px`;
  node.style.top = `${at.y}px`;
  if (size) node.style.fontSize = size;
  grid.append(node);
  await sleep(650);
  node.remove();
}

const SPARK_COLOURS = ["#ffd84d", "#ff8a3d", "#ff5f6d", "#7ce7ff", "#b689ff", "#8dff9e"];

function burst(x, y) {
  const hue = SPARK_COLOURS[Math.floor(Math.random() * SPARK_COLOURS.length)];
  const count = 22;
  const spread = 110 + Math.random() * 80;
  for (let i = 0; i < count; i++) {
    const angle = (i / count) * Math.PI * 2 + Math.random() * 0.2;
    const reach = spread * (0.6 + Math.random() * 0.5);
    const spark = document.createElement("div");
    spark.className = "spark";
    spark.style.left = `${x}px`;
    spark.style.top = `${y}px`;
    spark.style.setProperty("--dx", `${Math.cos(angle) * reach}px`);
    spark.style.setProperty("--dy", `${Math.sin(angle) * reach}px`);
    spark.style.setProperty("--spark", hue);
    spark.style.setProperty("--life", `${0.9 + Math.random() * 0.6}s`);
    document.body.append(spark);
    setTimeout(() => spark.remove(), 1600);
  }
}

function launchFirework() {
  const x = window.innerWidth * (0.12 + Math.random() * 0.76);
  const peak = window.innerHeight * (0.12 + Math.random() * 0.3);
  const climb = window.innerHeight - peak;
  const rocket = document.createElement("div");
  rocket.className = "rocket";
  rocket.style.left = `${x}px`;
  rocket.style.top = `${window.innerHeight}px`;
  rocket.style.setProperty("--climb", `${-climb}px`);
  rocket.style.setProperty("--rise", "0.45s");
  document.body.append(rocket);
  setTimeout(() => {
    rocket.remove();
    burst(x, peak);
  }, 450);
}

async function fireworks(duration = 2600) {
  const until = Date.now() + duration;
  while (Date.now() < until) {
    launchFirework();
    if (Math.random() < 0.5) launchFirework();
    await sleep(260);
  }
}

/* ---------- victory music ----------
   The Karate Kid montage track is copyrighted, so the built-in cue is an
   original 80s-style fanfare synthesised in the browser. Drop your own file at
   `battleship/static/sounds/victory.mp3` and that plays instead. */

const ANTHEM_FILES = [
  "sounds/victory.mp3", "sounds/victory.ogg", "sounds/victory.wav", "sounds/victory.m4a",
];
let anthem = null;
let audioCtx = null;

async function loadAnthem() {
  for (const file of ANTHEM_FILES) {
    try {
      const res = await fetch(file);
      if (!res.ok) continue;
      anthem = new Audio(URL.createObjectURL(await res.blob()));
      return;
    } catch (err) {
      /* keep looking */
    }
  }
}

// [semitones above C4, start beat, beats] — a rising "you did it" fanfare.
const FANFARE = [
  [7, 0, 0.5], [12, 0.5, 0.5], [16, 1, 0.5], [19, 1.5, 1],
  [17, 2.5, 0.5], [16, 3, 0.5], [19, 3.5, 1.5],
  [14, 5, 0.5], [17, 5.5, 0.5], [21, 6, 1.5],
];
const BASSLINE = [[0, 0], [0, 1], [5, 2], [7, 3], [0, 4], [5, 5], [7, 6], [0, 7]];
const BEAT = 0.28;

function pitch(semitones) {
  return 261.63 * Math.pow(2, semitones / 12);
}

function blip(ctx, semitones, at, beats, type, level) {
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = type;
  osc.frequency.value = pitch(semitones);
  const start = ctx.currentTime + at * BEAT;
  const end = start + beats * BEAT;
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(level, start + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, end);
  osc.connect(gain).connect(ctx.destination);
  osc.start(start);
  osc.stop(end + 0.05);
}

function playAnthem() {
  if (anthem) {
    anthem.currentTime = 0;
    anthem.play().catch(() => {});
    return;
  }
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return;
  audioCtx = audioCtx || new Ctx();
  audioCtx.resume();
  FANFARE.forEach(([note, at, beats]) => {
    blip(audioCtx, note, at, beats, "square", 0.14);
    blip(audioCtx, note + 12, at, beats, "triangle", 0.05);
  });
  BASSLINE.forEach(([note, at]) => blip(audioCtx, note - 12, at, 0.9, "sawtooth", 0.09));
}

function stopAnthem() {
  if (anthem) anthem.pause();
}

async function finisher(team, shipName) {
  const overlay = el("finisher");
  if (team === "devin") {
    overlay.innerHTML =
      '<div class="party-stage">' +
      '<img class="otter-pic" src="otter.png" alt="The Devin otter celebrating">' +
      `<div class="party-banner">${shipName || "Cursor ship"} sunk!</div>` +
      "</div>";
    overlay.classList.add("show", "party");
    playAnthem();
    await fireworks(2600);
    await sleep(300);
    overlay.classList.remove("show", "party");
    stopAnthem();
  } else {
    overlay.innerHTML = '<div class="cursor-logo">◆</div>';
    overlay.classList.add("show");
    await sleep(1600);
    overlay.classList.remove("show");
  }
}

function cellNode(team, row, col) {
  const grid = el(team === "devin" ? "away-grid" : "home-grid");
  return grid.querySelector(`.cell[data-row="${row}"][data-col="${col}"]`);
}

async function playEvents(events) {
  for (const ev of events) {
    const aim = cellNode(ev.team, ev.row, ev.col);
    if (aim) aim.classList.add("aim");
    await flyMissile(ev.team, ev.row, ev.col);
    if (aim) setTimeout(() => aim.classList.remove("aim"), 700);
    if (ev.result === "miss") {
      await boom(ev.team, ev.row, ev.col, "o", "1.1rem");
    } else if (ev.result === "hit") {
      await boom(ev.team, ev.row, ev.col, ev.team === "devin" ? "logo" : "✸");
    } else {
      await boom(ev.team, ev.row, ev.col, "💥", "2.2rem");
      await finisher(ev.team, ev.ship);
    }
  }
}

/* ---------- server calls ---------- */

async function api(path, body) {
  const res = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Something went wrong.");
  return data;
}

function disarmFusion() {
  fusionArmed = false;
  el("fusion").setAttribute("aria-pressed", "false");
  el("fusion-note").textContent =
    "Devin team only — arm it and your next called square goes up in a five-missile salvo.";
}

function say(text, isError) {
  const node = el("message");
  node.textContent = text;
  node.style.color = isError ? "#b3261e" : "var(--orange)";
}

async function fireAt(row, col) {
  if (busy) return;
  if (state && state.winner) {
    say("Game over — start a new one.", true);
    return;
  }
  if (state && state.away.grid[row][col] !== " ") {
    say(`${LETTERS[row]}${col + 1} has already been shelled.`, true);
    return;
  }
  const fusion = fusionArmed;
  busy = true;
  say(fusion ? `Devin Fusion: five missiles around ${LETTERS[row]}${col + 1}.` : "");
  if (fusion) disarmFusion();
  try {
    const data = await api(fusion ? "/api/fusion" : "/api/fire", { row, col });
    await playEvents(data.events);
    state = data.state;
    paint();
    if (state.winner) {
      say(state.winner === "devin" ? "🦦 FINAL: DEVIN WINS" : "◆ FINAL: CURSOR WINS");
    }
  } catch (err) {
    say(err.message, true);
  } finally {
    busy = false;
  }
}

/* ---------- speech ---------- */

/* Dictation hears digits as words, and words as the wrong words. Only the
   number slot — the word straight after a letter — is read through this table,
   so a stray "won" in conversation still cannot shell anything. */
const NUMBERS = {
  one: 1, won: 1, wun: 1, juan: 1,
  two: 2, too: 2, to: 2, tu: 2,
  three: 3, tree: 3, free: 3, thre: 3,
  four: 4, for: 4, fore: 4, faux: 4,
  five: 5, fife: 5, hive: 5,
  six: 6, sicks: 6, sex: 6,
  seven: 7, sevin: 7,
  eight: 8, ate: 8, ait: 8, hate: 8,
  nine: 9, niner: 9, nein: 9,
  ten: 10, tin: 10, tan: 10, then: 10,
};
/* Likewise for the row. "I" is the awkward one: spoken alone dictation writes
   it as the pronoun, or as "eye", "hi", "high" or "aye", so every one of those
   has to land on row I. */
const LETTER_WORDS = {
  alpha: "A", apple: "A", ay: "A",
  bee: "B", be: "B", bravo: "B",
  sea: "C", see: "C", cee: "C", charlie: "C",
  dee: "D", de: "D", delta: "D",
  echo: "E", ee: "E", eee: "E",
  ef: "F", eff: "F", foxtrot: "F",
  gee: "G", jee: "G", golf: "G",
  aitch: "H", haych: "H", hotel: "H", age: "H",
  eye: "I", aye: "I", hi: "I", high: "I", india: "I", ai: "I", ii: "I",
  jay: "J", jae: "J", juliet: "J", jail: "J",
};
/* A square only goes up in flames when you actually order the shot: either the phrase carries a
   firing verb, or the whole utterance is nothing but the coordinate. */
const ORDER = /\b(fire|firing|fired|launch|shoot|shot|strike|hit|bomb|target|attack|sonar|missile|square)\b/;

/* Words allowed to sit between the row and the column without breaking the pair. */
const FILLER = new Set(["number", "square", "column", "as", "in", "is", "at", "uh", "um"]);

function word2letter(word) {
  return /^[a-j]$/.test(word) ? word.toUpperCase() : LETTER_WORDS[word] || null;
}

function word2number(word) {
  const value = /^\d+$/.test(word) ? parseInt(word, 10) : NUMBERS[word];
  return value >= 1 && value <= 10 ? value : null;
}

/** "fire at D five" / "launch sonar on g-8" / "I1" -> "D5"; anything vaguer -> null */
function parseSpeech(text) {
  const clean = text
    .toLowerCase()
    .replace(/[.,!?'’"]/g, " ")
    .replace(/[-–—_/]/g, " ");
  const words = clean.split(/\s+/).filter(Boolean);

  let coord = null;
  for (let i = 0; i < words.length && !coord; i += 1) {
    // Dictation's pet mishearing: "I one" comes back as the phone.
    if (words[i] === "iphone") {
      coord = "I1";
      break;
    }
    // "e8", "i1", "i10" — dictation often glues the pair into one token.
    const glued = words[i].match(/^([a-j])\s?(10|[1-9])$/);
    if (glued) {
      coord = glued[1].toUpperCase() + glued[2];
      break;
    }
    const letter = word2letter(words[i]);
    if (!letter) continue;
    // The number can trail by a filler word: "fire at I, number one".
    for (let j = i + 1; j < Math.min(i + 3, words.length) && !coord; j += 1) {
      const number = word2number(words[j]);
      if (number) coord = `${letter}${number}`;
      else if (!FILLER.has(words[j])) break;
    }
  }
  if (!coord) return null;
  return ORDER.test(clean) || words.length <= 3 ? coord : null;
}

function setupMic() {
  const button = el("mic");
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    button.classList.add("unsupported");
    button.disabled = true;
    el("transcript").textContent =
      "This browser has no webkitSpeechRecognition — click a square instead (Chrome supports voice).";
    return;
  }

  const recognition = new Recognition();
  recognition.lang = "en-US";
  recognition.interimResults = true;
  recognition.continuous = false;
  let listening = false;

  recognition.addEventListener("result", (event) => {
    const text = Array.from(event.results).map((r) => r[0].transcript).join(" ");
    el("transcript").textContent = `“${text.trim()}”`;
    if (!event.results[event.results.length - 1].isFinal) return;
    const coord = parseSpeech(text);
    if (!coord) {
      say(`Didn't catch a square in “${text.trim()}” — try “fire at D five”.`, true);
      return;
    }
    say(`Heard “${text.trim()}” — firing at ${coord}.`);
    const row = LETTERS.indexOf(coord[0]);
    fireAt(row, parseInt(coord.slice(1), 10) - 1);
  });
  recognition.addEventListener("error", (event) => {
    say(
      event.error === "not-allowed"
        ? "Microphone blocked — allow mic access in the address bar."
        : `Speech error: ${event.error}`,
      true
    );
  });
  recognition.addEventListener("end", () => {
    listening = false;
    button.classList.remove("listening");
  });

  button.addEventListener("click", () => {
    if (listening) {
      recognition.stop();
      return;
    }
    listening = true;
    button.classList.add("listening");
    el("transcript").textContent = "Listening…";
    recognition.start();
  });
}

/* ---------- boot ---------- */

function tickClock() {
  const now = new Date();
  const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  el("clock").textContent = `${days[now.getDay()]}  ${String(now.getHours()).padStart(2, "0")}:${String(
    now.getMinutes()
  ).padStart(2, "0")}`;
}

async function boot() {
  buildGrid(el("home-grid"), false);
  buildGrid(el("away-grid"), true);
  loadAnthem();
  state = await api("/api/state");
  paint();
  setupMic();
  tickClock();
  setInterval(tickClock, 20000);

  el("new-game").addEventListener("click", async () => {
    state = await api("/api/new", {});
    say("New game. Devin fires first.");
    paint();
  });
  el("fusion").addEventListener("click", () => {
    if (fusionArmed) {
      disarmFusion();
      say("Fusion disarmed.");
      return;
    }
    fusionArmed = true;
    el("fusion").setAttribute("aria-pressed", "true");
    el("fusion-note").textContent =
      "Armed — your next shot lands on that square and the four nearest open ones.";
    say("Devin Fusion armed. Call your square.");
  });
  el("swarm").addEventListener("click", () => {
    swarmOn = !swarmOn;
    el("swarm").setAttribute("aria-pressed", String(swarmOn));
    paintSwarm();
    say(swarmOn ? "Devin Security Swarm online." : "Swarm stood down.");
  });

  el("reroll").addEventListener("click", async () => {
    try {
      state = await api("/api/reroll", {});
      say("Fleet rearranged.");
      paint();
    } catch (err) {
      say(err.message, true);
    }
  });
}

boot();
