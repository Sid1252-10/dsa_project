import { punjabGraph } from "./punjabGraph.js";

function nowIso() {
  return new Date().toISOString();
}

function edgeKey(a, b) {
  return a < b ? `${a}::${b}` : `${b}::${a}`;
}

function buildAdjacency(graph) {
  const byId = new Map(graph.cities.map((c) => [c.id, c]));
  const adj = new Map(graph.cities.map((c) => [c.id, []]));
  const weights = new Map();

  for (const road of graph.roads) {
    const [a, b, kmDist] = road;
    if (!byId.has(a) || !byId.has(b)) continue;
    // Use real km distance from graph; fall back to pixel estimate if missing
    let w;
    if (typeof kmDist === "number" && kmDist > 0) {
      w = kmDist;
    } else {
      const ca = byId.get(a), cb = byId.get(b);
      const dx = ca.x - cb.x, dy = ca.y - cb.y;
      w = Math.max(1, Math.round(Math.sqrt(dx * dx + dy * dy) / 20));
    }
    adj.get(a).push({ to: b, w });
    adj.get(b).push({ to: a, w });
    weights.set(edgeKey(a, b), w);
  }

  return { byId, adj, weights };
}

const { byId: cityById, adj } = buildAdjacency(punjabGraph);

export function shortestPath(fromId, toId) {
  if (!cityById.has(fromId) || !cityById.has(toId)) {
    return { path: [], distance: Infinity };
  }
  if (fromId === toId) return { path: [fromId], distance: 0 };

  const dist = new Map();
  const prev = new Map();
  const visited = new Set();
  for (const id of cityById.keys()) dist.set(id, Infinity);
  dist.set(fromId, 0);

  while (visited.size < cityById.size) {
    let u = null;
    let best = Infinity;
    for (const [id, d] of dist.entries()) {
      if (visited.has(id)) continue;
      if (d < best) {
        best = d;
        u = id;
      }
    }
    if (u === null) break;
    if (u === toId) break;
    visited.add(u);

    for (const { to, w } of adj.get(u) ?? []) {
      if (visited.has(to)) continue;
      const alt = dist.get(u) + w;
      if (alt < dist.get(to)) {
        dist.set(to, alt);
        prev.set(to, u);
      }
    }
  }

  const d = dist.get(toId);
  if (!Number.isFinite(d) || d === Infinity) return { path: [], distance: Infinity };

  const path = [];
  let cur = toId;
  while (cur) {
    path.push(cur);
    cur = prev.get(cur);
    if (cur === fromId) {
      path.push(fromId);
      break;
    }
  }
  path.reverse();
  return { path, distance: d };
}

export function computeSoloFare(distance, numPersons = 1) {
  // Base ₹55 + ₹20/km — raised ~32% from original rates
  const base = 55;
  const perKm = 20;
  const persons = Math.max(1, Math.min(6, Math.round(numPersons)));
  // Each extra person adds 60% of the per-km rate (shared cab, not full extra)
  const personMultiplier = 1 + (persons - 1) * 0.6;
  return Math.round((base + perKm * distance) * personMultiplier);
}

export function computeSharedPricing(soloFare, riders) {
  // Requirement: each rider pays less than solo, but total > solo.
  // We do this by: total = solo * 1.30, split equally.
  const total = Math.round(soloFare * 1.3);
  const each = Math.round(total / riders);
  return { each, total };
}

let nextId = 1;
function id(prefix) {
  nextId += 1;
  return `${prefix}_${nextId}`;
}

export const state = {
  graph: punjabGraph,
  drivers: [
    { id: "d1", name: "Ravi", cityId: "amritsar", status: "idle" },
    { id: "d2", name: "Priya", cityId: "ludhiana", status: "idle" },
    { id: "d3", name: "Arjun", cityId: "bathinda", status: "idle" },
    { id: "d4", name: "Simran", cityId: "jalandhar", status: "idle" }
  ],
  requests: [],
  rides: [],
  notifications: []
};

export function snapshot() {
  return {
    serverTime: nowIso(),
    drivers: state.drivers,
    requests: state.requests,
    rides: state.rides,
    notifications: state.notifications.slice(-50)
  };
}

export function createRideRequest({ userName, fromCityId, toCityId, wantsSharing, numPersons }) {
  if (fromCityId === toCityId) {
    return { ok: false, error: "From and To cannot be the same city." };
  }
  const route = shortestPath(fromCityId, toCityId);
  if (!route.path.length) {
    return { ok: false, error: "No route found between selected cities." };
  }

  const persons = Math.max(1, Math.min(6, Math.round(Number(numPersons) || 1)));

  const request = {
    id: id("req"),
    userName,
    fromCityId,
    toCityId,
    wantsSharing: !!wantsSharing,
    numPersons: persons,
    status: "pending_driver", // pending_driver | accepted | declined | cancelled
    createdAt: nowIso(),
    route,
    soloFare: computeSoloFare(route.distance, persons),
    assignedDriverId: null,
    rideId: null
  };

  state.requests.push(request);
  state.notifications.push({
    id: id("n"),
    type: "request_created",
    at: nowIso(),
    message: `New request by ${userName} (${persons} person${persons > 1 ? "s" : ""}): ${fromCityId} → ${toCityId}`,
    requestId: request.id,
    driverId: request.assignedDriverId
  });

  return { ok: true, request };
}

export function driverRespond({ driverId, requestId, accept }) {
  const req = state.requests.find((r) => r.id === requestId);
  const driver = state.drivers.find((d) => d.id === driverId);
  if (!req) return { ok: false, error: "Request not found." };
  if (!driver) return { ok: false, error: "Driver not found." };
  if (req.status !== "pending_driver") return { ok: false, error: "Request is not pending." };
  if (req.assignedDriverId && req.assignedDriverId !== driverId) {
    return { ok: false, error: "This request is assigned to a different driver." };
  }
  if (driver.status !== "idle") return { ok: false, error: "Driver is not idle." };

  if (!accept) {
    req.status = "declined";
    state.notifications.push({
      id: id("n"),
      type: "request_declined",
      at: nowIso(),
      message: `Driver ${driver.name} declined request ${req.id}.`,
      requestId: req.id,
      driverId
    });
    return { ok: true, request: req };
  }

  const ride = {
    id: id("ride"),
    driverId,
    driverName: driver.name,
    primaryUser: req.userName,
    passengers: [
      {
        userName: req.userName,
        pickupCityId: req.fromCityId,
        dropCityId: req.toCityId,
        pricing: { mode: "solo", soloFare: req.soloFare, pay: req.soloFare }
      }
    ],
    fromCityId: req.fromCityId,
    toCityId: req.toCityId,
    route: req.route,
    status: "active", // active | completed
    shareProposals: [] // proposals from other users to join
  };

  req.status = "accepted";
  req.rideId = ride.id;
  req.assignedDriverId = driverId;
  driver.status = "on_ride";
  // Keep driver at pickup location while ride is active.
  // (We don't simulate time/progress yet, so moving to destination here
  // would incorrectly make mid-route pickups impossible.)
  driver.cityId = req.fromCityId;

  state.rides.push(ride);
  state.notifications.push({
    id: id("n"),
    type: "ride_started",
    at: nowIso(),
    message: `Driver ${driver.name} accepted ${req.userName}'s ride.`,
    requestId: req.id,
    rideId: ride.id,
    driverId
  });
  return { ok: true, request: req, ride };
}

function sameDirectionRouteScore(aRoute, bRoute) {
  // Count total consecutive edges shared in the same direction.
  // A score >= 1 means at least one shared edge (2 consecutive nodes).
  const a = aRoute.path;
  const b = bRoute.path;
  let sharedEdges = 0;
  const bEdges = new Set();
  for (let j = 0; j < b.length - 1; j++) {
    bEdges.add(`${b[j]}::${b[j + 1]}`);
  }
  for (let i = 0; i < a.length - 1; i++) {
    if (bEdges.has(`${a[i]}::${a[i + 1]}`)) sharedEdges++;
  }
  return sharedEdges;
}

function indexOnRoute(route, cityId) {
  if (!route?.path?.length) return -1;
  return route.path.indexOf(cityId);
}

function pickupDropAvailableOnRide(ride, pickupCityId, dropCityId) {
  const p = indexOnRoute(ride.route, pickupCityId);
  const d = indexOnRoute(ride.route, dropCityId);
  if (p === -1 || d === -1) return { ok: false, reason: "Pickup/drop not on this trip route." };
  if (p > d) return { ok: false, reason: "Drop must come after pickup on the route." };
  return { ok: true };
}

export function listShareCandidates(requestId) {
  const req = state.requests.find((r) => r.id === requestId);
  if (!req) return { ok: false, error: "Request not found." };
  if (!req.wantsSharing) return { ok: false, error: "Request not marked for sharing." };
  // Block only if the request is definitively done
  if (req.status === "cancelled" || req.status === "declined") {
    return { ok: false, error: "This request is cancelled or declined — not eligible for sharing." };
  }
  // Request already has a driver and is in an active ride — sharing search is no longer relevant
  if (req.rideId) {
    return {
      ok: true,
      candidates: [],
      hint: "Your ride is already active. Check the 'Incoming share requests' section below — other riders can still propose to join your cab."
    };
  }

  // Only active rides can actually accept new passengers
  const activeRides = state.rides.filter((r) => r.status === "active");

  if (!activeRides.length) {
    return { ok: true, candidates: [], hint: "No active rides right now. A driver must accept a ride first before you can share into it." };
  }

  const candidates = activeRides
    .map((ride) => {
      const score = sameDirectionRouteScore(req.route, ride.route);
      const availability = pickupDropAvailableOnRide(ride, req.fromCityId, req.toCityId);
      return {
        rideId: ride.id,
        driverName: ride.driverName,
        driverId: ride.driverId,
        rideStatus: ride.status,
        score,
        route: ride.route,
        canUseDefaultPickupDrop: availability.ok
      };
    })
    .filter((c) => c.score >= 1)  // at least 1 shared edge (was 2 consecutive nodes, now 1 shared edge)
    .sort((a, b) => b.score - a.score);  // best matches first

  return { ok: true, candidates };
}

export function proposeShare({ requestId, rideId, pickupCityId, dropCityId }) {
  const req = state.requests.find((r) => r.id === requestId);
  const ride = state.rides.find((r) => r.id === rideId);
  if (!req) return { ok: false, error: "Request not found." };
  if (!ride) return { ok: false, error: "Ride not found." };
  if (req.status !== "pending_driver") return { ok: false, error: "Request is not pending." };
  if (!req.wantsSharing) return { ok: false, error: "Request not marked for sharing." };
  if (req.rideId) return { ok: false, error: "This request is already in a ride." };
  if (ride.status !== "active") return { ok: false, error: "You can only share into an active ride." };

  // Prevent duplicate proposals from the same request to the same ride
  const existing = ride.shareProposals.find((p) => p.requestId === requestId);
  if (existing) {
    if (existing.status === "pending") {
      return { ok: false, error: "You already have a pending share request on this ride. Wait for the rider to respond." };
    }
    if (existing.status === "accepted") {
      return { ok: false, error: "Your share request was already accepted for this ride." };
    }
    // rejected — allow re-proposing (rider might change their mind)
  }

  const availability = pickupDropAvailableOnRide(ride, pickupCityId, dropCityId);
  if (!availability.ok) return { ok: false, error: availability.reason };

  const proposal = {
    id: id("share"),
    fromUser: req.userName,
    requestId: req.id,
    pickupCityId,
    dropCityId,
    status: "pending", // pending | accepted | rejected
    createdAt: nowIso()
  };
  ride.shareProposals.push(proposal);

  state.notifications.push({
    id: id("n"),
    type: "share_proposed",
    at: nowIso(),
    message: `${req.userName} requested to share ride ${ride.id} (driver ${ride.driverName}).`,
    rideId: ride.id,
    requestId: req.id,
    toUser: ride.primaryUser
  });

  return { ok: true, proposal };
}

export function decideShare({ rideId, proposalId, accept }) {
  const ride = state.rides.find((r) => r.id === rideId);
  if (!ride) return { ok: false, error: "Ride not found." };
  if (ride.status !== "active") return { ok: false, error: "Ride has already completed — share request expired." };
  const proposal = ride.shareProposals.find((p) => p.id === proposalId);
  if (!proposal) return { ok: false, error: "Proposal not found." };
  if (proposal.status !== "pending") return { ok: false, error: `Proposal already ${proposal.status}.` };

  if (!accept) {
    proposal.status = "rejected";
    state.notifications.push({
      id: id("n"),
      type: "share_rejected",
      at: nowIso(),
      message: `${ride.primaryUser} rejected share request from ${proposal.fromUser}.`,
      rideId,
      requestId: proposal.requestId
    });
    return { ok: true, ride };
  }

  // Accept: convert ride to shared pricing for 2 riders.
  proposal.status = "accepted";
  const primary = ride.passengers[0];
  const soloFare = primary.pricing.soloFare ?? computeSoloFare(ride.route.distance);
  const pricing = computeSharedPricing(soloFare, 2);

  primary.pricing = { mode: "shared", soloFare, pay: pricing.each };
  ride.passengers.push({
    userName: proposal.fromUser,
    pickupCityId: proposal.pickupCityId,
    dropCityId: proposal.dropCityId,
    pricing: { mode: "shared", soloFare, pay: pricing.each }
  });

  const req = state.requests.find((r) => r.id === proposal.requestId);
  if (req) {
    req.status = "accepted";
    req.assignedDriverId = ride.driverId;
    req.rideId = ride.id;
  }

  state.notifications.push({
    id: id("n"),
    type: "share_accepted",
    at: nowIso(),
    message: `${ride.primaryUser} accepted sharing with ${proposal.fromUser}. Driver notified for pickup/drop.`,
    rideId,
    requestId: proposal.requestId,
    driverId: ride.driverId
  });

  return { ok: true, ride, pricing };
}

const initialDrivers = [
  { id: "d1", name: "Ravi",    cityId: "amritsar",  status: "idle" },
  { id: "d2", name: "Priya",   cityId: "ludhiana",  status: "idle" },
  { id: "d3", name: "Arjun",   cityId: "bathinda",  status: "idle" },
  { id: "d4", name: "Simran",  cityId: "jalandhar", status: "idle" }
];

// ── Auto-complete rides after 45–60 s ────────────────────────────────────────
export function completeRide(rideId) {
  const ride = state.rides.find((r) => r.id === rideId);
  if (!ride || ride.status !== "active") return { ok: false, error: "Ride not active." };

  ride.status = "completed";
  ride.completedAt = nowIso();

  // Expire all pending share proposals — ride is over, can't join anymore
  for (const proposal of ride.shareProposals) {
    if (proposal.status === "pending") {
      proposal.status = "expired";
      state.notifications.push({
        id: id("n"),
        type: "share_expired",
        at: nowIso(),
        message: `Share request from ${proposal.fromUser} expired — ride ${ride.id} has completed.`,
        rideId: ride.id,
        requestId: proposal.requestId
      });
    }
  }

  // Free the driver
  const driver = state.drivers.find((d) => d.id === ride.driverId);
  if (driver) {
    driver.status = "idle";
    driver.cityId = ride.toCityId;
  }

  // Mark all passenger requests as completed
  for (const p of ride.passengers) {
    const req = state.requests.find((r) => r.rideId === ride.id && r.userName === p.userName);
    if (req) req.status = "completed";
  }

  state.notifications.push({
    id: id("n"),
    type: "ride_completed",
    at: nowIso(),
    message: `Ride ${ride.id} completed. Driver ${driver?.name ?? ride.driverId} is now idle at ${ride.toCityId}.`,
    rideId: ride.id,
    driverId: ride.driverId
  });

  return { ok: true, ride };
}

// Check every 5 s; complete rides that have been active for 45–60 s
setInterval(() => {
  const now = Date.now();
  for (const ride of state.rides) {
    if (ride.status !== "active") continue;
    const req = state.requests.find((r) => r.rideId === ride.id);
    if (!req) continue;
    const age = now - new Date(req.createdAt).getTime();
    // Random completion window: 45–60 s (assigned once per ride)
    if (!ride._autoCompleteMs) {
      ride._autoCompleteMs = 45000 + Math.random() * 15000;
      ride.autoCompleteAt  = new Date(new Date(req.createdAt).getTime() + ride._autoCompleteMs).toISOString();
    }
    if (age >= ride._autoCompleteMs) completeRide(ride.id);
  }
}, 5000);

export function resetDemoState() {
  state.drivers = initialDrivers.map((d) => ({ ...d }));
  state.requests = [];
  state.rides = [];
  state.notifications = [];
  nextId = 1;
  state.notifications.push({
    id: id("n"),
    type: "state_reset",
    at: nowIso(),
    message: "State reset to demo defaults."
  });
  return snapshot();
}
