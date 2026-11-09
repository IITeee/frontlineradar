// ===== Configuration =====
// Set to a real endpoint (e.g. Buttondown/Mailchimp/Formspree URL) to enable signups.
// While empty, submit shows "Coming soon" (same pattern as pandemicradar.org).
const SIGNUP_ENDPOINT = "";

// TODO(giscus): fill in repoId + categoryId from https://giscus.app once the
// GitHub repo exists and Discussions are enabled. While either is empty the
// Community section shows "Comments open soon" and loads nothing.
const GISCUS = {
  repo: "IITeee/frontlineradar",
  repoId: "",        // TODO
  category: "Announcements",
  categoryId: "",    // TODO
  mapping: "specific",
  theme: "preferred_color_scheme",
  lang: "en",
  reactionsEnabled: "1",
  inputPosition: "top",
  loading: "lazy",
  topics: ["General", "Front line & maps", "Strikes & air defence", "Diplomacy", "Data & methodology"]
};

const $ = id => document.getElementById(id);
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

// theme toggle
$("theme") && ($("theme").onclick = () => {
  const r = document.documentElement; r.dataset.theme = r.dataset.theme === "light" ? "dark" : "light";
  try { localStorage.frTheme = r.dataset.theme } catch (e) {}
  location.reload();
});

// strikes chart
function strikeChart() {
  const D = window.FR_DATA, el = $("strikeChart");
  if (!el || !D || !D.strikes || !window.Chart) return;
  Chart.defaults.color = css("--mut"); Chart.defaults.font.family = "Inter"; Chart.defaults.borderColor = css("--line");
  let chart;
  function draw(range) {
    const rows = range === "weekly" ? D.strikes.weekly : D.strikes.daily;
    const labels = rows.map(r => r.week || r.date);
    const cfg = {
      data: { labels, datasets: [
        { type: "bar", label: "Drones launched", data: rows.map(r => r.drones_launched), backgroundColor: "#ffc53d", stack: "l", order: 2 },
        { type: "bar", label: "Missiles launched", data: rows.map(r => r.missiles_launched), backgroundColor: "#ff5d73", stack: "l", order: 2 },
        { type: "line", label: "Reported shot down / suppressed", data: rows.map(r => r.drones_destroyed + r.missiles_destroyed),
          borderColor: "#4d8dff", backgroundColor: "#4d8dff", pointRadius: 0, borderWidth: 2, tension: .25, order: 1 }
      ]},
      options: { maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
        scales: { x: { stacked: true, ticks: { maxTicksLimit: 10 } }, y: { stacked: true, beginAtZero: true } },
        plugins: { legend: { position: "bottom" } } }
    };
    if (chart) chart.destroy();
    chart = new Chart(el, cfg);
  }
  document.querySelectorAll(".seg button").forEach(b => b.onclick = () => {
    document.querySelectorAll(".seg button").forEach(x => x.setAttribute("aria-pressed", x === b ? "true" : "false"));
    draw(b.dataset.range);
  });
  draw("daily");
}
if (window.Chart) strikeChart(); else window.addEventListener("load", strikeChart);

// territorial control — dissolved areas only, no unit markers or arrows
function controlMap() {
  if (!window.L) return;
  const light = document.documentElement.dataset.theme === "light";
  const styles = {
    UA: { color: "#2c6aa3", weight: 0.6, fillColor: "#7eb6e6", fillOpacity: light ? 0.38 : 0.28 },
    RU: { color: "#8d2e2e", weight: 0.7, fillColor: "#d4524a", fillOpacity: 0.62 },
    CONTESTED: { color: "#c4840a", weight: 2.5, fillColor: "#f0b429", fillOpacity: 0.95 }
  };
  const labels = { UA: "Ukrainian-controlled", RU: "Russian-controlled", CONTESTED: "Contested" };
  document.querySelectorAll("[data-control-map]").forEach(el => {
    if (el.dataset.ready) return;
    el.dataset.ready = "1";
    const map = L.map(el, { scrollWheelZoom: false, minZoom: 5, maxZoom: 8, zoomControl: true });
    map.attributionControl.setPrefix("Leaflet");
    map.attributionControl.addAttribution("Areas derived from VIINA 2.0 (ODbL)");
    fetch(el.dataset.src).then(r => { if (!r.ok) throw new Error(r.status); return r.json(); }).then(gj => {
      const order = { UA: 0, RU: 1, CONTESTED: 2 };
      const features = (gj.features || []).slice().sort((a, b) => (order[a.properties.status] ?? 9) - (order[b.properties.status] ?? 9));
      const layer = L.geoJSON({ type: "FeatureCollection", features }, {
        style: f => styles[f.properties.status] || styles.UA,
        onEachFeature: (f, lyr) => {
          const name = f.properties.label || labels[f.properties.status] || "Assessed area";
          lyr.bindPopup("<b>" + name + "</b><br>Area-level assessment. Not a unit location.");
        }
      }).addTo(map);
      if (layer.getBounds().isValid()) map.fitBounds(layer.getBounds(), { padding: [12, 12] });
    }).catch(() => { el.insertAdjacentHTML("beforeend", '<p class="map-fallback">Control map could not be loaded.</p>'); });
  });
}
if (window.L) controlMap(); else window.addEventListener("load", controlMap);

// signup
$("signup") && ($("signup").onsubmit = async e => {
  e.preventDefault(); const m = $("signup-msg"), email = e.target.querySelector("input").value;
  if (!SIGNUP_ENDPOINT) { m.textContent = "Coming soon – the newsletter launches shortly. Thanks for your interest!"; return }
  try { await fetch(SIGNUP_ENDPOINT, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }) }); m.textContent = "Thanks! Check your inbox to confirm." }
  catch { m.textContent = "Something went wrong, please try again." }
});

// community — topic tabs switch the Giscus term (data-mapping "specific")
(function () {
  const tabs = $("topic-tabs"), slot = $("giscus"), soon = $("community-soon");
  if (!tabs || !slot || !soon) return;
  const ready = !!(GISCUS.repoId && GISCUS.categoryId);
  const theme = () => { try { return localStorage.frTheme || GISCUS.theme } catch (e) { return GISCUS.theme } };
  let term = GISCUS.topics[0], mounted = false;
  function send(config) {
    const frame = slot.querySelector("iframe.giscus-frame");
    if (!frame) return false;
    frame.contentWindow.postMessage({ giscus: { setConfig: config } }, "https://giscus.app"); return true;
  }
  function mount() {
    if (mounted) return; mounted = true;
    const s = document.createElement("script");
    s.src = "https://giscus.app/client.js"; s.async = true; s.crossOrigin = "anonymous";
    const attrs = { "data-repo": GISCUS.repo, "data-repo-id": GISCUS.repoId, "data-category": GISCUS.category, "data-category-id": GISCUS.categoryId,
      "data-mapping": GISCUS.mapping, "data-term": term, "data-strict": "0", "data-reactions-enabled": GISCUS.reactionsEnabled, "data-emit-metadata": "0",
      "data-input-position": GISCUS.inputPosition, "data-theme": theme(), "data-lang": GISCUS.lang, "data-loading": GISCUS.loading };
    Object.entries(attrs).forEach(([k, v]) => s.setAttribute(k, v));
    slot.replaceChildren(s);
  }
  function select(next, btn) {
    term = next;
    tabs.querySelectorAll("button").forEach(b => b.setAttribute("aria-selected", b === btn ? "true" : "false"));
    if (!ready) return;
    if (!send({ term })) mount();
  }
  GISCUS.topics.forEach((t, i) => {
    const b = document.createElement("button"); b.type = "button"; b.role = "tab"; b.textContent = t;
    b.setAttribute("aria-selected", i === 0 ? "true" : "false"); b.onclick = () => select(t, b); tabs.appendChild(b);
  });
  if (!ready) { soon.hidden = false; return }
  soon.remove(); select(term, tabs.querySelector("button"));
})();
