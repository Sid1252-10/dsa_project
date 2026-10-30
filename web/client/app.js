const $ = (id) => document.getElementById(id);

// Mapbox Configuration
const MAPBOX_TOKEN = "pk.eyJ1Ijoic2lkMTI1MiIsImEiOiJjbXZ1bXVldXMwN3h6Mnlxc25sZGVvdDJ2In0.hA6AyBIRBka2l0hXFkiVzg";

const CITY_COORDS = {
  "amritsar": [74.8723, 31.6340],
  "tarn_taran": [74.7500, 31.4800],
  "gurdaspur": [75.4000, 32.0300],
  "pathankot": [75.6400, 32.2700],
  "hoshiarpur": [75.9800, 32.0400],
  "kapurthala": [75.1500, 31.4200],
  "jalandhar": [75.5800, 31.3300],
  "ludhiana": [75.8600, 30.9000],
  "moga": [75.6500, 30.5500],
  "firozpur": [74.6300, 30.9100],
  "fazilka": [74.2200, 30.5400],
  "abohar": [74.3500, 30.3500],
  "bathinda": [74.9400, 30.2100],
  "faridkot": [75.1500, 30.3500],
  "muktsar": [74.6500, 30.3500],
  "mansa": [75.1500, 29.8500],
  "barnala": [75.7500, 30.3500],
  "sangrur": [75.8500, 30.2500],
  "patiala": [76.3800, 30.3300],
  "malerkotla": [76.4500, 30.5000],
  "rupnagar": [76.3500, 30.5400],
  "mohali": [76.7200, 30.7000],
  "chandigarh": [76.7800, 30.7300],
};

let graph = null;
let appState = null;
let selectedRoute = null;
let lastRequestId = null;
let map = null;
let markers = [];

function updateCityLabelVisibility() {
  if (!map) return;
  const zoom = map.getZoom();
  for (const marker of markers) {
    const element = marker.getElement();
    const threshold = element.dataset.kind === "major" ? 6 : 8;
    element.classList.toggle("city-marker--labeled", zoom >= threshold);
  }
}

function cityName(cityId) {
  const c = graph?.cities?.find((x) => x.id === cityId);
  return c ? c.name : cityId;
}

function routeText(route) {
  if (!route?.path?.length) return "—";
  return route.path.map(cityName).join(" → ");
}

async function apiGet(url) {
  const r = await fetch(url);
  const j = await r.json();
  if (!r.ok) throw new Error(j?.error || "Request failed");
  return j;
}

async function apiPost(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json();
  if (!r.ok) throw new Error(j?.error || "Request failed");
  return j;
}

function setOptions(selectEl, cities) {
  selectEl.innerHTML = "";
  for (const c of cities) {
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = `${c.name}${c.kind === "major" ? " (major)" : ""}`;
    selectEl.appendChild(opt);
  }
}

async function initMap() {
  if (!MAPBOX_TOKEN) {
    $("mapStatus").textContent = "Mapbox token is missing. Add a public token to web/client/app.js.";
    return;
  }
  if (!window.mapboxgl) {
    $("mapStatus").textContent = "Mapbox GL JS failed to load. Please check your internet connection.";
    return;
  }

  try {
    mapboxgl.accessToken = MAPBOX_TOKEN;
    map = new mapboxgl.Map({
      container: "mapContainer",
      style: "mapbox://styles/mapbox/streets-v12",
      center: [75.3, 31.1],
      zoom: 7,
    });

    await new Promise((resolve, reject) => {
      map.once("load", resolve);
      map.once("error", (event) => reject(event.error || new Error("Mapbox map failed to load.")));
    });
    const coordinates = Object.values(CITY_COORDS);
    const bounds = coordinates.reduce(
      (result, [lng, lat]) => result.extend([lng, lat]),
      new mapboxgl.LngLatBounds(coordinates[0], coordinates[0])
    );
    map.fitBounds(bounds, { padding: 36, maxZoom: 7 });
    map.on("error", (event) => {
      console.error("Mapbox map error:", event.error || event);
      $("mapStatus").textContent = "Mapbox could not load map data. Check the token, allowed URLs, and network.";
    });
    map.on("zoom", updateCityLabelVisibility);
  } catch (err) {
    console.error("Mapbox init error:", err);
    $("mapStatus").textContent = "Failed to initialize Mapbox map. Please check the token or network.";
  }
}

function drawMap() {
  if (!map || !graph) return;

  // Clear markers
  markers.forEach((m) => m.remove());
  markers = [];

  // Clear existing road/route sources
  if (map.getSource("roads")) {
    if (map.getLayer("roads-layer")) map.removeLayer("roads-layer");
    map.removeSource("roads");
  }
  if (map.getSource("selected-route")) {
    if (map.getLayer("route-layer")) map.removeLayer("route-layer");
    map.removeSource("selected-route");
  }

  const byId = new Map(graph.cities.map((c) => [c.id, c]));

  // 1. All Roads
  const roadsFeatures = [];
  for (const [a, b] of graph.roads) {
    const coordA = CITY_COORDS[a];
    const coordB = CITY_COORDS[b];
    if (!coordA || !coordB) continue;
    roadsFeatures.push({
      type: "Feature",
      geometry: {
        type: "LineString",
        coordinates: [coordA, coordB],
      },
    });
  }

  map.addSource("roads", {
    type: "geojson",
    data: {
      type: "FeatureCollection",
      features: roadsFeatures,
    },
  });

  map.addLayer({
    id: "roads-layer",
    type: "line",
    source: "roads",
    paint: {
      "line-color": "rgba(255,255,255,0.2)",
      "line-width": 2,
    },
  });

  // 2. Selected Route Highlight
  if (selectedRoute?.path?.length >= 2) {
    const routeFeatures = [];
    for (let i = 0; i < selectedRoute.path.length - 1; i++) {
      const a = selectedRoute.path[i];
      const b = selectedRoute.path[i + 1];
      const coordA = CITY_COORDS[a];
      const coordB = CITY_COORDS[b];
      if (!coordA || !coordB) continue;
      routeFeatures.push({
        type: "Feature",
        geometry: {
          type: "LineString",
          coordinates: [coordA, coordB],
        },
      });
    }

    map.addSource("selected-route", {
      type: "geojson",
      data: {
        type: "FeatureCollection",
        features: routeFeatures,
      },
    });

    map.addLayer({
      id: "route-layer",
      type: "line",
      source: "selected-route",
      paint: {
        "line-color": "#47d18c",
        "line-width": 5,
      },
    });
  }

  // 3. Cities as Markers
  for (const c of graph.cities) {
    const coord = CITY_COORDS[c.id];
    if (!coord) continue;

    const el = document.createElement("div");
    el.className = `city-marker city-marker--${c.kind}`;
    el.dataset.kind = c.kind;
    el.style.width = c.kind === "major" ? "12px" : "8px";
    el.style.height = c.kind === "major" ? "12px" : "8px";
    el.style.borderRadius = "50%";
    el.style.backgroundColor = c.kind === "major" ? "#5b8cff" : "#91a6ff";
    el.style.border = "1px solid white";
    el.style.boxShadow = "0 0 4px rgba(0,0,0,0.5)";
    el.style.cursor = "pointer";

    const label = document.createElement("span");
    label.className = "city-marker__label";
    label.textContent = c.name;
    el.appendChild(label);

    const popup = new mapboxgl.Popup({ offset: 25 }).setHTML(`<b>${c.name}</b>`);
    const marker = new mapboxgl.Marker(el)
      .setPopup(popup)
      .setLngLat(coord)
      .addTo(map);

    markers.push(marker);
  }
  updateCityLabelVisibility();

  if (selectedRoute?.path?.length) {
    $("mapStatus").textContent = `Route: ${routeText(selectedRoute)} (${selectedRoute.distance} km)`;
  } else {
    $("mapStatus").textContent = "Click \"Show path\" on a request to highlight the route.";
  }
}

function renderDriverSelect() {
  const sel = $("driverSelect");
  sel.innerHTML = "";
  for (const d of appState?.drivers ?? []) {
    const opt = document.createElement("option");
    opt.value = d.id;
    opt.textContent = `${d.name} · ${cityName(d.cityId)} · ${d.status}`;
    sel.appendChild(opt);
  }
}

function renderIncomingShares(userName) {
  const container = $("incomingShares");
  container.innerHTML = "";
  if (!userName) return;

  const rides = (appState?.rides ?? []).filter((r) => r.primaryUser === userName && r.status === "active");
  if (!rides.length) {
    container.innerHTML = `<div class="muted">No active ride for ${userName}.</div>`;
    return;
  }

  for (const ride of rides) {
    const pending = (ride.shareProposals ?? []).filter((p) => p.status === "pending");
    if (!pending.length) {
      const el = document.createElement("div");
      el.className = "item";
      el.innerHTML = `
        <div class="item__title">Ride ${ride.id}</div>
        <div class="item__sub">No pending share proposals.</div>
      `;
      container.appendChild(el);
      continue;
    }

    for (const p of pending) {
      const el = document.createElement("div");
      el.className = "item";
      el.innerHTML = `
        <div class="item__title">${p.fromUser} wants to share</div>
        <div class="item__sub">Pickup: ${cityName(p.pickupCityId)} · Drop: ${cityName(p.dropCityId)}</div>
        <div class="item__sub">Ride: ${ride.id} · Driver: ${ride.driverName}</div>
        <div class="item__actions">
          <button class="btn btn--ok" data-act="accept" data-ride="${ride.id}" data-proposal="${p.id}">Accept</button>
          <button class="btn btn--danger" data-act="reject" data-ride="${ride.id}" data-proposal="${p.id}">Reject</button>
        </div>
      `;
      el.addEventListener("click", async (e) => {
        const btn = e.target.closest("button");
        if (!btn) return;
        const rideId = btn.dataset.ride;
        const proposalId = btn.dataset.proposal;
        const accept = btn.dataset.act === "accept";
        try {
          await apiPost("/api/share/decide", { rideId, proposalId, accept });
          await refreshAll();
        } catch (err) {
          alert(err.message);
        }
      });
      container.appendChild(el);
    }
  }
}

function renderDriverView() {
  const driverId = $("driverSelect").value;
  const driver = (appState?.drivers ?? []).find((d) => d.id === driverId);
  $("driverStatus").textContent = driver
    ? `${driver.name} is ${driver.status} at ${cityName(driver.cityId)}`
    : "Select a driver.";

  const reqContainer = $("driverRequests");
  reqContainer.innerHTML = "";

  const relevant = (appState?.requests ?? []).filter((r) => r.status === "pending_driver");
  if (!relevant.length) {
    reqContainer.innerHTML = `<div class="muted">No pending requests right now.</div>`;
  } else {
    for (const r of relevant) {
      const el = document.createElement("div");
      el.className = "item";
      el.innerHTML = `
        <div class="item__title">${r.userName}: ${cityName(r.fromCityId)} → ${cityName(r.toCityId)}</div>
        <div class="item__sub">Route: ${routeText(r.route)} (distance: ${r.route.distance})</div>
        <div class="item__sub">Persons: <b>${r.numPersons ?? 1}</b> &nbsp;|&nbsp; Fare: \u20b9${r.soloFare}${r.wantsSharing ? " · sharing enabled" : ""}</div>
        <div class="item__actions">
          <button class="btn btn--ok" data-act="accept" data-req="${r.id}">Accept</button>
          <button class="btn btn--danger" data-act="decline" data-req="${r.id}">Decline</button>
          <button class="btn" data-act="show" data-req="${r.id}">Show path</button>
        </div>
      `;
      el.addEventListener("click", async (e) => {
        const btn = e.target.closest("button");
        if (!btn) return;
        const reqId = btn.dataset.req;
        if (btn.dataset.act === "show") {
          const req = (appState?.requests ?? []).find((x) => x.id === reqId);
          selectedRoute = req?.route ?? null;
          drawMap();
          return;
        }
        const accept = btn.dataset.act === "accept";
        try {
          await apiPost("/api/driver/respond", { driverId, requestId: reqId, accept });
          await refreshAll();
        } catch (err) {
          alert(err.message);
        }
      });
      reqContainer.appendChild(el);
    }
  }

  const nContainer = $("driverNotifications");
  nContainer.innerHTML = "";
  const notes = (appState?.notifications ?? []).filter((n) => n.driverId === driverId).slice(-10).reverse();
  if (!notes.length) {
    nContainer.innerHTML = `<div class="muted">No driver notifications yet.</div>`;
  } else {
    for (const n of notes) {
      const el = document.createElement("div");
      el.className = "item";
      el.innerHTML = `
        <div class="item__title">${n.type}</div>
        <div class="item__sub">${n.message}</div>
        <div class="item__sub">${n.at}</div>
      `;
      nContainer.appendChild(el);
    }
  }
}

function renderShareCandidates() {
  // no-op placeholder (populated by findShareBtn)
}

function renderQueues() {
  const pending = $("pendingQueue");
  const active  = $("activeQueue");
  pending.innerHTML = "";
  active.innerHTML  = "";

  // Pending Request Queue — FIFO order (earliest first)
  const pendingReqs = (appState?.requests ?? []).filter((r) => r.status === "pending_driver");
  if (!pendingReqs.length) {
    pending.innerHTML = `<div class="muted" style="font-size:12px;padding:4px">No pending requests.</div>`;
  } else {
    for (const r of pendingReqs) {
      const el = document.createElement("div");
      el.className = "queue-item";
      el.style.cursor = "pointer";
      el.title = "Click to show route on map";
      el.innerHTML = `
        <span class="queue-item__id">${r.id}</span>
        <span class="queue-item__route">${r.userName}: ${cityName(r.fromCityId)} → ${cityName(r.toCityId)}</span>
        <span class="queue-item__badge badge--pending">waiting</span>
      `;
      el.addEventListener("click", () => {
        selectedRoute = (selectedRoute === r.route) ? null : r.route;
        drawMap();
      });
      pending.appendChild(el);
    }
  }

  // Active Rides Queue — with live countdown
  const activeRides = (appState?.rides ?? []).filter((r) => r.status === "active");
  if (!activeRides.length) {
    active.innerHTML = `<div class="muted" style="font-size:12px;padding:4px">No active rides.</div>`;
  } else {
    for (const r of activeRides) {
      const passCount = r.passengers?.length ?? 1;
      const el = document.createElement("div");
      el.className = "queue-item";
      el.style.cursor = "pointer";
      el.title = "Click to show route on map";
      const countdownId = `cd-${r.id}`;
      el.innerHTML = `
        <span class="queue-item__id">${r.id}</span>
        <span class="queue-item__route">${r.driverName}: ${cityName(r.fromCityId)} → ${cityName(r.toCityId)}${passCount > 1 ? ` (×${passCount})` : ""}</span>
        <span class="queue-item__badge badge--active" id="${countdownId}">active</span>
      `;
      el.addEventListener("click", () => {
        selectedRoute = (selectedRoute === r.route) ? null : r.route;
        drawMap();
      });
      // Store the autoCompleteAt on the element for the countdown timer
      if (r.autoCompleteAt) el.dataset.completeAt = r.autoCompleteAt;
      active.appendChild(el);
    }
  }
}

// Update countdown badges every second (no server fetch needed)
function tickCountdowns() {
  const now = Date.now();
  document.querySelectorAll("#activeQueue .queue-item").forEach((el) => {
    const completeAt = el.dataset.completeAt;
    if (!completeAt) return;
    const badge = el.querySelector(".queue-item__badge");
    if (!badge) return;
    const remaining = Math.max(0, Math.round((new Date(completeAt).getTime() - now) / 1000));
    badge.textContent = remaining > 0 ? `⏱ ${remaining}s` : "completing...";
    badge.style.background = remaining <= 10
      ? "rgba(255,91,122,.18)"  // red tint when nearly done
      : "rgba(71,209,140,.14)";
    badge.style.color = remaining <= 10 ? "#ff5b7a" : "var(--ok)";
  });
}

function renderTopbar() {
  $("serverTime").textContent = appState?.serverTime ? `Server: ${appState.serverTime}` : "";
}

async function refreshAll() {
  const prevFromCity = $("fromCity").value;
  const prevToCity = $("toCity").value;
  // Remember current share city selections so refreshAll doesn't reset them
  const prevShareFrom = $("shareFromCity").value;
  const prevShareTo   = $("shareToCity").value;

  graph = await apiGet("/api/graph");
  appState = await apiGet("/api/state");

  setOptions($("fromCity"), graph.cities);
  setOptions($("toCity"), graph.cities);
  setOptions($("shareFromCity"), graph.cities);
  setOptions($("shareToCity"), graph.cities);

  if (prevFromCity) $("fromCity").value = prevFromCity;
  if (prevToCity) $("toCity").value = prevToCity;
  // Restore share city selections if they were set
  if (prevShareFrom) $("shareFromCity").value = prevShareFrom;
  if (prevShareTo)   $("shareToCity").value   = prevShareTo;

  renderDriverSelect();
  renderTopbar();
  drawMap();
  renderQueues();
  renderDriverView();
  renderIncomingShares($("userName").value.trim());
}

function shareCandidateCard(candidate, requestId) {
  const el = document.createElement("div");
  el.className = "item";
  const hint = candidate.canUseDefaultPickupDrop
    ? `<span class="pill" style="margin-top:6px">Pickup/drop on route: <b>YES</b></span>`
    : `<span class="pill" style="margin-top:6px">Pickup/drop on route: <b>Choose manually</b></span>`;
  const statusPill = `<span class="pill" style="margin-top:6px">Ride status: <b>${candidate.rideStatus}</b></span>`;
  const canRequest = candidate.rideStatus === "active";
  el.innerHTML = `
    <div class="item__title">Ride ${candidate.rideId} · Driver: ${candidate.driverName}</div>
    <div class="item__sub">Route: ${routeText(candidate.route)} (distance: ${candidate.route.distance})</div>
    <div style="display:flex; gap:8px; flex-wrap:wrap">${statusPill}${hint}</div>
    <div class="item__actions">
      <button class="btn btn--primary" data-act="propose" ${canRequest ? "" : "disabled"}>Request share</button>
      <button class="btn" data-act="show">Show path</button>
    </div>
  `;

  el.addEventListener("click", async (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    if (btn.dataset.act === "show") {
      selectedRoute = candidate.route;
      drawMap();
      return;
    }
    const pickupCityId = $("shareFromCity").value;
    const dropCityId = $("shareToCity").value;
    try {
      await apiPost("/api/share/propose", {
        requestId,
        rideId: candidate.rideId,
        pickupCityId,
        dropCityId
      });
      await refreshAll();
      alert("Share request sent to the rider in that cab. They must approve.");
    } catch (err) {
      alert(err.message);
    }
  });

  return el;
}

function wireEvents() {
  $("refreshBtn").addEventListener("click", refreshAll);
  $("resetBtn").addEventListener("click", async () => {
    try {
      await apiPost("/api/reset", {});
      lastRequestId = null;
      selectedRoute = null;
      $("userRequestResult").innerHTML = "";
      $("shareCandidates").innerHTML = "";
      await refreshAll();
    } catch (err) {
      alert(err.message);
    }
  });
  $("driverSelect").addEventListener("change", renderDriverView);

  $("submitRide").addEventListener("click", async () => {
    const userName   = $("userName").value.trim();
    const fromCityId = $("fromCity").value;
    const toCityId   = $("toCity").value;
    const wantsSharing = $("wantsSharing").checked;
    const numPersons   = parseInt($("numPersons").value, 10) || 1;
    if (!userName) {
      alert("Enter a username.");
      return;
    }
    if (fromCityId === toCityId) {
      alert("From and To cannot be the same city.");
      return;
    }
    try {
      const res = await apiPost("/api/request", { userName, fromCityId, toCityId, wantsSharing, numPersons });
      const req = res.request;
      lastRequestId = req.id;
      selectedRoute = null;   // don't auto-highlight — use "Show path" button instead
      $("userRequestResult").innerHTML = `
        <div class="pill">Request: <b>${req.id}</b></div>
        <div class="pill">Persons: <b>${req.numPersons ?? numPersons}</b></div>
        <div class="pill">Assigned driver: <b>${req.assignedDriverId ?? "any"}</b></div>
        <div class="pill">Fare: <b>\u20b9${req.soloFare}</b></div>
        <div class="muted" style="margin-top:8px">Route: ${routeText(req.route)} (${req.route.distance} km)</div>
      `;
      $("shareFromCity").value = fromCityId;
      $("shareToCity").value   = toCityId;
      await refreshAll();
    } catch (err) {
      $("userRequestResult").textContent = err.message;
    }
  });

  $("findShareBtn").addEventListener("click", async () => {
    const container = $("shareCandidates");
    container.innerHTML = "";
    if (!lastRequestId) {
      container.innerHTML = `<div class="muted">Submit a request with “Enable sharing” first.</div>`;
      return;
    }
    if ($("shareFromCity").value === $("shareToCity").value) {
      container.innerHTML = `<div class="muted">Share pickup and drop cannot be the same city.</div>`;
      return;
    }
    try {
      const res = await apiGet(`/api/share/candidates?requestId=${encodeURIComponent(lastRequestId)}`);
      if (!res.candidates.length) {
        // Show a helpful hint if the server sent one
        const hint = res.hint || "No rides found going the same way right now.";
        container.innerHTML = `<div class="muted">${hint}</div>`;
        return;
      }
      for (const c of res.candidates) {
        container.appendChild(shareCandidateCard(c, lastRequestId));
      }
    } catch (err) {
      container.innerHTML = `<div class="muted">${err.message}</div>`;
    }
  });

  $("userName").addEventListener("change", () => renderIncomingShares($("userName").value.trim()));
}

async function main() {
  wireEvents();
  await initMap();
  await refreshAll();

  // Live countdown ticker — updates every second, no server call
  setInterval(tickCountdowns, 1000);

  // Auto-poll server every 4 s so ride completions appear without manual refresh
  setInterval(async () => {
    try { await refreshAll(); } catch (_) { /* ignore network blip */ }
  }, 4000);
}

main().catch((e) => {
  // eslint-disable-next-line no-console
  console.error(e);
  alert(e.message);
});
