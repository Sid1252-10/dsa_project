"""
server.py
---------
Python backend server for the Yarivo ride booking and sharing web app.
Serves static files from web/client and implements all /api endpoints.
Uses Python's standard library (http.server) — no external packages required.
"""

from datetime import datetime, timezone
import json
import math
import os
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ─────────────────────────────────────────────
#  Punjab Graph
# ─────────────────────────────────────────────

PUNJAB_GRAPH = {
    "cities": [
        {"id": "amritsar", "name": "Amritsar", "x": 120, "y": 120, "kind": "major"},
        {"id": "tarn_taran", "name": "Tarn Taran", "x": 135, "y": 150, "kind": "minor"},
        {"id": "gurdaspur", "name": "Gurdaspur", "x": 175, "y": 95, "kind": "minor"},
        {"id": "pathankot", "name": "Pathankot", "x": 235, "y": 75, "kind": "major"},
        {"id": "hoshiarpur", "name": "Hoshiarpur", "x": 260, "y": 150, "kind": "minor"},
        {"id": "kapurthala", "name": "Kapurthala", "x": 210, "y": 200, "kind": "minor"},
        {"id": "jalandhar", "name": "Jalandhar", "x": 260, "y": 220, "kind": "major"},
        {"id": "ludhiana", "name": "Ludhiana", "x": 340, "y": 260, "kind": "major"},
        {"id": "moga", "name": "Moga", "x": 290, "y": 320, "kind": "minor"},
        {"id": "firozpur", "name": "Firozpur", "x": 205, "y": 360, "kind": "minor"},
        {"id": "fazilka", "name": "Fazilka", "x": 130, "y": 430, "kind": "minor"},
        {"id": "abohar", "name": "Abohar", "x": 175, "y": 460, "kind": "minor"},
        {"id": "bathinda", "name": "Bathinda", "x": 300, "y": 430, "kind": "major"},
        {"id": "faridkot", "name": "Faridkot", "x": 255, "y": 395, "kind": "minor"},
        {"id": "muktsar", "name": "Sri Muktsar Sahib", "x": 235, "y": 450, "kind": "minor"},
        {"id": "mansa", "name": "Mansa", "x": 360, "y": 455, "kind": "minor"},
        {"id": "barnala", "name": "Barnala", "x": 385, "y": 380, "kind": "minor"},
        {"id": "sangrur", "name": "Sangrur", "x": 430, "y": 360, "kind": "minor"},
        {"id": "patiala", "name": "Patiala", "x": 500, "y": 350, "kind": "major"},
        {"id": "malerkotla", "name": "Malerkotla", "x": 450, "y": 320, "kind": "minor"},
        {"id": "rupnagar", "name": "Rupnagar", "x": 455, "y": 230, "kind": "minor"},
        {"id": "mohali", "name": "Mohali", "x": 520, "y": 260, "kind": "major"},
        {"id": "chandigarh", "name": "Chandigarh", "x": 560, "y": 240, "kind": "major"},
    ],
    "roads": [
        ["amritsar", "tarn_taran"],
        ["amritsar", "gurdaspur"],
        ["gurdaspur", "pathankot"],
        ["pathankot", "hoshiarpur"],
        ["hoshiarpur", "jalandhar"],
        ["tarn_taran", "kapurthala"],
        ["kapurthala", "jalandhar"],
        ["amritsar", "kapurthala"],
        ["jalandhar", "ludhiana"],
        ["ludhiana", "rupnagar"],
        ["rupnagar", "mohali"],
        ["mohali", "chandigarh"],
        ["rupnagar", "chandigarh"],
        ["ludhiana", "malerkotla"],
        ["malerkotla", "sangrur"],
        ["malerkotla", "patiala"],
        ["sangrur", "patiala"],
        ["ludhiana", "moga"],
        ["moga", "firozpur"],
        ["firozpur", "fazilka"],
        ["fazilka", "abohar"],
        ["abohar", "muktsar"],
        ["muktsar", "bathinda"],
        ["faridkot", "bathinda"],
        ["faridkot", "moga"],
        ["faridkot", "muktsar"],
        ["bathinda", "barnala"],
        ["barnala", "sangrur"],
        ["barnala", "mansa"],
        ["mansa", "bathinda"],
        ["patiala", "mohali"],
        ["ludhiana", "patiala"],
    ],
}

# ─────────────────────────────────────────────
#  Graph Utilities & Routing
# ─────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalized_words(value):
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in str(value or "")).split())


def _city_center_for_name(value):
    normalized = _normalized_words(value)
    if not normalized:
        return None
    for city_id, coordinates in CITY_CENTERS.items():
        city_name = _normalized_words(CITY_BY_ID[city_id]["name"])
        aliases = {city_id.replace("_", " "), city_name}
        aliases.update(alias for alias, target in CITY_CENTER_ALIASES.items() if target == city_id)
        if any(normalized == alias or normalized.startswith(alias + " ") for alias in aliases):
            return coordinates
    return None


def _valid_coordinates(value):
    if isinstance(value, dict):
        if "coordinates" in value:
            return _valid_coordinates(value.get("coordinates"))
        lon, lat = value.get("longitude"), value.get("latitude")
    elif isinstance(value, (list, tuple)) and len(value) >= 2:
        lon, lat = value[0], value[1]
    else:
        return None
    try:
        lon, lat = float(lon), float(lat)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(lon) or not math.isfinite(lat) or not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
        return None
    return (lon, lat)


def _pickup_coordinates(from_location, from_city_id):
    feature_type = ""
    coordinates = None
    if isinstance(from_location, dict):
        feature_type = str(from_location.get("featureType") or from_location.get("feature_type") or "").lower()
        coordinates = _valid_coordinates(from_location)
    city_center = _city_center_for_name(from_city_id)
    if not city_center and isinstance(from_location, dict):
        city_center = _city_center_for_name(from_location.get("name"))
    if city_center and feature_type in {"place", "locality", "city"}:
        return city_center
    return coordinates or city_center


def _haversine_km(a, b):
    lon1, lat1 = map(math.radians, a)
    lon2, lat2 = map(math.radians, b)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.atan2(math.sqrt(h), math.sqrt(max(0.0, 1 - h)))


def _route_distance_meters(route):
    coordinates = (((route or {}).get("geometry") or {}).get("coordinates") or [])
    points = [_valid_coordinates(point) for point in coordinates]
    points = [point for point in points if point]
    if len(points) >= 2:
        return sum(_haversine_km(a, b) for a, b in zip(points, points[1:])) * 1000
    try:
        return max(0.0, float((route or {}).get("distance", 0)) * 1000)
    except (TypeError, ValueError):
        return 0.0


def _advance_ride_completions(now=None):
    now = time.time() if now is None else now
    for ride in state["rides"]:
        if ride.get("status") != "active" or not ride.get("autoCompleteAtEpoch") or now < ride["autoCompleteAtEpoch"]:
            continue
        ride["status"] = "completed"
        ride["completedAt"] = _now_iso()
        driver = next((item for item in state["drivers"] if item["id"] == ride.get("driverId")), None)
        if driver:
            driver["status"] = "idle"
            driver["cityId"] = ride.get("toCityId") or driver.get("cityId")
            destination = (ride.get("route") or {}).get("toLocation")
            driver["coordinates"] = _valid_coordinates(destination) or _city_center_for_name(driver["cityId"])
        for request in state["requests"]:
            if request.get("rideId") == ride.get("id"):
                request["status"] = "completed"
        state["notifications"].append({
            "id": make_id("n"), "type": "ride_completed", "at": ride["completedAt"],
            "message": f"Ride {ride['id']} reached its destination and is complete.",
            "requestId": ride.get("requestId"), "rideId": ride["id"], "driverId": ride.get("driverId"),
        })


def _driver_coordinates(driver):
    return _valid_coordinates(driver.get("coordinates")) or _city_center_for_name(driver.get("cityId"))


def _notify_driver_offer(req, driver):
    state["notifications"].append({
        "id": make_id("n"),
        "type": "request_offered",
        "at": _now_iso(),
        "message": f"Ride request {req['id']} is now available to {driver['name']}.",
        "requestId": req["id"],
        "driverId": driver["id"],
    })


def _offer_next_driver(req, now=None):
    now = time.time() if now is None else now
    drivers_by_id = {driver["id"]: driver for driver in state["drivers"]}
    offered = set(req.get("offeredDriverIds", []))
    declined = set(req.get("declinedDriverIds", []))
    order = req.get("dispatchDriverOrder", [])
    cursor = int(req.get("dispatchCursor", 0))

    while cursor < len(order):
        driver_id = order[cursor]
        cursor += 1
        driver = drivers_by_id.get(driver_id)
        if (not driver or driver.get("status") != "idle"
                or driver.get("vehicleType") != req.get("vehicleType")
                or driver_id in offered or driver_id in declined):
            continue
        req["dispatchCursor"] = cursor
        req.setdefault("offeredDriverIds", []).append(driver_id)
        req["dispatchCurrentDriverId"] = driver_id
        req["dispatchDeadline"] = now + DISPATCH_OFFER_SECONDS
        req["dispatchState"] = "offering"
        req["dispatchOfferRound"] = len(req["offeredDriverIds"])
        _notify_driver_offer(req, driver)
        return driver

    req["dispatchCursor"] = 0
    req["dispatchCurrentDriverId"] = None
    req["dispatchDeadline"] = None
    req["dispatchState"] = "awaiting_response" if req.get("offeredDriverIds") else "waiting_for_driver"
    return None


def _advance_request_dispatch(req, now=None):
    if req.get("status") != "pending_driver":
        return
    now = time.time() if now is None else now
    current_id = req.get("dispatchCurrentDriverId")
    current_driver = next((driver for driver in state["drivers"] if driver["id"] == current_id), None)
    deadline = req.get("dispatchDeadline")
    if current_driver and current_driver.get("status") == "idle" and deadline and now < deadline:
        return
    _offer_next_driver(req, now)


def _advance_all_dispatches(now=None):
    now = time.time() if now is None else now
    for req in state["requests"]:
        _advance_request_dispatch(req, now)


def _build_adjacency(graph):
    by_id = {c["id"]: c for c in graph["cities"]}
    adj = {c["id"]: [] for c in graph["cities"]}
    weights = {}

    for a, b in graph["roads"]:
        ca = by_id.get(a)
        cb = by_id.get(b)
        if not ca or not cb:
            continue
        dx = ca["x"] - cb["x"]
        dy = ca["y"] - cb["y"]
        w = max(1, round(math.sqrt(dx * dx + dy * dy) / 20))
        adj[a].append({"to": b, "w": w})
        adj[b].append({"to": a, "w": w})
        key = f"{a}::{b}" if a < b else f"{b}::{a}"
        weights[key] = w

    return by_id, adj, weights


CITY_BY_ID, ADJ, WEIGHTS = _build_adjacency(PUNJAB_GRAPH)

# Fallback pickup/driver positions for city-level locations and seeded drivers.
# Coordinates are [longitude, latitude], matching Mapbox and browser geolocation.
CITY_CENTERS = {
    "amritsar": (74.8723, 31.6340),
    "tarn_taran": (74.7500, 31.4800),
    "gurdaspur": (75.4000, 32.0300),
    "pathankot": (75.6400, 32.2700),
    "hoshiarpur": (75.9800, 31.5300),
    "kapurthala": (75.1500, 31.4200),
    "jalandhar": (75.5800, 31.3300),
    "ludhiana": (75.8600, 30.9000),
    "moga": (75.6500, 30.5500),
    "firozpur": (74.6300, 30.9100),
    "fazilka": (74.2200, 30.5400),
    "abohar": (74.3500, 30.3500),
    "bathinda": (74.9400, 30.2100),
    "faridkot": (75.1500, 30.3500),
    "muktsar": (74.6500, 30.3500),
    "mansa": (75.1500, 29.8500),
    "barnala": (75.7500, 30.3500),
    "sangrur": (75.8500, 30.2500),
    "patiala": (76.3800, 30.3300),
    "malerkotla": (76.4500, 30.5000),
    "rupnagar": (76.3500, 30.5400),
    "mohali": (76.7200, 30.7000),
    "chandigarh": (76.7800, 30.7300),
}
CITY_CENTER_ALIASES = {
    "sri muktsar sahib": "muktsar",
    "rupnagar": "rupnagar",
    "ropar": "rupnagar",
}
DISPATCH_OFFER_SECONDS = 15


def shortest_path(from_id: str, to_id: str):
    if from_id not in CITY_BY_ID or to_id not in CITY_BY_ID:
        return {"path": [], "distance": float("inf")}
    if from_id == to_id:
        return {"path": [from_id], "distance": 0}

    dist = {cid: float("inf") for cid in CITY_BY_ID}
    prev = {}
    visited = set()
    dist[from_id] = 0

    while len(visited) < len(CITY_BY_ID):
        u = None
        best = float("inf")
        for cid, d in dist.items():
            if cid in visited:
                continue
            if d < best:
                best = d
                u = cid
        if u is None or u == to_id:
            break
        visited.add(u)

        for edge in ADJ.get(u, []):
            to = edge["to"]
            w = edge["w"]
            if to in visited:
                continue
            alt = dist[u] + w
            if alt < dist[to]:
                dist[to] = alt
                prev[to] = u

    d = dist.get(to_id, float("inf"))
    if not math.isfinite(d) or d == float("inf"):
        return {"path": [], "distance": float("inf")}

    path = []
    cur = to_id
    while cur:
        path.append(cur)
        cur = prev.get(cur)
        if cur == from_id:
            path.append(from_id)
            break
    path.reverse()
    return {"path": path, "distance": d}


VEHICLE_FARE_ADDONS = {"mini": 0, "sedan": 75, "suv": 120, "premium": 200}


def _round_fare(amount):
    return math.floor(float(amount) + 0.5)


def compute_solo_fare(distance: float, num_persons: int = 1, vehicle_type: str = "sedan") -> int:
    try:
        kilometers = max(0.0, float(distance or 0))
    except (TypeError, ValueError):
        kilometers = 0.0
    return _round_fare(kilometers * 50 + VEHICLE_FARE_ADDONS.get(vehicle_type, VEHICLE_FARE_ADDONS["sedan"]))


def compute_shared_pricing(solo_fare: int, riders: int):
    riders = max(1, int(riders or 1))
    total = _round_fare(solo_fare * (1 + 0.4 * (riders - 1)))
    each = _round_fare(total / riders)
    return {"each": each, "total": total}


def allocate_shared_fares(participants, vehicle_type):
    """Price a shared trip by its longest solo fare, then allocate by passenger-distance."""
    total_people = sum(max(1, int(person.get("numPersons", 1))) for person in participants)
    solo_fares = [
        compute_solo_fare(person.get("routeDistanceKm", 0), vehicle_type=vehicle_type)
        for person in participants
    ]
    solo_total = sum(fare * max(1, int(person.get("numPersons", 1))) for fare, person in zip(solo_fares, participants))
    max_solo = max(solo_fares, default=0)
    target_total = _round_fare(max_solo * (1 + 0.4 * max(0, total_people - 1)))
    total = min(target_total, solo_total)

    weights = [
        max(0.001, float(person.get("routeDistanceKm", 0) or 0)) * max(1, int(person.get("numPersons", 1)))
        for person in participants
    ]
    weight_total = sum(weights) or len(weights) or 1
    raw_shares = [total * weight / weight_total for weight in weights]
    portions = [math.floor(share) for share in raw_shares]
    remainder = total - sum(portions)
    for index in sorted(range(len(raw_shares)), key=lambda i: raw_shares[i] - portions[i], reverse=True)[:remainder]:
        portions[index] += 1
    return {"total": total, "portions": portions, "soloFares": solo_fares}


# ─────────────────────────────────────────────
#  State & Actions
# ─────────────────────────────────────────────

next_id = 1


def make_id(prefix: str) -> str:
    global next_id
    next_id += 1
    return f"{prefix}_{next_id}"


INITIAL_DRIVERS = [
    {"id": "d1", "name": "Ravi", "cityId": "amritsar", "vehicleType": "sedan", "status": "idle"},
    {"id": "d2", "name": "Nikhil Sharma", "cityId": "ludhiana", "vehicleType": "mini", "status": "idle"},
    {"id": "d3", "name": "Arjun", "cityId": "bathinda", "vehicleType": "suv", "status": "idle"},
    {"id": "d4", "name": "Simran", "cityId": "jalandhar", "vehicleType": "premium", "status": "idle"},
    {"id": "d5", "name": "Kabir Gill", "cityId": "chandigarh", "coordinates": [76.7794, 30.7333], "vehicleType": "sedan", "status": "idle"},
    {"id": "d6", "name": "Mehak Kaur", "cityId": "Kharar", "coordinates": [76.6470, 30.7440], "vehicleType": "mini", "status": "idle"},
    {"id": "d7", "name": "Amanpreet Singh", "cityId": "ludhiana", "coordinates": [75.8573, 30.9009], "vehicleType": "suv", "status": "idle"},
    {"id": "d8", "name": "Jasleen Kaur", "cityId": "patiala", "coordinates": [76.3869, 30.3398], "vehicleType": "premium", "status": "idle"},
]

state = {
    "graph": PUNJAB_GRAPH,
    "drivers": [dict(d) for d in INITIAL_DRIVERS],
    "requests": [],
    "rides": [],
    "notifications": [],
}


def reset_demo_state():
    global next_id
    state["drivers"] = [dict(d) for d in INITIAL_DRIVERS]
    state["requests"] = []
    state["rides"] = []
    state["notifications"] = []
    next_id = 1
    state["notifications"].append(
        {
            "id": make_id("n"),
            "type": "state_reset",
            "at": _now_iso(),
            "message": "State reset to demo defaults.",
        }
    )
    return snapshot()


def snapshot():
    _advance_ride_completions()
    _advance_all_dispatches()
    return {
        "serverTime": _now_iso(),
        "drivers": state["drivers"],
        "requests": state["requests"],
        "rides": state["rides"],
        "notifications": state["notifications"][-50:],
    }


def create_ride_request(user_name: str, from_city_id: str, to_city_id: str, wants_sharing: bool, num_persons: int = 1, route_override=None, from_location=None, to_location=None, vehicle_type="sedan"):
    if vehicle_type not in VEHICLE_FARE_ADDONS:
        vehicle_type = "sedan"
    if from_city_id == to_city_id:
        return {"ok": False, "error": "From and To cannot be the same city."}
    route = route_override if isinstance(route_override, dict) else shortest_path(from_city_id, to_city_id)
    if isinstance(route_override, dict):
        try:
            distance = float(route_override.get("distance", 0))
            geometry = route_override.get("geometry")
            if distance <= 0 or not math.isfinite(distance) or not isinstance(geometry, dict) or geometry.get("type") != "LineString":
                return {"ok": False, "error": "A valid driving route is required. Please select the locations again."}
            route = {"path": [str(from_city_id), str(to_city_id)], "distance": round(distance, 2), "geometry": geometry,
                     "fromLocation": from_location, "toLocation": to_location}
        except (TypeError, ValueError):
            return {"ok": False, "error": "The selected route data is invalid."}
    if not route["path"]:
        return {"ok": False, "error": "No route found between selected cities."}

    if from_location is None and isinstance(route, dict):
        from_location = route.get("fromLocation")
    pickup_coordinates = _pickup_coordinates(from_location, from_city_id)
    if not pickup_coordinates:
        return {"ok": False, "error": "Could not determine pickup coordinates for driver proximity search. Select a pickup location from the suggestions."}

    driver_distances = []
    for driver in state["drivers"]:
        if driver.get("vehicleType") != vehicle_type:
            continue
        driver_coordinates = _driver_coordinates(driver)
        if driver_coordinates:
            driver_distances.append((_haversine_km(pickup_coordinates, driver_coordinates), driver["id"]))
    driver_distances.sort(key=lambda item: (item[0], item[1]))

    person_count = max(1, min(6, round(float(num_persons or 1))))
    solo_fare = compute_solo_fare(route["distance"], vehicle_type=vehicle_type)
    shared_pricing = compute_shared_pricing(solo_fare, person_count) if wants_sharing else {"total": solo_fare, "each": _round_fare(solo_fare / person_count)}
    req = {
        "id": make_id("req"),
        "userName": user_name,
        "fromCityId": from_city_id,
        "toCityId": to_city_id,
        "wantsSharing": bool(wants_sharing),
        "numPersons": person_count,
        "status": "pending_driver",
        "createdAt": _now_iso(),
        "route": route,
        "vehicleType": vehicle_type,
        "soloFare": solo_fare,
        "estimatedFare": shared_pricing["total"],
        "farePerPerson": shared_pricing["each"],
        "assignedDriverId": None,
        "rideId": None,
        "pickupCoordinates": list(pickup_coordinates),
        "dispatchDriverOrder": [driver_id for _, driver_id in driver_distances],
        "dispatchDistanceKmByDriver": {driver_id: round(distance, 1) for distance, driver_id in driver_distances},
        "dispatchCursor": 0,
        "offeredDriverIds": [],
        "declinedDriverIds": [],
        "dispatchCurrentDriverId": None,
        "dispatchDeadline": None,
        "dispatchOfferRound": 0,
        "dispatchState": "waiting_for_driver",
    }
    state["requests"].append(req)
    state["notifications"].append(
        {
            "id": make_id("n"),
            "type": "request_created",
            "at": _now_iso(),
            "message": f"New request by {user_name}: {from_city_id} → {to_city_id}",
            "requestId": req["id"],
            "driverId": req["assignedDriverId"],
        }
    )
    _advance_request_dispatch(req)
    return {"ok": True, "request": req}


def cancel_ride_request(request_id: str, user_name: str):
    req = next((item for item in state["requests"] if item["id"] == request_id), None)
    if not req:
        return {"ok": False, "error": "Request not found."}
    if req.get("userName") != user_name:
        return {"ok": False, "error": "This request belongs to a different passenger."}
    if req.get("status") != "pending_driver":
        return {"ok": False, "error": "Only a request that is still waiting for a driver can be cancelled."}

    req["status"] = "cancelled"
    req["dispatchCurrentDriverId"] = None
    req["dispatchDeadline"] = None
    req["dispatchState"] = "cancelled"
    state["notifications"].append({
        "id": make_id("n"),
        "type": "request_cancelled",
        "at": _now_iso(),
        "message": f"{user_name} cancelled ride request {request_id}.",
        "requestId": request_id,
    })
    return {"ok": True, "request": req}


def driver_respond(driver_id: str, request_id: str, accept: bool):
    req = next((r for r in state["requests"] if r["id"] == request_id), None)
    driver = next((d for d in state["drivers"] if d["id"] == driver_id), None)
    if not req:
        return {"ok": False, "error": "Request not found."}
    if not driver:
        return {"ok": False, "error": "Driver not found."}
    if driver.get("vehicleType") != req.get("vehicleType"):
        return {"ok": False, "error": "This request is for a different vehicle type."}
    _advance_request_dispatch(req)
    if req["status"] != "pending_driver":
        return {"ok": False, "error": "Request is not pending."}
    if driver_id not in req.get("offeredDriverIds", []) or driver_id in req.get("declinedDriverIds", []):
        return {"ok": False, "error": "This request has not been offered to this driver."}
    if driver["status"] != "idle":
        return {"ok": False, "error": "Driver is not idle."}

    if not accept:
        req.setdefault("declinedDriverIds", []).append(driver_id)
        state["notifications"].append(
            {
                "id": make_id("n"),
                "type": "request_declined",
                "at": _now_iso(),
                "message": f"Driver {driver['name']} declined request {req['id']}.",
                "requestId": req["id"],
                "driverId": driver_id,
            }
        )
        if req.get("dispatchCurrentDriverId") == driver_id:
            req["dispatchCurrentDriverId"] = None
            req["dispatchDeadline"] = None
            _offer_next_driver(req)
        return {"ok": True, "request": req}

    # Simulate travel at 2 seconds per kilometer. Measure the actual route
    # geometry so map zoom and rounded fare distance do not skew duration.
    duration_seconds = max(1, math.ceil(_route_distance_meters(req["route"]) / 500))
    auto_complete_at_epoch = time.time() + duration_seconds
    ride = {
        "id": make_id("ride"),
        "driverId": driver_id,
        "driverName": driver["name"],
        "primaryUser": req["userName"],
        "passengers": [
            {
                "userName": req["userName"],
                "requestId": req["id"],
                "pickupCityId": req["fromCityId"],
                "dropCityId": req["toCityId"],
                "numPersons": req["numPersons"],
                "routeDistanceKm": _route_distance_meters(req["route"]) / 1000,
                "pricing": {
                    "mode": "shared" if req["wantsSharing"] else "solo",
                    "soloFare": req["soloFare"],
                    "totalFare": req["estimatedFare"],
                    "pay": req["farePerPerson"] if req["wantsSharing"] else req["estimatedFare"],
                },
            }
        ],
        "fromCityId": req["fromCityId"],
        "toCityId": req["toCityId"],
        "route": req["route"],
        "vehicleType": req["vehicleType"],
        "totalFare": req["estimatedFare"],
        "status": "active",
        "requestId": req["id"],
        "autoCompleteAt": datetime.fromtimestamp(auto_complete_at_epoch, timezone.utc).isoformat(),
        "autoCompleteAtEpoch": auto_complete_at_epoch,
        "simulatedDurationSeconds": duration_seconds,
        "shareProposals": [],
    }

    req["status"] = "accepted"
    req["rideId"] = ride["id"]
    req["assignedDriverId"] = driver_id
    req["dispatchCurrentDriverId"] = None
    req["dispatchDeadline"] = None
    req["dispatchState"] = "accepted"
    req["autoCompleteAt"] = ride["autoCompleteAt"]
    driver["status"] = "on_ride"
    driver["cityId"] = req["fromCityId"]
    driver["coordinates"] = req.get("pickupCoordinates")

    state["rides"].append(ride)
    state["notifications"].append(
        {
            "id": make_id("n"),
            "type": "ride_started",
            "at": _now_iso(),
            "message": f"Driver {driver['name']} accepted {req['userName']}'s ride.",
            "requestId": req["id"],
            "rideId": ride["id"],
            "driverId": driver_id,
        }
    )
    return {"ok": True, "request": req, "ride": ride}


def _same_direction_score(a_route, b_route):
    a = a_route.get("path", [])
    b = b_route.get("path", [])
    best = 0
    for i in range(len(a) - 1):
        for j in range(len(b) - 1):
            if a[i] == b[j] and a[i + 1] == b[j + 1]:
                best = max(best, 2)
    return best


def _pickup_drop_available_on_ride(ride, pickup_city_id, drop_city_id):
    path = ride.get("route", {}).get("path", [])
    try:
        p = path.index(pickup_city_id)
        d = path.index(drop_city_id)
    except ValueError:
        return {"ok": False, "reason": "Pickup/drop not on this trip route."}
    if p > d:
        return {"ok": False, "reason": "Drop must come after pickup on the route."}
    return {"ok": True}


def list_share_candidates(request_id: str):
    req = next((r for r in state["requests"] if r["id"] == request_id), None)
    if not req:
        return {"ok": False, "error": "Request not found."}
    if not req["wantsSharing"]:
        return {"ok": False, "error": "Request not marked for sharing."}
    if req["rideId"]:
        return {"ok": False, "error": "This request is already in an active ride."}
    if req["status"] in ("cancelled", "declined"):
        return {"ok": False, "error": "This request is not eligible for sharing."}

    candidates = []
    for ride in state["rides"]:
        score = _same_direction_score(req["route"], ride["route"])
        avail = _pickup_drop_available_on_ride(ride, req["fromCityId"], req["toCityId"])
        candidates.append(
            {
                "rideId": ride["id"],
                "driverName": ride["driverName"],
                "driverId": ride["driverId"],
                "rideStatus": ride["status"],
                "score": score,
                "route": ride["route"],
                "canUseDefaultPickupDrop": avail["ok"],
            }
        )
    return {"ok": True, "candidates": [c for c in candidates if c["score"] >= 2]}


def propose_share(request_id: str, ride_id: str, pickup_city_id: str, drop_city_id: str):
    req = next((r for r in state["requests"] if r["id"] == request_id), None)
    ride = next((r for r in state["rides"] if r["id"] == ride_id), None)
    if not req:
        return {"ok": False, "error": "Request not found."}
    if not ride:
        return {"ok": False, "error": "Ride not found."}
    if req["status"] != "pending_driver":
        return {"ok": False, "error": "Request is not pending."}
    if not req["wantsSharing"]:
        return {"ok": False, "error": "Request not marked for sharing."}
    if req["rideId"]:
        return {"ok": False, "error": "This request is already in a ride."}
    if ride["status"] != "active":
        return {"ok": False, "error": "You can only share into an active ride."}

    avail = _pickup_drop_available_on_ride(ride, pickup_city_id, drop_city_id)
    if not avail["ok"]:
        return {"ok": False, "error": avail["reason"]}

    proposal = {
        "id": make_id("share"),
        "fromUser": req["userName"],
        "requestId": req["id"],
        "pickupCityId": pickup_city_id,
        "dropCityId": drop_city_id,
        "status": "pending",
        "createdAt": _now_iso(),
    }
    ride["shareProposals"].append(proposal)
    state["notifications"].append(
        {
            "id": make_id("n"),
            "type": "share_proposed",
            "at": _now_iso(),
            "message": f"{req['userName']} requested to share ride {ride['id']} (driver {ride['driverName']}).",
            "rideId": ride["id"],
            "requestId": req["id"],
            "toUser": ride["primaryUser"],
        }
    )
    return {"ok": True, "proposal": proposal}


def decide_share(ride_id: str, proposal_id: str, accept: bool):
    ride = next((r for r in state["rides"] if r["id"] == ride_id), None)
    if not ride:
        return {"ok": False, "error": "Ride not found."}
    proposal = next((p for p in ride["shareProposals"] if p["id"] == proposal_id), None)
    if not proposal:
        return {"ok": False, "error": "Proposal not found."}
    if proposal["status"] != "pending":
        return {"ok": False, "error": "Proposal already decided."}

    if not accept:
        proposal["status"] = "rejected"
        state["notifications"].append(
            {
                "id": make_id("n"),
                "type": "share_rejected",
                "at": _now_iso(),
                "message": f"{ride['primaryUser']} rejected share request from {proposal['fromUser']}.",
                "rideId": ride_id,
                "requestId": proposal["requestId"],
            }
        )
        return {"ok": True, "ride": ride}

    proposal["status"] = "accepted"
    req = next((r for r in state["requests"] if r["id"] == proposal["requestId"]), None)
    if not req:
        return {"ok": False, "error": "The passenger request for this share could not be found."}
    joined_passenger = {
        "userName": proposal["fromUser"],
        "requestId": req["id"],
        "pickupCityId": proposal["pickupCityId"],
        "dropCityId": proposal["dropCityId"],
        "numPersons": req["numPersons"],
        "routeDistanceKm": _route_distance_meters(req["route"]) / 1000,
        "pricing": {},
    }
    ride["passengers"].append(joined_passenger)
    fare_allocation = allocate_shared_fares(ride["passengers"], ride.get("vehicleType", "sedan"))
    for index, passenger in enumerate(ride["passengers"]):
        count = max(1, int(passenger.get("numPersons", 1)))
        passenger["pricing"] = {
            "mode": "shared",
            "soloFare": fare_allocation["soloFares"][index],
            "totalFare": fare_allocation["portions"][index],
            "pay": _round_fare(fare_allocation["portions"][index] / count),
        }
        linked_request = next((item for item in state["requests"] if item["id"] == passenger.get("requestId")), None)
        if linked_request:
            linked_request["estimatedFare"] = fare_allocation["portions"][index]
            linked_request["farePerPerson"] = passenger["pricing"]["pay"]
    ride["totalFare"] = fare_allocation["total"]
    ride["shareRiderCount"] = sum(max(1, int(person.get("numPersons", 1))) for person in ride["passengers"])
    if req:
        req["estimatedFare"] = joined_passenger["pricing"].get("totalFare")
        req["farePerPerson"] = joined_passenger["pricing"].get("pay")
        req["status"] = "accepted"
        req["assignedDriverId"] = ride["driverId"]
        req["rideId"] = ride["id"]
        req["dispatchCurrentDriverId"] = None
        req["dispatchDeadline"] = None
        req["dispatchState"] = "accepted"

    state["notifications"].append(
        {
            "id": make_id("n"),
            "type": "share_accepted",
            "at": _now_iso(),
            "message": f"{ride['primaryUser']} accepted sharing with {proposal['fromUser']}. Driver notified for pickup/drop.",
            "rideId": ride_id,
            "requestId": proposal["requestId"],
            "driverId": ride["driverId"],
        }
    )
    return {"ok": True, "ride": ride, "pricing": {"total": ride["totalFare"], "each": joined_passenger["pricing"]["pay"]}}


# ─────────────────────────────────────────────
#  HTTP Request Handler
# ─────────────────────────────────────────────

CLIENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "client"))


class CabApiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=CLIENT_DIR, **kwargs)

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/graph":
            self._send_json(state["graph"])
            return
        elif path == "/api/state":
            self._send_json(snapshot())
            return
        elif path == "/api/share/candidates":
            qs = parse_qs(parsed.query)
            req_id = qs.get("requestId", [None])[0]
            if not req_id:
                self._send_json({"ok": False, "error": "requestId is required."}, 400)
                return
            res = list_share_candidates(req_id)
            self._send_json(res, 200 if res.get("ok") else 400)
            return

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_json()

        if path == "/api/request":
            user_name = body.get("userName")
            from_city = body.get("fromCityId")
            to_city = body.get("toCityId")
            wants_sharing = body.get("wantsSharing", False)
            num_persons = body.get("numPersons", 1)
            route_override = body.get("route")
            from_location = body.get("fromLocation")
            to_location = body.get("toLocation")
            vehicle_type = body.get("vehicleType", "sedan")
            if not user_name or not from_city or not to_city:
                self._send_json({"ok": False, "error": "userName, fromCityId, toCityId are required."}, 400)
                return
            res = create_ride_request(user_name, from_city, to_city, wants_sharing, num_persons, route_override, from_location, to_location, vehicle_type)
            self._send_json(res, 200 if res.get("ok") else 400)
            return
        elif path == "/api/request/cancel":
            request_id = body.get("requestId")
            user_name = body.get("userName")
            if not request_id or not user_name:
                self._send_json({"ok": False, "error": "requestId and userName are required."}, 400)
                return
            res = cancel_ride_request(request_id, user_name)
            self._send_json(res, 200 if res.get("ok") else 400)
            return
        elif path == "/api/driver/respond":
            driver_id = body.get("driverId")
            req_id = body.get("requestId")
            accept = body.get("accept")
            if not driver_id or not req_id or not isinstance(accept, bool):
                self._send_json({"ok": False, "error": "driverId, requestId, accept(boolean) are required."}, 400)
                return
            res = driver_respond(driver_id, req_id, accept)
            self._send_json(res, 200 if res.get("ok") else 400)
            return
        elif path == "/api/share/propose":
            req_id = body.get("requestId")
            ride_id = body.get("rideId")
            pickup = body.get("pickupCityId")
            drop = body.get("dropCityId")
            if not req_id or not ride_id or not pickup or not drop:
                self._send_json({"ok": False, "error": "requestId, rideId, pickupCityId, dropCityId are required."}, 400)
                return
            res = propose_share(req_id, ride_id, pickup, drop)
            self._send_json(res, 200 if res.get("ok") else 400)
            return
        elif path == "/api/share/decide":
            ride_id = body.get("rideId")
            prop_id = body.get("proposalId")
            accept = body.get("accept")
            if not ride_id or not prop_id or not isinstance(accept, bool):
                self._send_json({"ok": False, "error": "rideId, proposalId, accept(boolean) are required."}, 400)
                return
            res = decide_share(ride_id, prop_id, accept)
            self._send_json(res, 200 if res.get("ok") else 400)
            return
        elif path == "/api/reset":
            res = reset_demo_state()
            self._send_json({"ok": True, "state": res})
            return

        self._send_json({"ok": False, "error": "Not Found"}, 404)


def run(port: int = 5174):
    server = HTTPServer(("0.0.0.0", port), CabApiHandler)
    print(f"Python Web UI server running at http://localhost:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()


if __name__ == "__main__":
    reset_demo_state()
    port = int(os.environ.get("PORT", "5174"))
    run(port)
