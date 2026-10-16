import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowRight,
  Boxes,
  Check,
  ChevronRight,
  Clock3,
  Database,
  Flag,
  FlaskConical,
  GitBranch,
  History,
  Layers3,
  LoaderCircle,
  Map,
  Pause,
  Play,
  Radio,
  RefreshCw,
  Route as RouteIcon,
  ShieldCheck,
  StepForward,
  Truck,
  Waves,
  X,
  Zap,
} from "lucide-react";
import type { World, Road, Plan, Ranking, Snapshot } from "./types";

async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(
    "/api" + path,
    body === undefined
      ? undefined
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  const result = await response.json();
  if (!response.ok)
    throw new Error(
      result.error || JSON.stringify(result.detail) || "Request failed",
    );
  return result;
}
const key = () => crypto.randomUUID();
const pretty = (s: string) => s.replaceAll("_", " ").toLowerCase();
const clock = (n: number) =>
  `${String(8 + Math.floor(n / 60)).padStart(2, "0")}:${String(n % 60).padStart(2, "0")}`;

function TownMap({
  w,
  selected,
  select,
  plan,
}: {
  w: World;
  selected: string;
  select: (id: string) => void;
  plan: Plan | null;
}) {
  const loc = Object.fromEntries(w.locations.map((l) => [l.id, l]));
  const activeRoads = new Set(
    w.assignments
      .filter((a) => ["reserved", "in_transit"].includes(a.state))
      .flatMap((a) => a.route.legs.map((l) => l.road)),
  );
  const proposed = new Set(
    plan?.routes.flatMap((r) => r.legs.map((l) => l.road)) || [],
  );
  const activate = (event: React.KeyboardEvent, id: string) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      select(id);
    }
  };
  return (
    <svg
      className="town-map"
      viewBox="0 0 860 650"
      role="img"
      aria-label="Fictional Alder Reach road and delivery map"
    >
      <defs>
        <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
          <path
            d="M 30 0 L 0 0 0 30"
            fill="none"
            stroke="#dfe6dd"
            strokeWidth=".5"
          />
        </pattern>
        <pattern
          id="water"
          width="22"
          height="18"
          patternUnits="userSpaceOnUse"
        >
          <path
            d="M2 9q5-4 10 0t10 0"
            fill="none"
            stroke="#aed0d4"
            strokeWidth="1"
          />
        </pattern>
      </defs>
      <rect width="860" height="650" fill="#f1f3eb" />
      <rect width="860" height="650" fill="url(#grid)" />
      <path
        d="M0 20 Q150 50 205 0 M0 600Q90 515 70 650 M800 0Q780 60 860 80 M860 560Q820 565 780 650"
        fill="none"
        stroke="#e3e9d8"
        strokeWidth="110"
      />
      <path
        d="M450 -30 C355 90 510 150 470 260 S390 430 500 680"
        fill="none"
        stroke="#c3dde0"
        strokeWidth="66"
      />
      <path
        d="M450 -30 C355 90 510 150 470 260 S390 430 500 680"
        fill="none"
        stroke="url(#water)"
        strokeWidth="58"
      />
      <text
        x="466"
        y="360"
        transform="rotate(-74 466 360)"
        className="river-label"
      >
        ALDER RIVER
      </text>
      <text x="62" y="55" className="district-label">
        WEST ALDER
      </text>
      <text x="630" y="55" className="district-label">
        EAST REACH
      </text>
      {w.roads.map((r) => {
        const a = loc[r.a],
          b = loc[r.b];
        const uncertain = ["UNKNOWN", "CONFLICTING", "STALE"].includes(
          r.status,
        );
        const active = activeRoads.has(r.id) || proposed.has(r.id);
        return (
          <g
            key={r.id}
            role="button"
            tabIndex={0}
            aria-label={`Select ${r.name}`}
            onKeyDown={(e) => activate(e, r.id)}
            onClick={() => select(r.id)}
            className="map-select"
          >
            <line
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke="transparent"
              strokeWidth="20"
            />
            {selected === r.id && (
              <line
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke="#eccb7c"
                strokeWidth="13"
                opacity=".65"
              />
            )}
            <line
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke={
                r.status === "VERIFIED_CLOSED"
                  ? "#ba675b"
                  : uncertain
                    ? "#bc8d3e"
                    : active
                      ? "#197d65"
                      : "#acb9ab"
              }
              strokeWidth={active ? 5 : r.id === "r08" ? 5 : 3}
              strokeDasharray={
                uncertain
                  ? "7 5"
                  : r.status === "VERIFIED_CLOSED"
                    ? "2 5"
                    : undefined
              }
            />
            {r.id === "r08" && (
              <>
                <rect
                  x="409"
                  y="214"
                  width="113"
                  height="24"
                  rx="6"
                  fill="#fff9e9"
                  stroke="#cfad60"
                />
                <text
                  x="465"
                  y="230"
                  textAnchor="middle"
                  className="bridge-label"
                >
                  {uncertain
                    ? "? "
                    : r.status === "VERIFIED_OPEN"
                      ? "✓ "
                      : "× "}
                  ALDER BRIDGE
                </text>
              </>
            )}
          </g>
        );
      })}
      {w.locations.map((l) => (
        <g
          key={l.id}
          className="map-select"
          role="button"
          tabIndex={0}
          aria-label={`Select ${l.name}`}
          onKeyDown={(e) =>
            activate(
              e,
              l.kind === "shelter"
                ? w.requests.find((q) => q.destination === l.id)!.id
                : l.id,
            )
          }
          onClick={() =>
            select(
              l.kind === "shelter"
                ? w.requests.find((q) => q.destination === l.id)!.id
                : l.id,
            )
          }
        >
          {l.kind === "depot" ? (
            <>
              <rect
                x={l.x - 13}
                y={l.y - 13}
                width="26"
                height="26"
                rx="6"
                fill="#173f35"
                stroke="white"
                strokeWidth="3"
              />
              <path
                d={`M${l.x - 6} ${l.y + 5}v-10h12v10m-6-10v10`}
                stroke="#e5f2da"
                fill="none"
                strokeWidth="1.5"
              />
            </>
          ) : l.kind === "shelter" ? (
            <>
              <circle
                cx={l.x}
                cy={l.y}
                r="13"
                fill={
                  w.requests
                    .filter((q) => q.destination === l.id)
                    .every((q) => q.status === "delivered")
                    ? "#23795f"
                    : "#fff"
                }
                stroke="#4a7260"
                strokeWidth="2"
              />
              <path
                d={`M${l.x - 7} ${l.y}l7-6 7 6m-12-1v7h10v-7`}
                stroke="#4a7260"
                fill="none"
                strokeWidth="1.5"
              />
            </>
          ) : (
            <circle
              cx={l.x}
              cy={l.y}
              r="4"
              fill="#f4f5ee"
              stroke="#8fa38d"
              strokeWidth="2"
            />
          )}
          <text
            x={l.x}
            y={l.y + (l.kind === "junction" ? -12 : 29)}
            textAnchor="middle"
            className={
              l.kind === "junction" ? "junction-label" : "location-label"
            }
          >
            {l.name}
          </text>
          {l.kind === "shelter" && (
            <text
              x={l.x}
              y={l.y + 44}
              textAnchor="middle"
              className="map-detail"
            >
              {w.requests
                .filter(
                  (q) => q.destination === l.id && q.status !== "delivered",
                )
                .reduce((s, q) => s + q.quantity, 0)}{" "}
              kits pending
            </text>
          )}
        </g>
      ))}
      {w.vehicles.map((v, i) => {
        const a = w.assignments.find((a) => a.id === v.assignment);
        let p = loc[v.location];
        let x = p.x,
          y = p.y;
        if (a && a.entered_at !== null && a.exits_at !== null) {
          const leg = a.route.legs[a.index];
          const from = loc[leg.start],
            to = loc[leg.end];
          const f = Math.min(
            1,
            (w.time - a.entered_at) / (a.exits_at - a.entered_at),
          );
          x = from.x + (to.x - from.x) * f;
          y = from.y + (to.y - from.y) * f;
        }
        return (
          <g
            key={v.id}
            role="button"
            tabIndex={0}
            aria-label={`Select ${v.name}`}
            onKeyDown={(e) => activate(e, v.id)}
            onClick={() => select(v.id)}
            className="map-select"
            transform={`translate(${x + 18 + (i === 2 ? 24 : 0)} ${y - 20})`}
          >
            <rect
              x="-10"
              y="-9"
              width="20"
              height="18"
              rx="5"
              fill={v.available ? "#f9f6e9" : "#e6d9d2"}
              stroke="#526e56"
            />
            <text textAnchor="middle" y="4" fontSize="10" fill="#254437">
              {v.id.toUpperCase()}
            </text>
          </g>
        );
      })}
      <g transform="translate(800 530)">
        <path d="M0 0l-6 18 6-4 6 4Z" fill="#496655" />
        <text x="0" y="-8" textAnchor="middle" className="junction-label">
          N
        </text>
      </g>
      <g transform="translate(50 610)">
        <path d="M0-5v5h80v-5M40 0v-5" fill="none" stroke="#73816e" />
        <text y="16" className="map-detail">
          Fictional schematic · not to scale
        </text>
      </g>
    </svg>
  );
}

export default function App() {
  const [world, setWorld] = useState<World | null>(null),
    [selected, setSelected] = useState("r08");
  const [scenarios, setScenarios] = useState<
      { id: string; name: string; description: string }[]
    >([]),
    [scenario, setScenario] = useState("critical_crossing");
  const [runs, setRuns] = useState<
      { id: string; scenario: string; time: number }[]
    >([]),
    [seed, setSeed] = useState(1);
  const [tab, setTab] = useState("operations"),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [healthy, setHealthy] = useState(false),
    [llm, setLlm] = useState(false),
    [mode, setMode] = useState("deterministic");
  const [ranking, setRanking] = useState<Ranking | null>(null),
    [plan, setPlan] = useState<Plan | null>(null),
    [detail, setDetail] = useState<unknown>(null),
    [queries, setQueries] = useState<unknown[]>([]);
  const [auto, setAuto] = useState(false),
    [replay, setReplay] = useState(false),
    [snapshots, setSnapshots] = useState<Snapshot[]>([]),
    [frame, setFrame] = useState(0);
  const [bench, setBench] = useState<any>(null),
    [benchJob, setBenchJob] = useState("idle");
  const busyRef = useRef(false);
  const refresh = useCallback(async (id: string) => {
    const [w, h] = await Promise.all([
      api<World>("/runs/" + id),
      api<any>("/health"),
    ]);
    setWorld(w);
    setHealthy(true);
    setLlm(h.llm_configured);
    localStorage.setItem("lastmile-run", id);
    return w;
  }, []);
  useEffect(() => {
    Promise.all([
      api<any[]>("/scenarios"),
      api<any>("/health"),
      api<any[]>("/runs"),
    ])
      .then(async ([s, h, r]) => {
        setScenarios(s);
        setHealthy(true);
        setLlm(h.llm_configured);
        setRuns(r);
        const id = localStorage.getItem("lastmile-run");
        if (id && r.some((x) => x.id === id)) await refresh(id);
      })
      .catch((e) => {
        setHealthy(false);
        setError(e.message);
      });
  }, [refresh]);
  async function act(fn: () => Promise<unknown>, refreshAfter = true) {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setError("");
    try {
      await fn();
      if (refreshAfter && world) await refresh(world.id);
    } catch (e) {
      setError((e as Error).message);
      setAuto(false);
      try {
        await api("/health");
      } catch {
        setHealthy(false);
      }
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  }
  async function newRun(reset = false) {
    await act(async () => {
      const w = await api<World>(reset ? `/runs/${world!.id}/reset` : "/runs", {
        scenario,
        seed,
      });
      setWorld(w);
      setPlan(null);
      setRanking(null);
      setDetail(null);
      setReplay(false);
      setAuto(false);
      localStorage.setItem("lastmile-run", w.id);
      setRuns(await api("/runs"));
    }, false);
  }
  async function cycle() {
    await act(async () => {
      const r = await api<any>(`/runs/${world!.id}/cycle`, { mode });
      if (r.stopped) setAuto(false);
      setPlan(null);
      setRanking(null);
    });
  }
  useEffect(() => {
    if (!auto || !world || replay) return;
    const timer = setTimeout(() => {
      if (world.status !== "active" || world.cycles >= 30) setAuto(false);
      else void cycle();
    }, 1200);
    return () => clearTimeout(timer);
  }, [auto, world, busy, replay]);
  useEffect(() => {
    if (!world || auto || replay) return;
    const timer = setInterval(() => {
      if (!busyRef.current)
        refresh(world.id).catch((e) => {
          setHealthy(false);
          setError(e.message);
        });
    }, 7000);
    return () => clearInterval(timer);
  }, [world?.id, auto, replay, refresh]);
  async function loadBench() {
    const r = await api<any>("/benchmarks");
    setBench(r.results);
    setBenchJob(r.job.status);
  }
  useEffect(() => {
    if (tab === "benchmarks") loadBench().catch((e) => setError(e.message));
    if (tab === "evidence" && world)
      api<unknown[]>(`/runs/${world.id}/queries`)
        .then(setQueries)
        .catch((e) => setError(e.message));
  }, [tab, world?.revision]);
  useEffect(() => {
    if (benchJob !== "running") return;
    const id = setInterval(
      () => loadBench().catch((e) => setError(e.message)),
      3000,
    );
    return () => clearInterval(id);
  }, [benchJob]);
  const shown = replay ? snapshots[frame]?.state || world : world;
  const disabled =
    busy || !healthy || replay || !world || world.status !== "active";
  const road = shown?.roads.find((r) => r.id === selected),
    request = shown?.requests.find((q) => q.id === selected),
    vehicle = shown?.vehicles.find((v) => v.id === selected),
    location = shown?.locations.find((l) => l.id === selected);
  const title =
    scenarios.find((s) => s.id === shown?.scenario)?.name ||
    "Critical crossing";
  const path = world ? "/runs/" + world.id : "";
  const displayPlan =
    plan?.revision === world?.revision && !replay ? plan : null;
  async function inspect(r: Road) {
    await act(async () => {
      await api(path + "/inspect", { road: r.id, key: key() });
      setRanking(null);
      setPlan(null);
    });
  }
  async function openReplay() {
    setAuto(false);
    await act(async () => {
      const s = await api<Snapshot[]>(path + "/replay");
      setSnapshots(s);
      setFrame(s.length - 1);
      setReplay(true);
      setPlan(null);
    }, false);
  }
  return (
    <div className="app-shell">
      <aside className="rail">
        <a className="brand-mark" href="#" aria-label="LastMile home">
          <RouteIcon size={24} />
        </a>
        <div className="rail-line" />
        {[
          { id: "operations", icon: Map, label: "Operations" },
          { id: "evidence", icon: GitBranch, label: "Graph evidence" },
          { id: "benchmarks", icon: FlaskConical, label: "Benchmarks" },
        ].map((item) => (
          <button
            key={item.id}
            title={item.label}
            aria-label={item.label}
            className={tab === item.id ? "rail-button active" : "rail-button"}
            onClick={() => setTab(item.id)}
          >
            <item.icon size={21} />
          </button>
        ))}
        <span className="rail-bottom">
          <Waves size={23} />
        </span>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="wordmark">
            LastMile<span>RELIEF COORDINATION</span>
          </div>
          <div className="topbar-right">
            <span className="synthetic">
              <span />
              FICTIONAL SCENARIO
            </span>
            <span className="avatar">LM</span>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">OPERATIONS / ALDER REACH</div>
              <h1>
                {tab === "operations"
                  ? "Every delivery starts with better evidence."
                  : tab === "evidence"
                    ? "Follow the evidence."
                    : "Measure the decisions."}
              </h1>
              <p>
                {tab === "operations"
                  ? "Verify the uncertainty. Deliver what matters."
                  : tab === "evidence"
                    ? "Actual FalkorDB queries, dependencies and recorded tool outcomes."
                    : "Reproducible comparisons across identical synthetic worlds."}
              </p>
            </div>
            <div className={"health " + (!healthy ? "degraded" : "")}>
              <span />
              {healthy ? "FalkorDB connected" : "Connection unavailable"}
              <small>
                Frontend ready ·{" "}
                {healthy ? "API healthy" : "state may be stale"}
              </small>
            </div>
          </div>
          {error && (
            <div className="error" role="alert">
              <Radio size={18} />
              <span>
                {error}
                {!healthy &&
                  " · Cached state is stale. Mutations are disabled."}
              </span>
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          <section className="controlbar">
            <div className="scenario-control">
              <span className="tiny-label">SCENARIO</span>
              <select
                aria-label="Scenario"
                value={scenario}
                disabled={busy || replay}
                onChange={(e) => setScenario(e.target.value)}
              >
                {scenarios.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
              <label className="seed-label">
                World{" "}
                <input
                  aria-label="World seed"
                  type="number"
                  min="0"
                  max="1000000"
                  value={seed}
                  disabled={busy || replay}
                  onChange={(e) => setSeed(Number(e.target.value))}
                />
              </label>
              <button
                disabled={busy || replay || !healthy}
                onClick={() => newRun()}
              >
                New run
              </button>
            </div>
            <div className="controller-control">
              <select
                aria-label="Controller mode"
                value={mode}
                disabled={busy || replay || auto}
                onChange={(e) => setMode(e.target.value)}
              >
                <option value="deterministic">Deterministic demo</option>
                <option value="llm" disabled={!llm}>
                  LLM agent{!llm ? " · configure key" : ""}
                </option>
              </select>
              <button
                className="button-primary"
                disabled={disabled || auto}
                onClick={cycle}
              >
                {busy ? (
                  <LoaderCircle size={15} className="spin" />
                ) : (
                  <Zap size={15} />
                )}{" "}
                One decision
              </button>
              <button
                className="button-icon"
                aria-label={auto ? "Pause simulation" : "Start simulation"}
                disabled={disabled && !auto}
                onClick={() => setAuto(!auto)}
              >
                {auto ? <Pause size={17} /> : <Play size={17} />}
              </button>
              <button
                className="button-icon"
                title="Advance 10 minutes"
                aria-label="Advance 10 minutes"
                disabled={disabled || auto}
                onClick={() =>
                  act(async () => {
                    await api(path + "/advance", { minutes: 10, key: key() });
                    setPlan(null);
                    setRanking(null);
                  })
                }
              >
                <StepForward size={18} />
              </button>
            </div>
          </section>
          {!shown ? (
            <section className="welcome">
              <div className="welcome-icon">
                <Map size={40} />
              </div>
              <h2>Your coordination workspace is ready.</h2>
              <p>
                Create a run to investigate reports, compare inspections and
                deliver relief kits in fictional Alder Reach.
              </p>
              <button
                className="button-primary"
                disabled={busy || !healthy}
                onClick={() => newRun()}
              >
                <Play size={16} /> Create first run
              </button>
              {runs.length > 0 && (
                <select
                  aria-label="Resume run"
                  defaultValue=""
                  onChange={(e) => act(() => refresh(e.target.value), false)}
                >
                  <option value="" disabled>
                    Resume an existing run
                  </option>
                  {runs.map((r) => (
                    <option key={r.id} value={r.id}>
                      {pretty(r.scenario)} · minute {r.time} ·{" "}
                      {r.id.slice(0, 6)}
                    </option>
                  ))}
                </select>
              )}
            </section>
          ) : (
            <>
              <section className="metric-grid">
                {[
                  {
                    icon: Boxes,
                    label: "KITS DELIVERED",
                    value: shown.metrics.delivered_kits,
                    sub: `${shown.metrics.on_time_kits} units on time`,
                  },
                  {
                    icon: Flag,
                    label: "DELIVERIES ON TIME",
                    value: shown.metrics.on_time_requests,
                    sub: `${shown.requests.length} total requests`,
                  },
                  {
                    icon: ShieldCheck,
                    label: "INSPECTION BUDGET",
                    value: shown.budget,
                    sub: `${shown.metrics.inspections} checks used`,
                  },
                  {
                    icon: Clock3,
                    label: replay ? "HISTORICAL TIME" : "SIMULATION TIME",
                    value: clock(shown.time),
                    sub: `${shown.time} / ${shown.horizon} minutes · ${shown.status}`,
                  },
                ].map((m) => (
                  <article className="metric" key={m.label}>
                    <div>
                      <span className="tiny-label">{m.label}</span>
                      <strong>{m.value}</strong>
                      <small>{m.sub}</small>
                    </div>
                    <m.icon size={21} />
                  </article>
                ))}
              </section>
              {replay && (
                <div className="replaybar">
                  <History size={19} />
                  <strong>Read-only replay</strong>
                  <span>
                    Historical {clock(shown.time)} · revision {shown.revision}
                  </span>
                  <input
                    aria-label="Replay revision"
                    type="range"
                    min="0"
                    max={snapshots.length - 1}
                    value={frame}
                    onChange={(e) => setFrame(Number(e.target.value))}
                  />
                  <button onClick={() => setReplay(false)}>
                    Return to live
                  </button>
                </div>
              )}
              {tab === "operations" && (
                <>
                  <div className="operations-grid">
                    <section className="panel map-panel">
                      <div className="panel-heading">
                        <div>
                          <span className="live-dot" />
                          <h2>Alder Reach</h2>
                          <span className="subtle">{title}</span>
                        </div>
                        <span className="map-badge">SCHEMATIC MAP</span>
                      </div>
                      <div
                        className="map-viewport"
                        tabIndex={0}
                        aria-label="Town map, scroll horizontally on small screens"
                      >
                        <TownMap
                          w={shown}
                          selected={selected}
                          select={setSelected}
                          plan={displayPlan}
                        />
                      </div>
                      <div className="map-legend">
                        <span>
                          <i className="legend-line verified" />
                          Verified open
                        </span>
                        <span>
                          <i className="legend-line uncertain" />
                          Uncertain / stale
                        </span>
                        <span>
                          <i className="legend-line closed" />
                          Closed
                        </span>
                        <span>
                          <i className="legend-line active-route" />
                          Delivery route
                        </span>
                        <span className="map-revision">
                          rev {shown.revision}
                        </span>
                      </div>
                    </section>
                    <aside className="panel evidence-panel">
                      <div className="panel-heading">
                        <div>
                          <Radio size={17} />
                          <h2>Field intelligence</h2>
                        </div>
                        <span className="count-badge">
                          {selected.toUpperCase()}
                        </span>
                      </div>
                      <div className="selection-content">
                        {road ? (
                          <>
                            <span className="eyebrow">ROAD SEGMENT</span>
                            <h3>{road.name}</h3>
                            <span
                              className={"status-pill " + pretty(road.status)}
                            >
                              {road.status === "VERIFIED_OPEN" ? (
                                <ShieldCheck size={12} />
                              ) : (
                                <Radio size={12} />
                              )}{" "}
                              {pretty(road.status)}
                            </span>
                            <div className="road-facts">
                              <span>
                                Travel time<strong>{road.minutes} min</strong>
                              </span>
                              <span>
                                Verification
                                <strong>
                                  {road.valid_until > shown.time
                                    ? `until ${clock(road.valid_until)}`
                                    : "Required"}
                                </strong>
                              </span>
                            </div>
                            <div className="section-label">
                              SOURCE REPORTS{" "}
                              <span>
                                {
                                  shown.reports.filter(
                                    (r) => r.road === road.id,
                                  ).length
                                }
                              </span>
                            </div>
                            <div className="reports">
                              {shown.reports
                                .filter((r) => r.road === road.id)
                                .map((r) => (
                                  <article className="report" key={r.id}>
                                    <div>
                                      <strong>{r.source}</strong>
                                      <span
                                        className={
                                          r.claim === "OPEN"
                                            ? "claim-open"
                                            : "claim-closed"
                                        }
                                      >
                                        {r.claim}
                                      </span>
                                    </div>
                                    <p>{r.text}</p>
                                    <small>
                                      Observed T{r.observed_at} · received T
                                      {r.received_at}
                                      <br />
                                      {r.authority} · {r.id}
                                    </small>
                                  </article>
                                ))}
                              {!shown.reports.some(
                                (r) => r.road === road.id,
                              ) && (
                                <p className="muted">
                                  Stable scenario verification covers the
                                  horizon.
                                </p>
                              )}
                            </div>
                            <button
                              className="full"
                              disabled={busy || !healthy || replay}
                              onClick={() =>
                                act(
                                  async () =>
                                    setDetail(
                                      await api(path + "/impact/" + road.id),
                                    ),
                                  false,
                                )
                              }
                            >
                              <GitBranch size={15} /> Trace delivery impact{" "}
                              <ArrowRight size={14} />
                            </button>
                            <button
                              className="button-primary full"
                              disabled={
                                disabled ||
                                !["CONFLICTING", "UNKNOWN", "STALE"].includes(
                                  road.status,
                                ) ||
                                shown.budget < 1
                              }
                              onClick={() => inspect(road)}
                            >
                              <ShieldCheck size={15} />
                              Inspect road · {road.inspection_minutes} min
                            </button>
                            <p className="footnote">
                              Inspection uses one check. The fleet keeps moving
                              while evidence is gathered.
                            </p>
                          </>
                        ) : request ? (
                          <>
                            <span className="eyebrow">
                              DELIVERY REQUEST {request.id.toUpperCase()}
                            </span>
                            <h3>
                              {
                                shown.locations.find(
                                  (l) => l.id === request.destination,
                                )?.name
                              }
                            </h3>
                            <span className="status-pill">
                              {pretty(request.status)}
                            </span>
                            <div className="road-facts">
                              <span>
                                Relief kits
                                <strong>{request.quantity} units</strong>
                              </span>
                              <span>
                                Deadline
                                <strong>{clock(request.deadline)}</strong>
                              </span>
                              <span>
                                Priority weight<strong>{request.weight}</strong>
                              </span>
                              <span>
                                Delivered
                                <strong>
                                  {request.delivered_at === null
                                    ? "Pending"
                                    : clock(request.delivered_at)}
                                </strong>
                              </span>
                            </div>
                            <p className="muted">
                              Indivisible request. The planner maximises on-time
                              priority × kit units.
                            </p>
                          </>
                        ) : vehicle ? (
                          <>
                            <span className="eyebrow">
                              VEHICLE {vehicle.id.toUpperCase()}
                            </span>
                            <h3>{vehicle.name}</h3>
                            <span className="status-pill">
                              {vehicle.available
                                ? "Available for work"
                                : "Withdrawn"}
                            </span>
                            <div className="road-facts">
                              <span>
                                Capacity<strong>{vehicle.capacity} kits</strong>
                              </span>
                              <span>
                                On board<strong>{vehicle.loaded} kits</strong>
                              </span>
                              <span>
                                Current location
                                <strong>
                                  {vehicle.location.toUpperCase()}
                                </strong>
                              </span>
                              <span>
                                Assignment
                                <strong>
                                  {vehicle.assignment ? "Committed" : "None"}
                                </strong>
                              </span>
                            </div>
                            <p className="muted">
                              Reservations and loaded stock persist across
                              refreshes and replanning.
                            </p>
                          </>
                        ) : (
                          <>
                            <span className="eyebrow">
                              {location?.kind || "LOCATION"}
                            </span>
                            <h3>{location?.name}</h3>
                            {location?.kind === "depot" && (
                              <p className="stock-number">
                                {shown.stock_available[location.id]}{" "}
                                <small>kits available</small>
                              </p>
                            )}
                          </>
                        )}
                      </div>
                    </aside>
                  </div>
                  <div className="lower-grid">
                    <section className="panel inspection-panel">
                      <div className="panel-heading">
                        <div>
                          <Layers3 size={17} />
                          <h2>What is worth verifying?</h2>
                        </div>
                        <button
                          disabled={disabled || auto}
                          onClick={() =>
                            act(
                              async () => setRanking(await api(path + "/rank")),
                              false,
                            )
                          }
                        >
                          {ranking?.revision === world?.revision
                            ? "Recalculate"
                            : "Compare inspections"}
                          <ChevronRight size={14} />
                        </button>
                      </div>
                      {ranking?.revision === shown.revision && !replay ? (
                        <>
                          <div className="ranking-note">
                            <span>
                              Base utility{" "}
                              <strong>{ranking.base_utility}</strong>
                            </span>
                            <span>{ranking.recommendation}</span>
                          </div>
                          <div className="table-scroll">
                            <table>
                              <thead>
                                <tr>
                                  <th>Road</th>
                                  <th>Open / closed</th>
                                  <th>Cost</th>
                                  <th>Est. gain</th>
                                </tr>
                              </thead>
                              <tbody>
                                {ranking.candidates.map((c) => (
                                  <tr
                                    key={c.road}
                                    onClick={() => setSelected(c.road)}
                                  >
                                    <td>
                                      <strong>{c.name}</strong>
                                      <small>
                                        Open prior {Math.round(c.prior * 100)}%
                                        · synthetic
                                      </small>
                                    </td>
                                    <td>
                                      {c.open_utility} / {c.closed_utility}
                                    </td>
                                    <td>{c.minutes} min</td>
                                    <td>
                                      <span
                                        className={
                                          c.gain > 0
                                            ? "gain-positive"
                                            : "gain-negative"
                                        }
                                      >
                                        {c.gain > 0 ? "+" : ""}
                                        {c.gain}
                                      </span>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                          <p className="footnote panel-footnote">
                            Expected utility after check − base utility. An
                            estimate under this bounded model, with a synthetic
                            prior.
                          </p>
                        </>
                      ) : (
                        <div className="empty-inline">
                          <Layers3 size={28} />
                          <div>
                            <strong>
                              Spend checks where they can change the plan.
                            </strong>
                            <p>
                              Compare the open and closed branches, including
                              inspection delay and delivery deadlines.
                            </p>
                          </div>
                        </div>
                      )}
                    </section>
                    <section className="panel plan-panel">
                      <div className="panel-heading">
                        <div>
                          <RouteIcon size={17} />
                          <h2>Delivery plan</h2>
                        </div>
                        <button
                          disabled={disabled || auto}
                          onClick={() =>
                            act(
                              async () => setPlan(await api(path + "/plan")),
                              false,
                            )
                          }
                        >
                          Preview plan
                          <ChevronRight size={14} />
                        </button>
                      </div>
                      {displayPlan ? (
                        <div className="plan-preview">
                          <div className="plan-utility">
                            <strong>{displayPlan.utility}</strong>
                            <span>
                              predicted total utility
                              <small>
                                {displayPlan.status} within candidate model ·{" "}
                                {displayPlan.solver_seconds}s
                              </small>
                            </span>
                          </div>
                          {displayPlan.routes.map((r) => (
                            <div className="plan-route" key={r.vehicle}>
                              <Truck size={15} />
                              <strong>{r.vehicle.toUpperCase()}</strong>
                              <span>
                                {r.requests.join(" → ").toUpperCase()}
                              </span>
                              <small>
                                {r.quantity} kits · {r.travel} min
                              </small>
                            </div>
                          ))}
                          <p className="footnote">
                            {displayPlan.unmet.length} unmet request(s). Preview
                            holds no stock.
                          </p>
                          <button
                            className="button-primary full"
                            disabled={disabled || !displayPlan.routes.length}
                            onClick={() =>
                              act(async () => {
                                await api(path + "/commit", {
                                  plan_id: displayPlan.id,
                                  expected_revision: displayPlan.revision,
                                  key: key(),
                                });
                                setPlan(null);
                              })
                            }
                          >
                            <Check size={16} />
                            Reserve & commit plan
                          </button>
                        </div>
                      ) : (
                        <div className="empty-inline">
                          <RouteIcon size={28} />
                          <div>
                            <strong>
                              A feasible route, with resources to match.
                            </strong>
                            <p>
                              Preview capacity, shared depot stock and on-time
                              arrivals before reserving.
                            </p>
                          </div>
                        </div>
                      )}
                    </section>
                  </div>
                  <div className="lower-grid">
                    <section className="panel">
                      <div className="panel-heading">
                        <div>
                          <Boxes size={17} />
                          <h2>Relief requests</h2>
                        </div>
                        <span className="subtle">
                          {shown.metrics.unmet_kits} kits remaining
                        </span>
                      </div>
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>Destination</th>
                              <th>Kits</th>
                              <th>Due</th>
                              <th>Status</th>
                            </tr>
                          </thead>
                          <tbody>
                            {shown.requests.map((q) => (
                              <tr key={q.id}>
                                <td>
                                  <button
                                    className="text-button"
                                    onClick={() => setSelected(q.id)}
                                  >
                                    {
                                      shown.locations.find(
                                        (l) => l.id === q.destination,
                                      )?.name
                                    }
                                    <small>
                                      {q.id.toUpperCase()} · weight {q.weight}
                                    </small>
                                  </button>
                                </td>
                                <td>{q.quantity}</td>
                                <td>{clock(q.deadline)}</td>
                                <td>
                                  <span
                                    className={"delivery-status " + q.status}
                                  >
                                    {q.status === "delivered" && (
                                      <Check size={12} />
                                    )}{" "}
                                    {pretty(q.status)}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </section>
                    <section className="panel">
                      <div className="panel-heading">
                        <div>
                          <Activity size={17} />
                          <h2>Decision & event log</h2>
                        </div>
                        <button
                          disabled={busy || !healthy}
                          onClick={openReplay}
                        >
                          <History size={14} />
                          Replay
                        </button>
                      </div>
                      <div className="timeline">
                        {shown.decisions
                          .slice(-4)
                          .reverse()
                          .map((d) => (
                            <button
                              className="timeline-decision"
                              key={d.id}
                              onClick={() =>
                                act(
                                  async () =>
                                    setDetail(
                                      replay
                                        ? { decision: d }
                                        : await api(path + "/evidence/" + d.id),
                                    ),
                                  false,
                                )
                              }
                            >
                              <span className="timeline-dot" />
                              <div>
                                <small>
                                  {clock(d.time)} · {d.mode}
                                </small>
                                <p>{d.summary}</p>
                                <span className="evidence-link">
                                  Follow evidence <ArrowRight size={12} />
                                </span>
                              </div>
                            </button>
                          ))}
                        {shown.events
                          .slice(-5)
                          .reverse()
                          .map((e) => (
                            <div className="timeline-event" key={e.id}>
                              <span className="timeline-dot neutral" />
                              <div>
                                <small>
                                  {clock(e.time)} · {e.kind}
                                </small>
                                <p>{e.summary}</p>
                              </div>
                            </div>
                          ))}
                      </div>
                    </section>
                  </div>
                </>
              )}
              {tab === "evidence" && (
                <section className="panel developer-view">
                  <div className="panel-heading">
                    <div>
                      <Database size={18} />
                      <h2>Graph query evidence</h2>
                    </div>
                    <button
                      disabled={busy || !healthy || replay}
                      onClick={() =>
                        act(
                          async () =>
                            setDetail(await api(path + "/bottlenecks")),
                          false,
                        )
                      }
                    >
                      Shared road dependencies
                    </button>
                  </div>
                  <p className="developer-intro">
                    Fixed parameterised Cypher. Returned IDs and measured
                    durations come from actual queries. Paths traverse up to 12
                    road segments and preserve six alternatives per pair.
                  </p>
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Query</th>
                          <th>Parameters</th>
                          <th>Returned IDs</th>
                          <th>Duration</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(queries as any[])
                          .slice(-30)
                          .reverse()
                          .map((q, i) => (
                            <tr key={i}>
                              <td>
                                <code>{q.query}</code>
                              </td>
                              <td>
                                <code>{JSON.stringify(q.parameters)}</code>
                              </td>
                              <td className="ids">
                                {q.returned_ids.join(", ") ||
                                  `${q.rows} row(s)`}
                              </td>
                              <td>{q.milliseconds} ms</td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              )}
              {tab === "benchmarks" && (
                <section className="panel benchmark-panel">
                  <div className="panel-heading">
                    <div>
                      <FlaskConical size={18} />
                      <h2>Policy comparison</h2>
                    </div>
                    <button
                      disabled={
                        busy || !healthy || replay || benchJob === "running"
                      }
                      onClick={() =>
                        act(async () => {
                          const job = await api<any>("/benchmarks", {});
                          setBenchJob(job.status);
                        }, false)
                      }
                    >
                      {benchJob === "running" ? (
                        <LoaderCircle size={15} className="spin" />
                      ) : (
                        <Play size={15} />
                      )}
                      Run 30-run suite
                    </button>
                  </div>
                  <p className="developer-intro">
                    10 fixed worlds per policy. Same observations, planner,
                    resources and physical schedule. Seeded random inspections
                    use a separate policy RNG. Live LLM execution is excluded.
                  </p>
                  {bench ? (
                    <>
                      <div className="benchmark-cards">
                        {bench.aggregate.map((a: any) => (
                          <article key={a.policy}>
                            <span className="tiny-label">
                              {a.policy === "value"
                                ? "GRAPH INSPECTION VALUE"
                                : a.policy === "random"
                                  ? "RANDOM INSPECTIONS"
                                  : "NO INSPECTIONS"}
                            </span>
                            <strong>{a.mean_utility}</strong>
                            <p>mean delivered utility</p>
                            <small>
                              {a.mean_on_time_kits} on-time kits ·{" "}
                              {a.mean_inspections} checks
                            </small>
                          </article>
                        ))}
                      </div>
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>World</th>
                              <th>No inspection</th>
                              <th>Random</th>
                              <th>Graph value</th>
                              <th>Difference vs no inspection</th>
                            </tr>
                          </thead>
                          <tbody>
                            {bench.comparisons.map((c: any) => (
                              <tr key={c.seed}>
                                <td>{c.seed}</td>
                                <td>{c.none}</td>
                                <td>{c.random}</td>
                                <td>{c.value}</td>
                                <td>
                                  <span
                                    className={
                                      c.delta > 0
                                        ? "gain-positive"
                                        : c.delta < 0
                                          ? "gain-negative"
                                          : ""
                                    }
                                  >
                                    {c.delta > 0 ? "+" : ""}
                                    {c.delta} · {c.result}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <p className="footnote panel-footnote">
                        All per-world results, ties and regressions are retained
                        in benchmarks/results.json and results.csv. These
                        synthetic outcomes do not establish real-world
                        performance.
                      </p>
                    </>
                  ) : (
                    <div className="empty-inline">
                      <FlaskConical size={30} />
                      <p>
                        No completed suite yet. Run the reproducible benchmark
                        to populate this view.
                      </p>
                    </div>
                  )}
                </section>
              )}
              <footer>
                <span>
                  <ShieldCheck size={14} />
                  Synthetic data. Simulated actions. Evidence-backed decisions.
                </span>
                <div>
                  <button
                    disabled={disabled || auto}
                    onClick={() =>
                      act(async () => {
                        await api(path + "/disrupt", { key: key() });
                        setPlan(null);
                        setRanking(null);
                      })
                    }
                  >
                    Trigger capacity disruption
                  </button>
                  <button
                    disabled={busy || replay || !healthy || auto}
                    onClick={() => {
                      if (
                        window.confirm(
                          "Reset only this LastMile run and start the selected scenario?",
                        )
                      )
                        newRun(true);
                    }}
                  >
                    <RefreshCw size={12} />
                    Reset selected run
                  </button>
                </div>
              </footer>
            </>
          )}
        </main>
      </div>
      {detail !== null && (
        <div className="modal-backdrop" onClick={() => setDetail(null)}>
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label="Decision evidence"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="panel-heading">
              <h2>Connected evidence</h2>
              <button
                autoFocus
                aria-label="Close evidence"
                onClick={() => setDetail(null)}
              >
                <X size={18} />
              </button>
            </div>
            <pre>{JSON.stringify(detail, null, 2)}</pre>
          </section>
        </div>
      )}
    </div>
  );
}
