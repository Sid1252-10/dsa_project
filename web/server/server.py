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


def compute_solo_fare(distance: int, num_persons: int = 1) -> int:
    base = 55
    per_km = 20
    persons = max(1, min(6, round(float(num_persons or 1))))
    return round((base + per_km * distance) * (1 + (persons - 1) * 0.6))


def compute_shared_pricing(solo_fare: int, riders: int):
    total = round(solo_fare * 1.3)
    each = round(total / riders)
    return {"each": each, "total": total}


# ─────────────────────────────────────────────
#  State & Actions
# ─────────────────────────────────────────────

next_id = 1


def make_id(prefix: str) -> str:
    global next_id
    next_id += 1
    return f"{prefix}_{next_id}"


INITIAL_DRIVERS = [
    {"id": "d1", "name": "Ravi", "cityId": "amritsar", "status": "idle"},
    {"id": "d2", "name": "Priya", "cityId": "ludhiana", "status": "idle"},
    {"id": "d3", "name": "Arjun", "cityId": "bathinda", "status": "idle"},
    {"id": "d4", "name": "Simran", "cityId": "jalandhar", "status": "idle"},
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
    return {
        "serverTime": _now_iso(),
        "drivers": state["drivers"],
        "requests": state["requests"],
        "rides": state["rides"],
        "notifications": state["notifications"][-50:],
    }


def create_ride_request(user_name: str, from_city_id: str, to_city_id: str, wants_sharing: bool, num_persons: int = 1, route_override=None, from_location=None, to_location=None):
    if from_city_id == to_city_id:
        return {"ok": False, "error": "From and To cannot be the same city."}
    route = route_override if isinstance(route_override, dict) else shortest_path(from_city_id, to_city_id)
    if isinstance(route_override, dict):
        try:
            distance = float(route_override.get("distance", 0))
            geometry = route_override.get("geometry")
            if distance <= 0 or not math.isfinite(distance) or not isinstance(geometry, dict) or geometry.get("type") != "LineString":
                return {"ok": False, "error": "A valid driving route is required. Please select the locations again."}
            route = {"path": [str(from_city_id), str(to_city_id)], "distance": round(distance, 1), "geometry": geometry,
                     "fromLocation": from_location, "toLocation": to_location}
        except (TypeError, ValueError):
            return {"ok": False, "error": "The selected route data is invalid."}
    if not route["path"]:
        return {"ok": False, "error": "No route found between selected cities."}

    req = {
        "id": make_id("req"),
        "userName": user_name,
        "fromCityId": from_city_id,
        "toCityId": to_city_id,
        "wantsSharing": bool(wants_sharing),
        "numPersons": max(1, min(6, round(float(num_persons or 1)))),
        "status": "pending_driver",
        "createdAt": _now_iso(),
        "route": route,
        "soloFare": compute_solo_fare(route["distance"], num_persons),
        "assignedDriverId": None,
        "rideId": None,
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
    return {"ok": True, "request": req}


def driver_respond(driver_id: str, request_id: str, accept: bool):
    req = next((r for r in state["requests"] if r["id"] == request_id), None)
    driver = next((d for d in state["drivers"] if d["id"] == driver_id), None)
    if not req:
        return {"ok": False, "error": "Request not found."}
    if not driver:
        return {"ok": False, "error": "Driver not found."}
    if req["status"] != "pending_driver":
        return {"ok": False, "error": "Request is not pending."}
    if req["assignedDriverId"] and req["assignedDriverId"] != driver_id:
        return {"ok": False, "error": "This request is assigned to a different driver."}
    if driver["status"] != "idle":
        return {"ok": False, "error": "Driver is not idle."}

    if not accept:
        req["status"] = "declined"
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
        return {"ok": True, "request": req}

    ride = {
        "id": make_id("ride"),
        "driverId": driver_id,
        "driverName": driver["name"],
        "primaryUser": req["userName"],
        "passengers": [
            {
                "userName": req["userName"],
                "pickupCityId": req["fromCityId"],
                "dropCityId": req["toCityId"],
                "pricing": {"mode": "solo", "soloFare": req["soloFare"], "pay": req["soloFare"]},
            }
        ],
        "fromCityId": req["fromCityId"],
        "toCityId": req["toCityId"],
        "route": req["route"],
        "status": "active",
        "shareProposals": [],
    }

    req["status"] = "accepted"
    req["rideId"] = ride["id"]
    req["assignedDriverId"] = driver_id
    driver["status"] = "on_ride"
    driver["cityId"] = req["fromCityId"]

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
    primary = ride["passengers"][0]
    solo_fare = primary["pricing"].get("soloFare") or compute_solo_fare(ride["route"]["distance"])
    pricing = compute_shared_pricing(solo_fare, 2)

    primary["pricing"] = {"mode": "shared", "soloFare": solo_fare, "pay": pricing["each"]}
    ride["passengers"].append(
        {
            "userName": proposal["fromUser"],
            "pickupCityId": proposal["pickupCityId"],
            "dropCityId": proposal["dropCityId"],
            "pricing": {"mode": "shared", "soloFare": solo_fare, "pay": pricing["each"]},
        }
    )

    req = next((r for r in state["requests"] if r["id"] == proposal["requestId"]), None)
    if req:
        req["status"] = "accepted"
        req["assignedDriverId"] = ride["driverId"]
        req["rideId"] = ride["id"]

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
    return {"ok": True, "ride": ride, "pricing": pricing}


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
            if not user_name or not from_city or not to_city:
                self._send_json({"ok": False, "error": "userName, fromCityId, toCityId are required."}, 400)
                return
            res = create_ride_request(user_name, from_city, to_city, wants_sharing, num_persons, route_override, from_location, to_location)
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
