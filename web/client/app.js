// ═══════════════════════════════════════════════════════════
// Yarivo — Complete Client App Logic
// Interactive Mapbox Map + Smart City Search + Full DSA Flow
// ═══════════════════════════════════════════════════════════

const $ = (id) => document.getElementById(id);

// ── State ─────────────────────────────────────────────────
let graph            = null;
let appState         = null;
let selectedRoute    = null;
let lastRequestId    = null;
let currentScreen    = null;
let autoRefreshTimer = null;
let selectedVehicle  = 'sedan';
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

const maps = { passenger: null, driver: null };
const mapMarkers = { passenger: [], driver: [] };
const mapViewSignatures = { passenger: '', driver: '' };
const selectedPlaces = { from: null, to: null };
let routeLookupTimer = null;

// ── Vehicle configuration ─────────────────────────────────
const VEHICLE_CONFIG = {
  mini: {
    name: 'Mini',
    model: 'Maruti Swift',
    capacity: 2,
    icon: '🚗',
    plate: 'PB-08-CD-5678',
    multiplier: 1.0,
    desc: 'Hatchback · Solo/duo travel'
  },
  sedan: {
    name: 'Sedan',
    model: 'Maruti Dzire',
    capacity: 4,
    icon: '🚙',
    plate: 'PB-10-AB-1234',
    multiplier: 1.25,
    desc: 'Comfortable sedan · Up to 4 riders'
  },
  suv: {
    name: 'SUV',
    model: 'Maruti Ertiga',
    capacity: 6,
    icon: '🚐',
    plate: 'PB-03-EF-9012',
    multiplier: 1.6,
    desc: 'Spacious SUV · Up to 6 passengers'
  },
  premium: {
    name: 'Premium',
    model: 'Toyota Camry',
    capacity: 4,
    icon: '⭐',
    plate: 'PB-02-GH-3456',
    multiplier: 2.2,
    desc: 'Luxury executive travel'
  },
  shared: {
    name: 'Shared',
    model: 'Shared Cab',
    capacity: 2,
    icon: '🤝',
    plate: 'PB-65-SH-7788',
    multiplier: 0.65,
    desc: 'Affordable shared ride'
  }
};

const DRIVER_VEHICLES = {
  d1: { model: 'Sedan (Dzire)', plate: 'PB-10-AB-1234', type: 'sedan', icon: '🚙' },
  d2: { model: 'Mini (Swift)', plate: 'PB-08-CD-5678', type: 'mini', icon: '🚗' },
  d3: { model: 'SUV (Ertiga)', plate: 'PB-03-EF-9012', type: 'suv', icon: '🚐' },
  d4: { model: 'Premium (Camry)', plate: 'PB-02-GH-3456', type: 'premium', icon: '⭐' }
};

// ── Persistent Request Vehicle Store ──────────────────────
function getRequestVehicle(requestId) {
  try {
    const map = JSON.parse(localStorage.getItem('cabsystem_request_vehicles') || '{}');
    return map[requestId] || 'sedan';
  } catch {
    return 'sedan';
  }
}

function saveRequestVehicle(requestId, vehicleType) {
  try {
    const map = JSON.parse(localStorage.getItem('cabsystem_request_vehicles') || '{}');
    map[requestId] = vehicleType;
    localStorage.setItem('cabsystem_request_vehicles', JSON.stringify(map));
  } catch (_) {}
}

// ── API Helpers (Preserved Exactly) ───────────────────────
async function apiGet(url) {
  const r = await fetch(url);
  const j = await r.json();
  if (!r.ok) throw new Error(j?.error || 'Request failed');
  return j;
}

async function apiPost(url, body) {
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  const j = await r.json();
  if (!r.ok) throw new Error(j?.error || 'Request failed');
  return j;
}

// ── Utilities ─────────────────────────────────────────────
function cityName(cityId) {
  const c = graph?.cities?.find((x) => x.id === cityId);
  return escapeHtml(c ? c.name : cityId);
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
}

function newSearchSessionToken() {
  return window.crypto?.randomUUID?.() || `search-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function routeText(route) {
  if (!route?.path?.length) return '—';
  return route.path.map(cityName).join(' → ');
}

function findShortestPath(fromId, toId) {
  if (!graph?.cities?.length || !fromId || !toId) return null;
  if (fromId === toId) return { path: [fromId], distance: 0 };

  const byId = new Map(graph.cities.map(city => [city.id, city]));
  const distances = new Map(graph.cities.map(city => [city.id, Infinity]));
  const previous = new Map();
  const visited = new Set();
  if (!byId.has(fromId) || !byId.has(toId)) return null;
  distances.set(fromId, 0);

  while (visited.size < graph.cities.length) {
    let current = null;
    let best = Infinity;
    for (const [cityId, distance] of distances) {
      if (!visited.has(cityId) && distance < best) {
        current = cityId;
        best = distance;
      }
    }
    if (current === null || current === toId) break;
    visited.add(current);

    for (const edge of graph.roads) {
      const [a, b, explicitWeight] = edge;
      let neighbor = null;
      if (a === current) neighbor = b;
      else if (b === current) neighbor = a;
      if (!neighbor || visited.has(neighbor)) continue;
      const cityA = byId.get(a);
      const cityB = byId.get(b);
      if (!cityA || !cityB) continue;
      const weight = Number.isFinite(explicitWeight) && explicitWeight > 0
        ? explicitWeight
        : Math.max(1, Math.round(Math.hypot(cityA.x - cityB.x, cityA.y - cityB.y) / 20));
      const candidate = distances.get(current) + weight;
      if (candidate < distances.get(neighbor)) {
        distances.set(neighbor, candidate);
        previous.set(neighbor, current);
      }
    }
  }

  const distance = distances.get(toId);
  if (!Number.isFinite(distance)) return null;
  const path = [];
  for (let cityId = toId; cityId; cityId = previous.get(cityId)) {
    path.unshift(cityId);
    if (cityId === fromId) break;
  }
  return path[0] === fromId ? { path, distance } : null;
}

function formatTime(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function statusBadge(status) {
  const map = {
    pending_driver: ['badge-pending',   '⏳ Pending Driver'],
    accepted:       ['badge-active',    '✅ Active Ride'],
    completed:      ['badge-completed', '🏁 Completed'],
    declined:       ['badge-declined',  '❌ Declined'],
    cancelled:      ['badge-declined',  '🚫 Cancelled'],
    expired:        ['badge-expired',   '⌛ Expired'],
    idle:           ['badge-idle',      '🟢 Idle'],
    on_ride:        ['badge-on-ride',   '🚕 On Ride'],
    active:         ['badge-active',    '🟢 Active'],
  };
  const [cls, label] = map[status] ?? ['badge-pending', status];
  return `<span class="badge ${cls}">${label}</span>`;
}

function notifIcon(type) {
  const map = {
    request_created:  '📋',
    ride_started:     '🚀',
    ride_completed:   '🏁',
    share_proposed:   '🤝',
    share_accepted:   '✅',
    share_rejected:   '❌',
    share_expired:    '⌛',
    request_declined: '❌',
    state_reset:      '🔄',
  };
  return map[type] ?? '📣';
}

// ── Screen navigation ─────────────────────────────────────
function showScreen(name) {
  if (!['passenger', 'driver', 'manager'].includes(name)) name = 'passenger';
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  const el = $(`screen-${name}`);
  if (el) el.classList.add('active');
  currentScreen = name;

  if (name === 'passenger' || name === 'driver') {
    requestAnimationFrame(async () => {
      await initMap(name);
      maps[name]?.resize();
      drawMap(name === 'passenger' ? 'mapSvg' : 'mapSvg2', name === 'passenger' ? 'mapStatus' : 'mapStatus2');
    });
  }

  if (!autoRefreshTimer) {
    autoRefreshTimer = setInterval(async () => {
      try { await refreshAll(); } catch (_) { /* ignore network blips */ }
    }, 4000);
  }
  refreshAll().catch(console.error);
}

function goHome() {
  window.location.href = './index.html';
}

function logout() {
  sessionStorage.removeItem('cabsystem_session');
  window.location.href = './auth.html';
}

// ── Vehicle Selection ─────────────────────────────────────
function selectVehicle(type) {
  selectedVehicle = type;
  const hiddenInput = $('selectedVehicleType');
  if (hiddenInput) hiddenInput.value = type;

  document.querySelectorAll('.vehicle-card').forEach(card => {
    card.classList.toggle('active', card.dataset.vehicle === type);
  });

  const config = VEHICLE_CONFIG[type];
  if (!config) return;

  const sharingCheck = $('wantsSharing');
  if (sharingCheck && type === 'shared') {
    sharingCheck.checked = true;
  }

  const numPersonsSelect = $('numPersons');
  if (numPersonsSelect && parseInt(numPersonsSelect.value, 10) > config.capacity) {
    numPersonsSelect.value = String(config.capacity);
  }

  // Update live preview if route is active
  onRouteEndpointsChanged();
}

// ── Worldwide Mapbox place search ─────────────────────────
function setupCityAutocomplete(searchInputId, hiddenSelectId, dropdownId, searchBtnId) {
  const input        = $(searchInputId);
  const hiddenSelect = $(hiddenSelectId);
  const dropdown     = $(dropdownId);
  const searchBtn    = $(searchBtnId);

  if (!input || !dropdown) return;

  let activeIndex = -1;
  let places = [];
  let searchTimer = null;
  let searchSequence = 0;
  let sessionToken = newSearchSessionToken();
  const placeKey = searchInputId.startsWith('from') ? 'from' : 'to';

  async function renderSuggestions(query = '') {
    const cleanQuery = query.trim();
    const sequence = ++searchSequence;
    if (cleanQuery.length < 2) {
      dropdown.innerHTML = '<div class="autocomplete-header">Type at least 2 characters to search worldwide</div>';
      dropdown.classList.add('open');
      places = [];
      return;
    }
    dropdown.innerHTML = '<div class="autocomplete-header">Searching places…</div>';
    dropdown.classList.add('open');
    try {
      const url = new URL('https://api.mapbox.com/search/searchbox/v1/suggest');
      url.search = new URLSearchParams({ q: cleanQuery, access_token: MAPBOX_TOKEN, session_token: sessionToken, limit: '6', language: 'en' });
      const response = await fetch(url);
      if (sequence !== searchSequence) return;
      const data = await response.json();
      if (!response.ok) throw new Error(data.message || data.error || `Place search failed (${response.status}). Check the token’s Search Box access and network.`);
      places = data.suggestions || [];
      if (!places.length) {
        dropdown.innerHTML = `<div class="autocomplete-header">No places found for “${escapeHtml(cleanQuery)}”</div>`;
        return;
      }
      dropdown.innerHTML = `<div class="autocomplete-header">Worldwide locations</div>` + places.map((feature, index) => {
        const title = feature.name_preferred || feature.name;
        const subtitle = feature.full_address || feature.place_formatted || '';
        return `<div class="autocomplete-item ${index === activeIndex ? 'active' : ''}" data-place-index="${index}"><div class="autocomplete-item__left"><span class="autocomplete-item__icon">📍</span><div><div class="autocomplete-item__name">${escapeHtml(title)}</div><div class="autocomplete-item__sub">${escapeHtml(subtitle)}</div></div></div></div>`;
      }).join('');
      dropdown.querySelectorAll('.autocomplete-item').forEach(item => item.addEventListener('mousedown', (event) => {
        event.preventDefault();
        choosePlace(places[Number(item.dataset.placeIndex)]);
      }));
    } catch (error) {
      if (sequence !== searchSequence) return;
      dropdown.innerHTML = `<div class="autocomplete-header">${escapeHtml(error.message)}</div>`;
    }
  }

  async function choosePlace(suggestion) {
    if (!suggestion?.mapbox_id) return;
    searchSequence += 1;
    const choiceSession = sessionToken;
    const chosenQuery = input.value;
    dropdown.innerHTML = '<div class="autocomplete-header">Loading selected location…</div>';
    dropdown.classList.add('open');
    try {
      const url = new URL(`https://api.mapbox.com/search/searchbox/v1/retrieve/${encodeURIComponent(suggestion.mapbox_id)}`);
      url.search = new URLSearchParams({ access_token: MAPBOX_TOKEN, session_token: choiceSession, language: 'en' });
      const response = await fetch(url);
      const data = await response.json();
      if (input.value !== chosenQuery) return;
      const feature = data.features?.[0];
      if (!response.ok || !feature) throw new Error(data.message || 'Could not load that location. Please choose another result.');
      const properties = feature.properties || {};
      const coordinates = properties.coordinates
        ? [properties.coordinates.longitude, properties.coordinates.latitude]
        : feature.geometry?.coordinates;
      if (!Array.isArray(coordinates) || coordinates.length < 2) throw new Error('That location has no usable map coordinates.');
      const place = { name: properties.full_address || [properties.name_preferred || properties.name, properties.place_formatted].filter(Boolean).join(', '), coordinates };
      sessionToken = newSearchSessionToken();
      selectedPlaces[placeKey] = place;
      input.value = place.name;
      if (hiddenSelect) hiddenSelect.value = place.name;
      input.dataset.selectedCityId = place.name;
      dropdown.classList.remove('open');
      onRouteEndpointsChanged();
    } catch (error) {
      dropdown.innerHTML = `<div class="autocomplete-header">${escapeHtml(error.message)}</div>`;
    }
  }

  input.addEventListener('focus', () => { if (input.value) renderSuggestions(input.value); });
  input.addEventListener('input', () => {
    activeIndex = -1;
    places = [];
    selectedPlaces[placeKey] = null;
    if (hiddenSelect) hiddenSelect.value = '';
    onRouteEndpointsChanged();
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => renderSuggestions(input.value), 300);
  });
  if (searchBtn) searchBtn.addEventListener('click', (event) => { event.preventDefault(); input.focus(); renderSuggestions(input.value); });
  input.addEventListener('keydown', (event) => {
    const items = dropdown.querySelectorAll('.autocomplete-item');
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      if (!items.length) return;
      event.preventDefault();
      activeIndex = (activeIndex + (event.key === 'ArrowDown' ? 1 : items.length - 1)) % items.length;
      items.forEach((item, index) => item.classList.toggle('active', index === activeIndex));
    } else if (event.key === 'Enter') {
      if (items.length && places.length) { event.preventDefault(); choosePlace(places[Math.max(0, activeIndex)]); }
    } else if (event.key === 'Escape') dropdown.classList.remove('open');
  });

  // Close when clicking outside
  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target) && (!searchBtn || !searchBtn.contains(e.target))) {
      dropdown.classList.remove('open');
    }
  });

  input.chooseCity = (id, name) => {
    const city = graph?.cities?.find(item => item.id === id);
    if (!city || !CITY_COORDS[city.id]) return;
    const place = { name: `${city.name}, Punjab, India`, coordinates: CITY_COORDS[city.id] };
    selectedPlaces[placeKey] = place;
    input.value = place.name;
    if (hiddenSelect) hiddenSelect.value = place.name;
    dropdown.classList.remove('open');
    onRouteEndpointsChanged();
  };
}

function quickSelectCity(fieldBaseId, cityId) {
  const searchInput  = $(`${fieldBaseId}Search`);
  const hiddenSelect = $(fieldBaseId);
  const city = graph?.cities?.find(c => c.id === cityId);
  if (!city) return;

  if (searchInput && searchInput.chooseCity) {
    searchInput.chooseCity(city.id, city.name);
  } else {
    if (searchInput) searchInput.value = `${city.name}${city.kind === 'major' ? ' ★' : ''}`;
    if (hiddenSelect) hiddenSelect.value = city.id;
    onRouteEndpointsChanged();
  }
}

// ── Interactive Map Click Handler ─────────────────────────
function onMapCityClicked(cityId, cName) {
  const fromSelect = $('fromCity');
  const toSelect   = $('toCity');
  const fromInput  = $('fromCitySearch');
  const toInput    = $('toCitySearch');

  if (!fromSelect || !toSelect) return;

  // If pickup is empty or user is setting pickup first
  if (!fromSelect.value) {
    quickSelectCity('fromCity', cityId);
  } else if (!toSelect.value && fromSelect.value !== cityId) {
    quickSelectCity('toCity', cityId);
  } else {
    // Both already set: update destination
    if (fromSelect.value === cityId) {
      quickSelectCity('fromCity', cityId);
    } else {
      quickSelectCity('toCity', cityId);
    }
  }
}

// ── Real-Time Route Preview on Map ────────────────────────
function onRouteEndpointsChanged() {
  clearTimeout(routeLookupTimer);
  const from = selectedPlaces.from;
  const to = selectedPlaces.to;
  if (!from || !to) {
    selectedRoute = null;
    const status = $('mapStatus');
    if (status) status.textContent = 'Search worldwide locations to preview a driving route.';
    drawMap('mapSvg', 'mapStatus');
    return;
  }
  if (from.coordinates[0] === to.coordinates[0] && from.coordinates[1] === to.coordinates[1]) {
    selectedRoute = null;
    const status = $('mapStatus');
    if (status) status.textContent = 'Choose two different locations.';
    drawMap('mapSvg', 'mapStatus');
    return;
  }
  selectedRoute = null;
  drawMap('mapSvg', 'mapStatus');
  const signature = JSON.stringify([from.coordinates, to.coordinates]);
  routeLookupTimer = setTimeout(async () => {
    try {
      const url = `https://api.mapbox.com/directions/v5/mapbox/driving/${from.coordinates.join(',')};${to.coordinates.join(',')}?overview=full&geometries=geojson&access_token=${encodeURIComponent(MAPBOX_TOKEN)}`;
      const response = await fetch(url);
      const data = await response.json();
      if (signature !== JSON.stringify([selectedPlaces.from?.coordinates, selectedPlaces.to?.coordinates])) return;
      if (!response.ok || !data.routes?.length) throw new Error(data.message || 'No driving route found for these locations.');
      const result = data.routes[0];
      selectedRoute = {
        path: [from.name, to.name],
        distance: Math.max(1, Math.round(result.distance / 1000)),
        geometry: result.geometry,
        fromLocation: from,
        toLocation: to,
      };
      const vCfg = VEHICLE_CONFIG[selectedVehicle] || VEHICLE_CONFIG.sedan;
      const baseFare = Math.round((55 + 20 * selectedRoute.distance) * vCfg.multiplier);
      const status = $('mapStatus');
      if (status) status.innerHTML = `<strong>Driving route:</strong> ${escapeHtml(from.name)} → ${escapeHtml(to.name)} · <strong>${selectedRoute.distance} km</strong> · ${vCfg.icon} <strong>Est. Fare: ₹${baseFare}</strong>`;
      drawMap('mapSvg', 'mapStatus');
    } catch (error) {
      selectedRoute = null;
      const status = $('mapStatus');
      if (status) status.textContent = error.message;
      drawMap('mapSvg', 'mapStatus');
    }
  }, 0);
}

async function initMap(role = currentScreen) {
  if (!['passenger', 'driver'].includes(role) || maps[role]) return maps[role];

  const config = role === 'passenger'
    ? { containerId: 'mapContainer', statusId: 'mapStatus', svgId: 'mapSvg' }
    : { containerId: 'mapContainer2', statusId: 'mapStatus2', svgId: 'mapSvg2' };
  const status = $(config.statusId);
  const container = $(config.containerId);
  if (!container) return null;
  if (!MAPBOX_TOKEN || !window.mapboxgl) {
    if (status) status.textContent = !MAPBOX_TOKEN
      ? 'Mapbox token is missing. Add a public token to web/client/app.js.'
      : 'Mapbox GL JS failed to load. Check your internet connection.';
    return null;
  }

  try {
    mapboxgl.accessToken = MAPBOX_TOKEN;
    const map = new mapboxgl.Map({
      container,
      style: 'mapbox://styles/mapbox/streets-v12',
      center: [77.2090, 28.6139],
      zoom: 7.5,
    });
    maps[role] = map;

    await new Promise((resolve, reject) => {
      map.once('load', resolve);
      map.once('error', (event) => reject(event.error || new Error('Mapbox map failed to load.')));
    });

    map.on('error', (event) => {
      console.error('Mapbox map error:', event.error || event);
      if (status) status.textContent = 'Mapbox could not load map data. Check the token, allowed URLs, and network.';
    });
    drawMap(config.svgId, config.statusId);
    return map;
  } catch (err) {
    maps[role] = null;
    console.error('Mapbox init error:', err);
    if (status) status.textContent = 'Failed to initialize Mapbox. Check the token or network.';
    return null;
  }
}

function drawMap(mapTargetId = 'mapSvg', statusId = 'mapStatus') {
  const role = mapTargetId === 'mapSvg2' || mapTargetId === 'mapContainer2' ? 'driver' : 'passenger';
  const map = maps[role];
  if (!map || !graph || !map.isStyleLoaded()) return;

  const collection = { type: 'FeatureCollection', features: selectedRoute?.geometry ? [{ type: 'Feature', properties: {}, geometry: selectedRoute.geometry }] : [] };
  if (!map.getSource('selected-route')) {
    map.addSource('selected-route', { type: 'geojson', data: collection });
    map.addLayer({ id: 'selected-route-line', type: 'line', source: 'selected-route', paint: { 'line-color': '#1677ff', 'line-width': 5 } });
  } else map.getSource('selected-route').setData(collection);
  mapMarkers[role].forEach(marker => marker.remove());
  mapMarkers[role] = [];
  const locations = [
    selectedRoute?.fromLocation || (role === 'passenger' ? selectedPlaces.from : null),
    selectedRoute?.toLocation || (role === 'passenger' ? selectedPlaces.to : null),
  ].filter(Boolean);
  locations.forEach((location, index) => {
    const marker = new mapboxgl.Marker({ color: index === 0 ? '#16a36a' : '#1677ff' })
      .setLngLat(location.coordinates).setPopup(new mapboxgl.Popup({ offset: 24 }).setText(location.name)).addTo(map);
    mapMarkers[role].push(marker);
  });
  const routeCoordinates = selectedRoute?.geometry?.coordinates?.length
    ? selectedRoute.geometry.coordinates
    : locations.map(location => location.coordinates);
  const viewSignature = JSON.stringify(routeCoordinates);
  if (routeCoordinates.length && mapViewSignatures[role] !== viewSignature) {
    const bounds = routeCoordinates.reduce((b, point) => b.extend(point), new mapboxgl.LngLatBounds(routeCoordinates[0], routeCoordinates[0]));
    map.fitBounds(bounds, { padding: 48, maxZoom: 14 });
  }
  mapViewSignatures[role] = viewSignature;
}

// ── Countdown Ticker ──────────────────────────────────────
function tickCountdowns() {
  const now = Date.now();
  document.querySelectorAll('[data-complete-at]').forEach((el) => {
    const badge = el.querySelector('.countdown-badge, .badge-active');
    if (!badge) return;
    const remaining = Math.max(0, Math.round((new Date(el.dataset.completeAt).getTime() - now) / 1000));
    if (remaining > 0) {
      badge.textContent = `⏱ ${remaining}s`;
      badge.style.background = remaining <= 10 ? 'var(--error-bg)' : '';
      badge.style.color       = remaining <= 10 ? 'var(--error)'    : '';
    } else {
      badge.textContent = 'Completing…';
    }
  });

  document.querySelectorAll('.mgr-countdown').forEach((el) => {
    const completeAt = el.dataset.completeAt;
    if (!completeAt) return;
    const remaining = Math.max(0, Math.round((new Date(completeAt).getTime() - now) / 1000));
    el.textContent = remaining > 0 ? `⏱ ${remaining}s` : 'Done';
    el.className = `badge mgr-countdown ${remaining > 0 ? 'badge-active' : 'badge-completed'}`;
  });
}

// ═══════════════════════════════════════════════════════════
//  PASSENGER WORKFLOW
// ═══════════════════════════════════════════════════════════

function renderQueues() {
  const pending = $('pendingQueue');
  const active  = $('activeQueue');
  if (!pending || !active) return;
  pending.innerHTML = '';
  active.innerHTML  = '';

  const pendingReqs = (appState?.requests ?? []).filter((r) => r.status === 'pending_driver');
  if (!pendingReqs.length) {
    pending.innerHTML = '<div class="queue-empty">No pending requests right now</div>';
  } else {
    for (const r of pendingReqs) {
      const vType = getRequestVehicle(r.id);
      const vCfg  = VEHICLE_CONFIG[vType] || VEHICLE_CONFIG.sedan;
      const el = document.createElement('div');
      el.className = 'queue-item';
      el.title = 'Click to show route on map';
      el.innerHTML = `
        <span class="queue-item__id">${r.id}</span>
        <span class="queue-item__route">
          <strong>${r.userName}</strong> · ${vCfg.icon} ${cityName(r.fromCityId)} → ${cityName(r.toCityId)}
        </span>
        ${statusBadge('pending_driver')}
      `;
      el.addEventListener('click', () => {
        selectedRoute = (selectedRoute === r.route) ? null : r.route;
        drawMap('mapSvg', 'mapStatus');
      });
      pending.appendChild(el);
    }
  }

  const activeRides = (appState?.rides ?? []).filter((r) => r.status === 'active');
  if (!activeRides.length) {
    active.innerHTML = '<div class="queue-empty">No active rides right now</div>';
  } else {
    for (const r of activeRides) {
      const vType = getRequestVehicle(r.id) || 'sedan';
      const vCfg  = VEHICLE_CONFIG[vType] || VEHICLE_CONFIG.sedan;
      const passCount = r.passengers?.length ?? 1;
      const el = document.createElement('div');
      el.className = 'queue-item';
      el.title = 'Click to show route on map';
      if (r.autoCompleteAt) el.dataset.completeAt = r.autoCompleteAt;
      el.innerHTML = `
        <span class="queue-item__id">${r.id}</span>
        <span class="queue-item__route">
          ${vCfg.icon} <strong>${r.driverName}</strong> (${vCfg.model}): ${cityName(r.fromCityId)} → ${cityName(r.toCityId)}${passCount > 1 ? ` ×${passCount}` : ''}
        </span>
        <span class="badge badge-active countdown-badge">active</span>
      `;
      el.addEventListener('click', () => {
        selectedRoute = (selectedRoute === r.route) ? null : r.route;
        drawMap('mapSvg', 'mapStatus');
      });
      active.appendChild(el);
    }
  }
}

function renderIncomingShares(userName) {
  const container = $('incomingShares');
  const section   = $('incomingShareSection');
  if (!container || !section) return;

  container.innerHTML = '';
  if (!userName) { section.style.display = 'none'; return; }

  const rides = (appState?.rides ?? []).filter((r) => r.primaryUser === userName && r.status === 'active');
  if (!rides.length) { section.style.display = 'none'; return; }

  let hasPending = false;
  for (const ride of rides) {
    const pending = (ride.shareProposals ?? []).filter((p) => p.status === 'pending');
    if (pending.length) hasPending = true;
    for (const p of pending) {
      const el = document.createElement('div');
      el.className = 'share-item';
      el.innerHTML = `
        <div class="share-item__title">🤝 ${p.fromUser} requested to share your cab!</div>
        <div class="share-item__meta">
          Pickup: ${cityName(p.pickupCityId)} · Drop: ${cityName(p.dropCityId)}<br/>
          Ride: ${ride.id} · Driver: ${ride.driverName}
        </div>
        <div class="share-item__actions">
          <button class="btn btn-success btn-sm" data-act="accept" data-ride="${ride.id}" data-proposal="${p.id}">✅ Accept &amp; Split Fare</button>
          <button class="btn btn-danger btn-sm"  data-act="reject" data-ride="${ride.id}" data-proposal="${p.id}">❌ Decline</button>
        </div>
      `;
      el.addEventListener('click', async (e) => {
        const btn = e.target.closest('button');
        if (!btn) return;
        try {
          await apiPost('/api/share/decide', {
            rideId: btn.dataset.ride,
            proposalId: btn.dataset.proposal,
            accept: btn.dataset.act === 'accept'
          });
          await refreshAll();
        } catch (err) { alert(err.message); }
      });
      container.appendChild(el);
    }
  }

  section.style.display = hasPending ? 'block' : 'none';
}

function shareCandidateCard(candidate, requestId) {
  const el = document.createElement('div');
  el.className = 'share-item';
  const canRequest = candidate.rideStatus === 'active';
  const onRoute = candidate.canUseDefaultPickupDrop
    ? '<span class="badge badge-active" style="font-size:11px">On route ✓</span>'
    : '<span class="badge badge-pending" style="font-size:11px">Custom pickup/drop</span>';
  el.innerHTML = `
    <div class="share-item__title">🚕 Ride ${candidate.rideId} · Driver ${candidate.driverName}</div>
    <div class="share-item__meta">
      Route: ${routeText(candidate.route)} (${candidate.route.distance} km)<br/>
      Status: ${statusBadge(candidate.rideStatus)} ${onRoute}
    </div>
    <div class="share-item__actions">
      <button class="btn btn-primary btn-sm" data-act="propose" ${canRequest ? '' : 'disabled'}>🤝 Request Share</button>
      <button class="btn btn-secondary btn-sm" data-act="show">🗺️ Show Route</button>
    </div>
  `;
  el.addEventListener('click', async (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;
    if (btn.dataset.act === 'show') {
      selectedRoute = candidate.route;
      drawMap('mapSvg', 'mapStatus');
      return;
    }
    const pickupCityId = $('shareFromCity').value;
    const dropCityId   = $('shareToCity').value;
    try {
      await apiPost('/api/share/propose', { requestId, rideId: candidate.rideId, pickupCityId, dropCityId });
      await refreshAll();
      alert('Share proposal sent to passenger in that cab! They will accept or decline.');
    } catch (err) { alert(err.message); }
  });
  return el;
}

async function submitRide() {
  const userName     = $('userName').value.trim();
  const fromCityId   = selectedPlaces.from?.name || '';
  const toCityId     = selectedPlaces.to?.name || '';
  const wantsSharing = $('wantsSharing').checked;
  const numPersons   = parseInt($('numPersons').value, 10) || 1;
  const vType        = selectedVehicle || 'sedan';
  const vCfg         = VEHICLE_CONFIG[vType] || VEHICLE_CONFIG.sedan;

  if (!userName) {
    alert('Please enter your full name.');
    $('userName').focus();
    return;
  }
  if (!fromCityId || !toCityId || !selectedPlaces.from || !selectedPlaces.to) {
    alert('Please select both pickup and destination from the location suggestions.');
    return;
  }
  if (!selectedRoute?.geometry) {
    alert('Please wait for the driving route to load, then try again.');
    return;
  }
  if (fromCityId === toCityId || selectedPlaces.from.coordinates.join(',') === selectedPlaces.to.coordinates.join(',')) {
    alert('Pickup and destination cannot be the same location.');
    return;
  }

  const btn = $('submitRide');
  btn.disabled = true;
  btn.textContent = '⏳ Calculating route & dispatching…';

  try {
    // ── PRESERVED API CALL ──────────────────────────────
    const res = await apiPost('/api/request', { userName, fromCityId, toCityId, wantsSharing, numPersons, route: selectedRoute, fromLocation: selectedPlaces.from, toLocation: selectedPlaces.to });
    const req = res.request;
    lastRequestId = req.id;
    selectedRoute = req.route;

    // Save vehicle type for this request
    saveRequestVehicle(req.id, vType);

    // Calculate vehicle-adjusted fare
    const calculatedFare = Math.round(req.soloFare * vCfg.multiplier);

    // Show result card
    const resultEl = $('passengerResult');
    resultEl.className = '';
    resultEl.innerHTML = `
      <div class="result-card">
        <div class="result-card__header">
          <div class="result-card__title">🎉 Ride Request Dispatched!</div>
          ${statusBadge(req.status)}
        </div>
        <div class="result-route">📍 ${routeText(req.route)}</div>
        <div class="result-pills">
          <div class="result-pill">🆔 ${req.id}</div>
          <div class="result-pill">📏 ${req.route.distance} km</div>
          <div class="result-pill"><span class="vehicle-badge-pill">${vCfg.icon} ${vCfg.name} (${vCfg.model})</span></div>
          <div class="result-pill">👥 ${req.numPersons ?? numPersons} passenger${(req.numPersons ?? numPersons) > 1 ? 's' : ''}</div>
          <div class="result-pill fare">💰 ₹${calculatedFare} (Estimated)</div>
        </div>
        <div class="muted" style="margin-top:8px">
          ${vCfg.icon} Assigned Vehicle: <strong>${vCfg.name}</strong> (${vCfg.model}) · Licence Plate: <strong>${vCfg.plate}</strong>
        </div>
        <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap">
          ${wantsSharing ? `<button class="btn btn-secondary btn-sm" onclick="showShareSection()">🤝 Find Share Rides</button>` : ''}
          <button class="btn btn-ghost btn-sm" onclick="resetPassengerForm()">← Book Another Ride</button>
        </div>
      </div>
    `;

    // Pre-fill share dropdowns
    if ($('shareFromCity')) $('shareFromCity').value = fromCityId;
    if ($('shareToCity'))   $('shareToCity').value   = toCityId;

    await refreshAll();
  } catch (err) {
    $('passengerResult').innerHTML = `
      <div class="result-card" style="background:var(--error-bg);border-color:rgba(240,68,56,0.3)">
        <div style="color:var(--error);font-weight:600">⚠️ ${err.message}</div>
      </div>
    `;
  } finally {
    btn.disabled = false;
    btn.textContent = '🚖 Confirm & Dispatch Cab';
  }
}

function showShareSection() {
  $('shareSection').classList.remove('hidden');
  $('shareSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function resetPassengerForm() {
  $('passengerResult').innerHTML = '';
  $('shareSection').classList.add('hidden');
  $('shareCandidates').innerHTML = '';
  lastRequestId = null;
  selectedPlaces.from = null;
  selectedPlaces.to = null;
  if ($('fromCity')) $('fromCity').value = '';
  if ($('toCity')) $('toCity').value = '';
  if ($('fromCitySearch')) $('fromCitySearch').value = '';
  if ($('toCitySearch')) $('toCitySearch').value = '';
  selectedRoute = null;
  drawMap('mapSvg', 'mapStatus');
}

// ═══════════════════════════════════════════════════════════
//  DRIVER WORKFLOW
// ═══════════════════════════════════════════════════════════

function renderDriverSelect() {
  const sel = $('driverSelect');
  if (!sel) return;
  const prev = sel.value;
  sel.innerHTML = '';
  for (const d of appState?.drivers ?? []) {
    const v = DRIVER_VEHICLES[d.id] || { model: 'Sedan (Dzire)' };
    const opt = document.createElement('option');
    opt.value = d.id;
    opt.textContent = `${d.name} — ${v.model} (${cityName(d.cityId)})`;
    sel.appendChild(opt);
  }
  if (prev) sel.value = prev;
}

function renderDriverView() {
  const driverId = $('driverSelect')?.value;
  const driver   = (appState?.drivers ?? []).find((d) => d.id === driverId);
  const driverV  = DRIVER_VEHICLES[driverId] || { model: 'Sedan (Dzire)', plate: 'PB-10-AB-1234', icon: '🚙' };

  // Status card
  const avatar = $('driverAvatar');
  const name   = $('driverInfoName');
  const city   = $('driverInfoCity');
  const badge  = $('driverStatusBadge');
  if (driver) {
    if (avatar) avatar.textContent = driver.name.charAt(0).toUpperCase();
    if (name)   name.textContent   = `${driver.name} · ${driverV.icon} ${driverV.model}`;
    if (city)   city.textContent   = `📍 Stationed at ${cityName(driver.cityId)} · Plate: ${driverV.plate}`;
    if (badge)  badge.innerHTML    = statusBadge(driver.status);
  } else {
    if (name) name.textContent = 'Select a driver profile';
    if (city) city.textContent = '—';
    if (badge) badge.innerHTML = '';
  }

  // Pending requests for driver
  const reqContainer = $('driverRequests');
  if (!reqContainer) return;
  reqContainer.innerHTML = '';

  const relevant = (appState?.requests ?? []).filter((r) => r.status === 'pending_driver');
  const reqCount = $('reqCount');
  if (reqCount) reqCount.textContent = `${relevant.length} pending`;

  if (!relevant.length) {
    reqContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-state__icon">📭</div>
        <div class="empty-state__text">No pending requests right now.<br/>Passenger ride requests will appear here instantly.</div>
      </div>`;
  } else {
    for (const r of relevant) {
      const reqVType = getRequestVehicle(r.id);
      const reqVCfg  = VEHICLE_CONFIG[reqVType] || VEHICLE_CONFIG.sedan;
      const el = document.createElement('div');
      el.className = 'req-item';
      el.innerHTML = `
        <div class="req-item__top">
          <div class="req-item__name">${r.userName}</div>
          <span class="vehicle-badge-pill">${reqVCfg.icon} ${reqVCfg.name}</span>
        </div>
        <div class="req-item__route">📍 ${cityName(r.fromCityId)} → 🏁 ${cityName(r.toCityId)}</div>
        <div class="req-item__meta">
          <span>📏 ${r.route?.distance ?? '?'} km</span>
          <span>👥 <strong>${r.numPersons ?? 1}</strong> passenger${(r.numPersons ?? 1) > 1 ? 's' : ''}</span>
          <span>💰 <strong>₹${Math.round(r.soloFare * reqVCfg.multiplier)}</strong></span>
          ${r.wantsSharing ? '<span>🤝 Sharing OK</span>' : ''}
        </div>
        <div class="req-item__actions">
          <button class="btn btn-success btn-sm" data-act="accept"  data-req="${r.id}">✅ Accept</button>
          <button class="btn btn-danger  btn-sm" data-act="decline" data-req="${r.id}">❌ Decline</button>
          <button class="btn btn-ghost   btn-sm" data-act="show"    data-req="${r.id}">🗺️ Show Route</button>
        </div>
      `;
      el.addEventListener('click', async (e) => {
        const btn = e.target.closest('button');
        if (!btn) return;
        const reqId = btn.dataset.req;
        if (btn.dataset.act === 'show') {
          const req = (appState?.requests ?? []).find((x) => x.id === reqId);
          selectedRoute = req?.route ?? null;
          drawMap('mapSvg2', 'mapStatus2');
          return;
        }
        const accept = btn.dataset.act === 'accept';
        if (!driverId) { alert('Please select a driver first.'); return; }
        try {
          // ── PRESERVED API CALL ──────────────────────────
          await apiPost('/api/driver/respond', { driverId, requestId: reqId, accept });
          await refreshAll();
        } catch (err) { alert(err.message); }
      });
      reqContainer.appendChild(el);
    }
  }

  // Driver notifications
  const nContainer = $('driverNotifications');
  if (!nContainer) return;
  nContainer.innerHTML = '';

  const notes = (appState?.notifications ?? [])
    .filter((n) => !driverId || n.driverId === driverId || !n.driverId)
    .slice(-15).reverse();

  if (!notes.length) {
    nContainer.innerHTML = '<div class="empty-state"><div class="empty-state__text">No notifications yet.</div></div>';
    return;
  }
  for (const n of notes) {
    const el = document.createElement('div');
    el.className = 'notif-item';
    el.innerHTML = `
      <div class="notif-item__icon">${notifIcon(n.type)}</div>
      <div>
        <div class="notif-item__msg">${n.message}</div>
        <div class="notif-item__time">${formatTime(n.at)}</div>
      </div>
    `;
    nContainer.appendChild(el);
  }
}

// ═══════════════════════════════════════════════════════════
//  MANAGER WORKFLOW
// ═══════════════════════════════════════════════════════════

function renderManagerStats() {
  const drivers   = appState?.drivers ?? [];
  const requests  = appState?.requests ?? [];
  const rides     = appState?.rides ?? [];

  const statEl = (id, val) => { const e = $(id); if (e) e.textContent = val; };
  statEl('statDrivers',   drivers.length);
  statEl('statActive',    rides.filter(r => r.status === 'active').length);
  statEl('statPending',   requests.filter(r => r.status === 'pending_driver').length);
  statEl('statCompleted', rides.filter(r => r.status === 'completed').length);

  // Driver fleet table
  const fleetBody = $('driverFleetBody');
  const fleetCount = $('fleetCount');
  if (fleetBody) {
    fleetBody.innerHTML = '';
    if (fleetCount) fleetCount.textContent = `${drivers.length} drivers`;
    for (const d of drivers) {
      const dVeh = DRIVER_VEHICLES[d.id] || { model: 'Sedan (Dzire)', plate: 'PB-10-AB-1234', icon: '🚙' };
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><strong>${d.name}</strong></td>
        <td><span class="vehicle-badge-pill">${dVeh.icon} ${dVeh.model}</span></td>
        <td>${statusBadge(d.status)}</td>
        <td>${cityName(d.cityId)}</td>
      `;
      fleetBody.appendChild(tr);
    }
    if (!drivers.length) {
      fleetBody.innerHTML = '<tr><td colspan="4" class="queue-empty">No drivers registered.</td></tr>';
    }
  }

  // Active rides table
  const activeBody  = $('activeRidesBody');
  const activeCount = $('activeRidesCount');
  const activeRides = rides.filter(r => r.status === 'active');
  if (activeBody) {
    activeBody.innerHTML = '';
    if (activeCount) activeCount.textContent = `${activeRides.length} rides`;
    const now = Date.now();
    for (const r of activeRides) {
      const vType = getRequestVehicle(r.id);
      const vCfg  = VEHICLE_CONFIG[vType] || VEHICLE_CONFIG.sedan;
      const passCount = r.passengers?.length ?? 1;
      const remaining = r.autoCompleteAt
        ? Math.max(0, Math.round((new Date(r.autoCompleteAt).getTime() - now) / 1000))
        : null;
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="mono">${r.id}</td>
        <td>${r.driverName}</td>
        <td><span class="vehicle-badge-pill">${vCfg.icon} ${vCfg.name}</span></td>
        <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${cityName(r.fromCityId)} → ${cityName(r.toCityId)}</td>
        <td>${passCount}x</td>
        <td>
          ${remaining !== null
            ? `<span class="badge mgr-countdown badge-active" data-complete-at="${r.autoCompleteAt}">⏱ ${remaining}s</span>`
            : '<span class="badge badge-active">Active</span>'}
        </td>
      `;
      activeBody.appendChild(tr);
    }
    if (!activeRides.length) {
      activeBody.innerHTML = '<tr><td colspan="6" class="queue-empty">No active rides right now.</td></tr>';
    }
  }

  // All requests table
  const allBody  = $('allRequestsBody');
  const allCount = $('allReqCount');
  const allReqs  = requests.slice().reverse();
  if (allBody) {
    allBody.innerHTML = '';
    if (allCount) allCount.textContent = `${allReqs.length} requests`;
    for (const r of allReqs) {
      const reqVType = getRequestVehicle(r.id);
      const reqVCfg  = VEHICLE_CONFIG[reqVType] || VEHICLE_CONFIG.sedan;
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="mono">${r.id}</td>
        <td>${r.userName}</td>
        <td><span class="vehicle-badge-pill">${reqVCfg.icon} ${reqVCfg.name}</span></td>
        <td>${cityName(r.fromCityId)} → ${cityName(r.toCityId)}</td>
        <td>${r.numPersons ?? 1}</td>
        <td>₹${Math.round(r.soloFare * reqVCfg.multiplier)}</td>
        <td>${statusBadge(r.status)}</td>
      `;
      allBody.appendChild(tr);
    }
    if (!allReqs.length) {
      allBody.innerHTML = '<tr><td colspan="7" class="queue-empty">No requests recorded yet.</td></tr>';
    }
  }

  // Notifications feed
  const notifFeed  = $('notifFeed');
  const notifCount = $('notifCount');
  const notifs = (appState?.notifications ?? []).slice(-20).reverse();
  if (notifFeed) {
    notifFeed.innerHTML = '';
    if (notifCount) notifCount.textContent = `${notifs.length} events`;
    if (!notifs.length) {
      notifFeed.innerHTML = '<div class="empty-state"><div class="empty-state__text">No activity yet.</div></div>';
    } else {
      for (const n of notifs) {
        const el = document.createElement('div');
        el.className = 'notif-item';
        el.innerHTML = `
          <div class="notif-item__icon">${notifIcon(n.type)}</div>
          <div>
            <div class="notif-item__msg">${n.message}</div>
            <div class="notif-item__time">${formatTime(n.at)}</div>
          </div>
        `;
        notifFeed.appendChild(el);
      }
    }
  }

  const mt = $('managerTime');
  if (mt && appState?.serverTime) mt.textContent = `Server: ${formatTime(appState.serverTime)}`;
}

async function confirmReset() {
  if (!confirm('⚠️ Reset demo state?\n\nThis will clear all rides, pending requests, and notifications. All drivers will return to idle.')) return;
  try {
    // ── PRESERVED API CALL ──────────────────────────────
    await apiPost('/api/reset', {});
    lastRequestId = null;
    selectedRoute = null;
    await refreshAll();
  } catch (err) { alert(err.message); }
}

// ═══════════════════════════════════════════════════════════
//  SHARED REFRESH
// ═══════════════════════════════════════════════════════════

function setOptions(select, cities, includeBlank = false) {
  if (!select || !cities) return;
  const current = select.value;
  // If already populated with options, preserve selection
  if (select.children.length > 0) {
    if (current) select.value = current;
    return;
  }
  select.innerHTML = '';
  if (includeBlank) {
    const emptyOpt = document.createElement('option');
    emptyOpt.value = '';
    emptyOpt.textContent = '-- Select City --';
    select.appendChild(emptyOpt);
  }
  for (const c of cities) {
    const opt = document.createElement('option');
    opt.value = c.id;
    opt.textContent = `${c.name}${c.kind === 'major' ? ' ★' : ''}`;
    select.appendChild(opt);
  }
  if (current) {
    select.value = current;
  }
}

async function refreshAll() {
  // ── PRESERVED API CALLS ──────────────────────────────
  graph    = await apiGet('/api/graph');
  appState = await apiGet('/api/state');

  // Update server time
  const st = $('serverTime');
  if (st && appState?.serverTime) st.textContent = `Server: ${formatTime(appState.serverTime)}`;

  // Populate city selects
  if (graph?.cities) {
    setOptions($('fromCity'),      graph.cities, true);
    setOptions($('toCity'),        graph.cities, true);
    setOptions($('shareFromCity'), graph.cities, false);
    setOptions($('shareToCity'),   graph.cities, false);
    for (const [id, place] of [['fromCity', selectedPlaces.from], ['toCity', selectedPlaces.to]]) {
      const select = $(id);
      if (!select || !place) continue;
      if (!Array.from(select.options).some(option => option.value === place.name)) select.add(new Option(place.name, place.name));
      select.value = place.name;
    }
    if (lastRequestId && selectedPlaces.from && selectedPlaces.to) {
      for (const [id, place] of [['shareFromCity', selectedPlaces.from], ['shareToCity', selectedPlaces.to]]) {
        const select = $(id);
        if (select && !Array.from(select.options).some(option => option.value === place.name)) {
          select.add(new Option(place.name, place.name));
        }
      }
      $('shareFromCity').value = selectedPlaces.from.name;
      $('shareToCity').value = selectedPlaces.to.name;
    }

  }

  // Screen-specific renders
  if (currentScreen === 'passenger') {
    renderQueues();
    drawMap('mapSvg', 'mapStatus');
    renderIncomingShares($('userName')?.value?.trim());
  }
  if (currentScreen === 'driver') {
    renderDriverSelect();
    renderDriverView();
    drawMap('mapSvg2', 'mapStatus2');
  }
  if (currentScreen === 'manager') {
    renderManagerStats();
  }
}

// ═══════════════════════════════════════════════════════════
//  WIRE EVENTS & AUTH RESTORATION
// ═══════════════════════════════════════════════════════════

function wireEvents() {
  // Setup city autocomplete
  setupCityAutocomplete('fromCitySearch', 'fromCity', 'fromCityDropdown', 'fromCitySearchBtn');
  setupCityAutocomplete('toCitySearch', 'toCity', 'toCityDropdown', 'toCitySearchBtn');

  // Submit ride button
  $('submitRide')?.addEventListener('click', submitRide);

  // Swap cities button
  $('swapBtn')?.addEventListener('click', () => {
    const fromInput = $('fromCitySearch');
    const toInput   = $('toCitySearch');
    const fromSelect = $('fromCity');
    const toSelect = $('toCity');
    if (!fromSelect || !toSelect) return;

    const previousCity = fromSelect.value;
    fromSelect.value = toSelect.value;
    toSelect.value = previousCity;
    [selectedPlaces.from, selectedPlaces.to] = [selectedPlaces.to, selectedPlaces.from];
    if (fromInput && toInput) {
      const previousText = fromInput.value;
      fromInput.value = toInput.value;
      toInput.value = previousText;
    }
    onRouteEndpointsChanged();
  });

  // Find share candidates
  $('findShareBtn')?.addEventListener('click', async () => {
    const container = $('shareCandidates');
    container.innerHTML = '';
    if (!lastRequestId) {
      container.innerHTML = '<div class="empty-state"><div class="empty-state__text">Submit a ride request with sharing enabled first.</div></div>';
      return;
    }
    if ($('shareFromCity').value === $('shareToCity').value) {
      container.innerHTML = '<div class="muted" style="padding:8px">Share pickup and drop cannot be the same city.</div>';
      return;
    }
    try {
      // ── PRESERVED API CALL ──────────────────────────
      const res = await apiGet(`/api/share/candidates?requestId=${encodeURIComponent(lastRequestId)}`);
      if (!res.candidates.length) {
        const hint = res.hint || 'No matching rides found on your route right now.';
        container.innerHTML = `<div class="empty-state"><div class="empty-state__icon">🔍</div><div class="empty-state__text">${hint}</div></div>`;
        return;
      }
      for (const c of res.candidates) {
        container.appendChild(shareCandidateCard(c, lastRequestId));
      }
    } catch (err) {
      container.innerHTML = `<div class="muted" style="padding:8px">Error: ${err.message}</div>`;
    }
  });

  // Passenger name change
  $('userName')?.addEventListener('input', () => {
    renderIncomingShares($('userName').value.trim());
  });

  // Driver select change
  $('driverSelect')?.addEventListener('change', renderDriverView);
}

// ── Check Auth & URL Role ─────────────────────────────────
function checkSessionAndRole() {
  const params = new URLSearchParams(window.location.search);
  const urlRole = params.get('role');

  let session = null;
  try {
    session = JSON.parse(sessionStorage.getItem('cabsystem_session') || 'null');
  } catch (_) {}

  const role = urlRole || session?.role || 'passenger';

  // Apply user info to labels if available
  if (session?.name) {
    const userField = $('userName');
    if (userField && !userField.value) userField.value = session.name;

    const passLabel = $('passengerNameLabel');
    if (passLabel) passLabel.textContent = session.name;

    const passAv = $('passengerAvatar');
    if (passAv) passAv.textContent = session.name.charAt(0).toUpperCase();

    const dLabel = $('driverNameLabel');
    if (dLabel && role === 'driver') {
      dLabel.textContent = session.driverId ? `${session.name} · ${session.driverId}` : session.name;
    }

    const mLabel = $('managerNameLabel');
    if (mLabel && role === 'manager') {
      mLabel.textContent = session.managerId ? `${session.name} · ${session.managerId}` : session.name;
    }

    if (role === 'driver' && session.driverId) {
      const driverSel = $('driverSelect');
      if (driverSel) {
        if (session.driverId === 'DRV-101') driverSel.value = 'd1';
        else if (session.driverId === 'DRV-102') driverSel.value = 'd3';
        else if (session.driverId === 'DRV-103') driverSel.value = 'd4';
      }
    }
  }

  showScreen(role);
}

// ═══════════════════════════════════════════════════════════
//  MAIN
// ═══════════════════════════════════════════════════════════

async function main() {
  wireEvents();
  await refreshAll();
  checkSessionAndRole();
  await initMap(currentScreen);
  await refreshAll();

  // Set default vehicle or URL vehicle
  const params = new URLSearchParams(window.location.search);
  const urlVehicle = params.get('vehicle');
  if (urlVehicle && VEHICLE_CONFIG[urlVehicle]) {
    selectVehicle(urlVehicle);
  } else {
    selectVehicle('sedan');
  }

  // Countdown ticker every 1s
  setInterval(tickCountdowns, 1000);

  // Expose functions for inline HTML events
  window.showScreen         = showScreen;
  window.goHome             = goHome;
  window.logout             = logout;
  window.refreshAll         = refreshAll;
  window.confirmReset       = confirmReset;
  window.showShareSection   = showShareSection;
  window.resetPassengerForm = resetPassengerForm;
  window.selectVehicle      = selectVehicle;
  window.quickSelectCity    = quickSelectCity;
  window.renderDriverView   = renderDriverView;
  window.onMapCityClicked   = onMapCityClicked;
}

main().catch((e) => {
  console.error(e);
});
