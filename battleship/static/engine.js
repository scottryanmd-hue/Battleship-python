/* The whole game, in the browser.
 *
 * `web.py` normally answers the page's /api calls, but a static host (GitHub
 * Pages) has no Python behind it. This is the same rules as `board.py` and
 * `session.py` ported to JavaScript, behind the same tiny API, so app.js cannot
 * tell the difference: `LocalEngine.handle("/api/fire", {row, col})` returns
 * what the server would have returned.
 *
 * The heat map is the placement-density map from `probability.py`, not its
 * Monte Carlo posterior; the page already knows how to label that ("density").
 */

(() => {
  const SIZE = 10;
  const LETTERS = "ABCDEFGHIJ";
  const FLEET = [
    ["Carrier", 5],
    ["Battleship", 4],
    ["Cruiser", 3],
    ["Submarine", 3],
    ["Destroyer", 2],
  ];
  const EXPLOSION_THRESHOLD = 3;
  const FUSION_SHOTS = 2;
  const SWE2_COLUMNS = [1, 4, 6];
  const HIT_WEIGHT = 25;
  const EMPTY = " ";
  const MISS = "o";
  const HIT = "x";
  const SUNK = "#";

  const coord = (row, col) => `${LETTERS[row]}${col + 1}`;
  const key = (row, col) => row * SIZE + col;

  class Board {
    constructor() {
      this.grid = Array.from({ length: SIZE }, () => Array(SIZE).fill(EMPTY));
      this.ships = [];
    }

    placeFleetRandomly() {
      const taken = new Set();
      for (const [name, size] of FLEET) {
        for (;;) {
          const horizontal = Math.random() < 0.5;
          const row = Math.floor(Math.random() * (SIZE - (horizontal ? 0 : size - 1)));
          const col = Math.floor(Math.random() * (SIZE - (horizontal ? size - 1 : 0)));
          const cells = [];
          for (let i = 0; i < size; i += 1) {
            cells.push(horizontal ? [row, col + i] : [row + i, col]);
          }
          if (cells.some(([r, c]) => taken.has(key(r, c)))) continue;
          cells.forEach(([r, c]) => taken.add(key(r, c)));
          this.ships.push({ name, size, cells, hits: new Set(), sunk: false });
          break;
        }
      }
    }

    shipAt(row, col) {
      return this.ships.find((ship) => ship.cells.some(([r, c]) => r === row && c === col));
    }

    alreadyShot(row, col) {
      return this.grid[row][col] !== EMPTY;
    }

    /* [result, ship, exploded] with result "miss" | "hit" | "sunk". */
    fire(row, col) {
      const ship = this.shipAt(row, col);
      if (!ship) {
        this.grid[row][col] = MISS;
        return ["miss", null, false];
      }
      ship.hits.add(key(row, col));
      this.grid[row][col] = HIT;
      const exploded = ship.hits.size >= Math.min(EXPLOSION_THRESHOLD, ship.size);
      if (exploded || ship.hits.size === ship.size) {
        ship.sunk = true;
        ship.cells.forEach(([r, c]) => {
          ship.hits.add(key(r, c));
          this.grid[r][c] = SUNK;
        });
        return ["sunk", ship, exploded];
      }
      return ["hit", ship, false];
    }

    get defeated() {
      return this.ships.length > 0 && this.ships.every((ship) => ship.sunk);
    }
  }

  /* ---------- the swarm's placement-density map ---------- */

  function placements(size) {
    const spots = [];
    for (const horizontal of [true, false]) {
      const rows = horizontal ? SIZE : SIZE - size + 1;
      const cols = horizontal ? SIZE - size + 1 : SIZE;
      for (let row = 0; row < rows; row += 1) {
        for (let col = 0; col < cols; col += 1) {
          const cells = [];
          for (let i = 0; i < size; i += 1) {
            cells.push(horizontal ? [row, col + i] : [row + i, col]);
          }
          spots.push(cells);
        }
      }
    }
    return spots;
  }

  function density(board) {
    const blocked = board.grid.map((row) => row.map((v) => v === MISS || v === SUNK));
    const wounded = board.grid.map((row) => row.map((v) => v === HIT));
    const scores = Array.from({ length: SIZE }, () => Array(SIZE).fill(0));

    for (const ship of board.ships) {
      if (ship.sunk) continue;
      for (const cells of placements(ship.size)) {
        if (cells.some(([r, c]) => blocked[r][c])) continue;
        const hits = cells.filter(([r, c]) => wounded[r][c]).length;
        const weight = 1 + HIT_WEIGHT * hits;
        cells.forEach(([r, c]) => {
          if (!wounded[r][c]) scores[r][c] += weight;
        });
      }
    }

    const peak = Math.max(0, ...scores.flat());
    if (peak <= 0) return scores;
    return scores.map((row) => row.map((v) => Math.round((v / peak) * 1e4) / 1e4));
  }

  /* ---------- one game ---------- */

  class Session {
    constructor() {
      this.player = new Board();
      this.ai = new Board();
      this.player.placeFleetRandomly();
      this.ai.placeFleetRandomly();
      this.aiTargets = [];
      for (let r = 0; r < SIZE; r += 1) {
        for (let c = 0; c < SIZE; c += 1) this.aiTargets.push([r, c]);
      }
      for (let i = this.aiTargets.length - 1; i > 0; i -= 1) {
        const j = Math.floor(Math.random() * (i + 1));
        [this.aiTargets[i], this.aiTargets[j]] = [this.aiTargets[j], this.aiTargets[i]];
      }
      this.turn = 1;
      this.winner = null;
      this.log = ["Wii Sports Resort weather: clear. Devin fires first."];
      this.stats = {
        devin_hits: 0,
        devin_misses: 0,
        devin_sunk: 0,
        cursor_hits: 0,
        cursor_misses: 0,
        cursor_sunk: 0,
      };
    }

    rerollHomeFleet() {
      if (this.turn !== 1 || Object.values(this.stats).some(Boolean)) {
        throw new Error("The battle has started — no rearranging now.");
      }
      this.player = new Board();
      this.player.placeFleetRandomly();
    }

    shoot(team, row, col) {
      const target = team === "devin" ? this.ai : this.player;
      const [result, ship, exploded] = target.fire(row, col);
      const event = {
        team,
        row,
        col,
        coord: coord(row, col),
        result,
        ship: ship ? ship.name : null,
        exploded,
        hits: ship ? ship.hits.size : 0,
      };
      const who = team === "devin" ? "Devin" : "Cursor";
      if (result === "miss") {
        this.stats[`${team}_misses`] += 1;
        this.log.push(`${who} missiles splash down at ${event.coord}.`);
      } else {
        this.stats[`${team}_hits`] += 1;
        if (result === "sunk") {
          this.stats[`${team}_sunk`] += 1;
          const blow = exploded
            ? `${Math.min(EXPLOSION_THRESHOLD, ship.size)} missiles detonate`
            : "The last cell goes under";
          const finisher = team === "devin" ? "the otter flies in" : "Cursor closes in";
          this.log.push(`${blow} the ${ship.name} at ${event.coord} — ${finisher}.`);
        } else {
          this.log.push(`${who} hits the hull at ${event.coord}.`);
        }
      }
      this.log = this.log.slice(-6);
      return event;
    }

    checkTarget(row, col) {
      if (this.winner) throw new Error("The game is already over.");
      if (!(row >= 0 && row < SIZE && col >= 0 && col < SIZE)) {
        throw new Error("That square is off the board.");
      }
      if (this.ai.alreadyShot(row, col)) throw new Error("You already shelled that square.");
    }

    cursorReply(events) {
      let shot = this.aiTargets.pop();
      while (shot && this.player.alreadyShot(shot[0], shot[1])) shot = this.aiTargets.pop();
      if (!shot) return true;
      events.push(this.shoot("cursor", shot[0], shot[1]));
      if (this.player.defeated) {
        this.winner = "cursor";
        return false;
      }
      this.turn += 1;
      return true;
    }

    fire(row, col) {
      this.checkTarget(row, col);
      const events = [this.shoot("devin", row, col)];
      if (this.ai.defeated) {
        this.winner = "devin";
        return events;
      }
      this.cursorReply(events);
      return events;
    }

    fusionTargets(row, col, count = FUSION_SHOTS) {
      const ring = [
        [-1, 0], [0, -1], [0, 1], [1, 0],
        [-1, -1], [-1, 1], [1, -1], [1, 1],
      ];
      const seen = new Set(ring.map(([dr, dc]) => `${dr},${dc}`));
      const rest = [];
      for (let dr = -3; dr <= 3; dr += 1) {
        for (let dc = -3; dc <= 3; dc += 1) {
          if ((dr === 0 && dc === 0) || seen.has(`${dr},${dc}`)) continue;
          rest.push([dr, dc]);
        }
      }
      rest.sort((a, b) => {
        const ring_a = Math.max(Math.abs(a[0]), Math.abs(a[1]));
        const ring_b = Math.max(Math.abs(b[0]), Math.abs(b[1]));
        if (ring_a !== ring_b) return ring_a - ring_b;
        const walk = Math.abs(a[0]) + Math.abs(a[1]) - (Math.abs(b[0]) + Math.abs(b[1]));
        return walk || a[0] - b[0] || a[1] - b[1];
      });

      const targets = [[row, col]];
      for (const [dr, dc] of ring.concat(rest)) {
        if (targets.length >= count) break;
        const r = row + dr;
        const c = col + dc;
        if (r >= 0 && r < SIZE && c >= 0 && c < SIZE && !this.ai.alreadyShot(r, c)) {
          targets.push([r, c]);
        }
      }
      return targets;
    }

    fusion(row, col) {
      this.checkTarget(row, col);
      const events = [];
      for (const [r, c] of this.fusionTargets(row, col)) {
        events.push(this.shoot("devin", r, c));
        events[events.length - 1].fusion = true;
        if (this.ai.defeated) {
          this.winner = "devin";
          return events;
        }
      }
      this.cursorReply(events);
      return events;
    }

    swe2() {
      if (this.winner) throw new Error("The game is already over.");
      const events = [];
      for (const column of SWE2_COLUMNS) {
        const col = column - 1;
        for (let row = 0; row < SIZE; row += 1) {
          if (this.ai.alreadyShot(row, col)) continue;
          events.push(this.shoot("devin", row, col));
          events[events.length - 1].barrage = true;
          if (this.ai.defeated) {
            this.winner = "devin";
            return events;
          }
        }
      }
      if (!events.length) throw new Error("Columns 1, 4 and 6 are already shelled out.");
      this.cursorReply(events);
      return events;
    }

    outsource() {
      if (this.winner) throw new Error("The game is already over.");
      const afloat = this.ai.ships.filter((ship) => !ship.sunk);
      if (!afloat.length) throw new Error("Cursor has nothing left afloat.");
      const target = afloat.reduce((big, ship) => (ship.size > big.size ? ship : big));
      const reveal = shipState(target, true);
      /* One missile per square of the hull, even though three detonate her and
         squares already hit need no second hole: the extra ones are for show
         and fly first, so the salvo still ends on the shot that sinks her. */
      const needed = Math.min(EXPLOSION_THRESHOLD, target.size) - target.hits.size;
      const live = target.cells
        .filter(([r, c]) => !this.ai.alreadyShot(r, c))
        .slice(0, needed);
      const isLive = new Set(live.map(([r, c]) => key(r, c)));
      const events = [];
      for (const [row, col] of target.cells) {
        if (isLive.has(key(row, col))) continue;
        events.push({
          team: "devin",
          row,
          col,
          coord: coord(row, col),
          result: "hit",
          ship: target.name,
          exploded: false,
          hits: target.hits.size,
          restrike: true,
        });
      }
      for (const [row, col] of live) events.push(this.shoot("devin", row, col));
      events.forEach((event) => {
        event.outsourced = true;
      });
      if (events.length) events[0].reveal = reveal;
      if (this.ai.defeated) {
        this.winner = "devin";
        return events;
      }
      this.cursorReply(events);
      return events;
    }

    boardState(board, reveal) {
      return {
        grid: board.grid.map((row) => row.join("")),
        ships: board.ships.map((ship) => shipState(ship, reveal)).filter(Boolean),
        fleet: board.ships.map((ship) => ({
          name: ship.name,
          size: ship.size,
          hits: ship.hits.size,
          sunk: ship.sunk,
        })),
      };
    }

    swarm() {
      const heat = density(this.ai);
      let best = null;
      for (let r = 0; r < SIZE; r += 1) {
        for (let c = 0; c < SIZE; c += 1) {
          if (heat[r][c] > 0 && (!best || heat[r][c] > best[0])) best = [heat[r][c], r, c];
        }
      }
      return {
        heat,
        probability: heat.map((row) => row.slice()),
        best: best ? coord(best[1], best[2]) : null,
        method: "density",
        ess: 0,
      };
    }

    state() {
      return {
        size: SIZE,
        turn: this.turn,
        winner: this.winner,
        log: this.log,
        stats: {
          ...this.stats,
          devin_alive: FLEET.length - this.stats.cursor_sunk,
          cursor_alive: FLEET.length - this.stats.devin_sunk,
        },
        home: this.boardState(this.player, true),
        away: this.boardState(this.ai, this.winner !== null),
        swarm: this.swarm(),
      };
    }
  }

  function shipState(ship, reveal) {
    if (!reveal && !ship.sunk) return null;
    const [firstRow, firstCol] = ship.cells[0];
    return {
      name: ship.name,
      size: ship.size,
      row: firstRow,
      col: firstCol,
      horizontal: firstRow === ship.cells[ship.cells.length - 1][0],
      sunk: ship.sunk,
      hits: [...ship.hits]
        .map((cell) => [Math.floor(cell / SIZE), cell % SIZE])
        .sort((a, b) => a[0] - b[0] || a[1] - b[1]),
    };
  }

  /* ---------- the shape web.py has ---------- */

  let session = new Session();

  function parseCoord(text) {
    const cleaned = String(text).trim().toUpperCase().replace(/\s+/g, "");
    const match = cleaned.match(/^([A-J])(\d{1,2})$/);
    if (!match) throw new Error("Use a coordinate like B7 (row A-J, column 1-10).");
    const col = Number(match[2]) - 1;
    if (col < 0 || col >= SIZE) throw new Error("Column must be between 1 and 10.");
    return [LETTERS.indexOf(match[1]), col];
  }

  function salvo(events) {
    return { events, state: session.state() };
  }

  window.LocalEngine = {
    handle(path, body) {
      switch (path) {
        case "/api/state":
          return session.state();
        case "/api/new":
          session = new Session();
          return session.state();
        case "/api/reroll":
          session.rerollHomeFleet();
          return session.state();
        case "/api/swe2":
          return salvo(session.swe2());
        case "/api/outsource":
          return salvo(session.outsource());
        case "/api/fire":
        case "/api/fusion": {
          const [row, col] =
            body && body.coord !== undefined
              ? parseCoord(body.coord)
              : [Number(body.row), Number(body.col)];
          return salvo(path === "/api/fire" ? session.fire(row, col) : session.fusion(row, col));
        }
        default:
          throw new Error("no such endpoint");
      }
    },
  };
})();
