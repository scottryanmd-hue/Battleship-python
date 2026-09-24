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
      if (clickable) cell.addEventListener("click", () => fireAt(r, c));
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
  badge.textContent = team === "devin" ? "◉" : "◆";
  badge.style.left = `${w / 2 - 6}px`;
  badge.style.top = `${h / 2 - 18}px`;
  node.append(badge);

  const hits = new Set((ship.hits || []).map(([r, c]) => `${r},${c}`));
  shipCells(ship).forEach(([r, c], i) => {
    if (!hits.has(`${r},${c}`)) return;
    const pip = document.createElement("div");
    pip.className = "pip";
    pip.textContent = ship.sunk ? "#" : "✸";
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
  paintFleet(el("home-fleet"), state.home.fleet);
  paintFleet(el("away-fleet"), state.away.fleet);
  el("log").innerHTML = state.log.map((line) => `<li>${line}</li>`).join("");
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
  missile.textContent = team === "devin" ? "◉➤" : "➤◆";
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
  node.className = "boom";
  node.textContent = glyph;
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

async function finisher(team, shipName) {
  const overlay = el("finisher");
  if (team === "devin") {
    overlay.innerHTML =
      '<div class="party-stage">' +
      '<img class="otter-pic" src="otter.png" alt="The Devin otter celebrating">' +
      `<div class="party-banner">${shipName || "Cursor ship"} sunk!</div>` +
      "</div>";
    overlay.classList.add("show", "party");
    await fireworks(2600);
    await sleep(300);
    overlay.classList.remove("show", "party");
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
      await boom(ev.team, ev.row, ev.col, "✸");
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
  busy = true;
  say("");
  try {
    const data = await api("/api/fire", { row, col });
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

const NUMBERS = {
  one: 1, won: 1, two: 2, to: 2, too: 2, three: 3, tree: 3, four: 4, for: 4, fore: 4,
  five: 5, fife: 5, six: 6, sex: 6, seven: 7, eight: 8, ate: 8, ait: 8, nine: 9, niner: 9,
  nein: 9, ten: 10,
};
const LETTER_WORDS = {
  alpha: "A", apple: "A", hey: "A", bee: "B", be: "B", bravo: "B", see: "C", sea: "C",
  charlie: "C", dee: "D", delta: "D", the: "D", echo: "E", ee: "E", ef: "F", foxtrot: "F",
  gee: "G", golf: "G", jee: "G", ji: "G", aitch: "H", haych: "H", hotel: "H", eye: "I",
  india: "I", aye: "A", ay: "A", jay: "J", jai: "J", juliet: "J",
};

/** "fire at D five" / "launch sonar on g-8" / "d5" -> "D5" */
function parseSpeech(text) {
  const clean = text.toLowerCase().replace(/[.,!?]/g, " ").replace(/[-–]/g, " ");
  const tight = clean.replace(/\s+/g, "");
  const direct = tight.match(/([a-j])(10|[1-9])(?!\d)/);
  if (direct) return direct[1].toUpperCase() + direct[2];

  const words = clean.split(/\s+/).filter(Boolean);
  let letter = null;
  let number = null;
  for (const word of words) {
    const asLetter = /^[a-j]$/.test(word) ? word.toUpperCase() : LETTER_WORDS[word];
    const asNumber = /^\d+$/.test(word) ? parseInt(word, 10) : NUMBERS[word];
    if (letter === null && asLetter) {
      letter = asLetter;
      continue;
    }
    if (number === null && asNumber >= 1 && asNumber <= 10) number = asNumber;
  }
  return letter && number ? `${letter}${number}` : null;
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
    say(`Firing at ${coord}.`);
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
