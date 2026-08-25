const els = {
  status: document.getElementById("status-line"),
  banner: document.getElementById("banner"),
  mode: document.getElementById("mode-pill"),
  live: document.getElementById("live-pill"),
  kill: document.getElementById("kill-pill"),
  run: document.getElementById("btn-run"),
  killBtn: document.getElementById("btn-kill"),
  equity: document.getElementById("m-equity"),
  equityHint: document.getElementById("m-equity-hint"),
  cash: document.getElementById("m-cash"),
  pnl: document.getElementById("m-pnl"),
  pnlHint: document.getElementById("m-pnl-hint"),
  pos: document.getElementById("m-pos"),
  posHint: document.getElementById("m-pos-hint"),
  quotes: document.getElementById("quotes-body"),
  holdings: document.getElementById("pos-body"),
  audit: document.getElementById("audit-body"),
  detail: document.getElementById("audit-detail"),
  session: document.getElementById("session-kv"),
};

let state = null;
let selectedIndex = -1;
let busy = false;

function money(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(n);
}

function num(value, digits = 2) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function pct(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  const sign = n > 0 ? "+" : "";
  return `${sign}${(n * 100).toFixed(2)}%`;
}

function when(iso) {
  if (!iso) return "never";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    month: "short",
    day: "numeric",
  });
}

function clock(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleTimeString(undefined, { hour12: false });
}

function showBanner(text) {
  if (!text) {
    els.banner.classList.add("hidden");
    els.banner.textContent = "";
    return;
  }
  els.banner.classList.remove("hidden");
  els.banner.textContent = text;
}

function emptyRow(cols, text) {
  return `<tr><td colspan="${cols}" class="empty">${text}</td></tr>`;
}

function renderQuotes(quotes) {
  if (!quotes || quotes.length === 0) {
    els.quotes.innerHTML = emptyRow(4, "No quotes yet. Run an iteration.");
    return;
  }
  els.quotes.innerHTML = quotes
    .map(
      (q) => `<tr>
        <td>${q.symbol}</td>
        <td class="num">${money(q.bid)}</td>
        <td class="num">${money(q.last)}</td>
        <td class="num">${money(q.ask)}</td>
      </tr>`
    )
    .join("");
}

function renderHoldings(positions) {
  if (!positions || positions.length === 0) {
    els.holdings.innerHTML = emptyRow(4, "No positions.");
    return;
  }
  els.holdings.innerHTML = positions
    .map(
      (p) => `<tr>
        <td>${p.symbol}</td>
        <td class="num">${num(p.qty, 4)}</td>
        <td class="num">${money(p.avg_price)}</td>
        <td class="num">${money(p.market_value)}</td>
      </tr>`
    )
    .join("");
}

function badgeClass(decision) {
  return decision === "BUY" || decision === "SELL" ? "badge hot" : "badge";
}

function riskLabel(row) {
  const gate = row.risk_gate || {};
  if (gate.status) return gate.status;
  if (gate.reason) return gate.reason;
  if (gate.reconcile_mismatch) return "MISMATCH";
  return "—";
}

function brokerLabel(row) {
  const exec = row.execution || {};
  return exec.status || "—";
}

function strategyLabel(row) {
  const sig = row.strategy_signal || {};
  return sig.strategy_id || "—";
}

function renderAudit(rows) {
  if (!rows || rows.length === 0) {
    els.audit.innerHTML = emptyRow(6, "No decisions yet.");
    els.detail.classList.add("hidden");
    els.detail.hidden = true;
    return;
  }
  els.audit.innerHTML = rows
    .map((row, i) => {
      const open = i === selectedIndex ? " is-open" : "";
      return `<tr class="clickable${open}" data-index="${i}">
        <td class="num">${clock(row.timestamp)}</td>
        <td>${row.symbol}</td>
        <td><span class="${badgeClass(row.decision)}">${row.decision}</span></td>
        <td>${strategyLabel(row)}</td>
        <td>${riskLabel(row)}</td>
        <td>${brokerLabel(row)}</td>
      </tr>`;
    })
    .join("");
}

function pretty(obj) {
  if (!obj) return "—";
  return JSON.stringify(obj, null, 2);
}

function renderDetail() {
  if (!state || selectedIndex < 0 || !state.audit[selectedIndex]) {
    els.detail.classList.add("hidden");
    els.detail.hidden = true;
    return;
  }
  const row = state.audit[selectedIndex];
  els.detail.hidden = false;
  els.detail.classList.remove("hidden");
  els.detail.innerHTML = `
    <h3>${row.symbol} · ${row.decision} · ${when(row.timestamp)}</h3>
    <h3>Strategy</h3>
    <pre>${pretty(row.strategy_signal)}</pre>
    <h3>Risk</h3>
    <pre>${pretty(row.risk_gate)}</pre>
    <h3>Action</h3>
    <pre>${pretty(row.action)}</pre>
    <h3>Execution</h3>
    <pre>${pretty(row.execution)}</pre>
  `;
}

function renderSession(snapshot) {
  const s = snapshot.status;
  const r = snapshot.risk;
  const rows = [
    ["Broker", s.broker],
    ["Symbols", (s.symbols || []).join(", ")],
    ["Loop strategy", (s.strategies || []).join(", ")],
    ["Configured strategies", (s.configured_strategies || []).join(", ")],
    ["LLM", s.llm_enabled ? s.llm_model : "off"],
    ["Market data", s.market_data],
    ["Iterations", String(s.runs)],
    ["Last run", when(s.last_run_at)],
    ["Max position", `${(Number(r.max_position_pct) * 100).toFixed(0)}%`],
    ["Portfolio heat", `${(Number(r.max_portfolio_heat_pct) * 100).toFixed(0)}%`],
    ["Max daily loss", `${(Number(r.max_daily_loss_pct) * 100).toFixed(0)}%`],
    ["Max orders / day", String(r.max_orders_per_day)],
    ["PDT guard", r.pdt_guard_enabled ? "on" : "off"],
  ];
  els.session.innerHTML = rows
    .map(([k, v]) => `<dt>${k}</dt><dd>${v || "—"}</dd>`)
    .join("");
}

function render(snapshot) {
  state = snapshot;
  const s = snapshot.status;
  const p = snapshot.portfolio;
  const nPos = (p.positions || []).length;

  els.mode.textContent = s.broker;
  els.live.textContent = s.live_trading_enabled ? "live on" : "live off";
  els.live.classList.toggle("muted", !s.live_trading_enabled);

  els.kill.textContent = s.kill_switch ? "disarmed" : "armed";
  els.kill.classList.toggle("warn", s.kill_switch);
  els.kill.classList.toggle("muted", !s.kill_switch);
  els.killBtn.textContent = s.kill_switch ? "Re-arm" : "Disarm";
  els.run.disabled = Boolean(s.kill_switch);

  els.equity.textContent = money(p.equity);
  els.equityHint.textContent = `start ${money(p.session_start_equity)}`;
  els.cash.textContent = money(p.cash);
  els.pnl.textContent = money(p.day_pnl);
  els.pnlHint.textContent = pct(p.day_pnl_pct);
  els.pos.textContent = String(nPos);
  els.posHint.textContent = nPos === 1 ? "open symbol" : "open symbols";

  const last = s.last_run_at ? when(s.last_run_at) : "not yet";
  els.status.textContent = `${s.runs} iteration${s.runs === 1 ? "" : "s"} · last ${last} · ${
    snapshot.audit.length
  } decisions`;

  if (s.last_error) showBanner(s.last_error);
  else if (s.kill_switch) showBanner("Kill switch on. New iterations are blocked.");
  else showBanner("");

  renderQuotes(snapshot.quotes);
  renderHoldings(p.positions);
  renderAudit(snapshot.audit);
  renderDetail();
  renderSession(snapshot);
}

async function fetchState() {
  const res = await fetch("/api/state");
  if (!res.ok) throw new Error(`state ${res.status}`);
  return res.json();
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : "{}",
  });
  if (!res.ok) throw new Error(`${url} ${res.status}`);
  return res.json();
}

async function refresh() {
  try {
    render(await fetchState());
  } catch (err) {
    showBanner(`Could not load state: ${err.message}`);
  }
}

async function withBusy(fn) {
  if (busy) return;
  busy = true;
  els.run.disabled = true;
  try {
    await fn();
  } catch (err) {
    showBanner(err.message);
  } finally {
    busy = false;
    if (state && !state.status.kill_switch) els.run.disabled = false;
  }
}

els.run.addEventListener("click", () =>
  withBusy(async () => {
    const result = await postJson("/api/run");
    if (result.state) render(result.state);
    if (result.blocked) showBanner("Kill switch on. New iterations are blocked.");
  })
);

els.killBtn.addEventListener("click", () =>
  withBusy(async () => {
    const enabled = !(state && state.status.kill_switch);
    const result = await postJson("/api/kill-switch", { enabled });
    if (result.state) render(result.state);
  })
);

els.audit.addEventListener("click", (event) => {
  const row = event.target.closest("tr[data-index]");
  if (!row) return;
  const index = Number(row.dataset.index);
  selectedIndex = selectedIndex === index ? -1 : index;
  if (state) {
    renderAudit(state.audit);
    renderDetail();
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "r" && !event.metaKey && !event.ctrlKey && event.target === document.body) {
    els.run.click();
  }
});

refresh();
setInterval(refresh, 8000);
