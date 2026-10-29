"""
cab_system.py
=============
Queue-Based Cab Allocation & Ride Sharing System
DSA Project  |  Python (Rewritten from cab_system.cpp)

Core Data Structures:
  - Request Queue  : FIFO queue of incoming ride requests
  - Waiting Queue  : Unmatched / shareable requests
  - Driver Pool    : Fixed array of registered drivers
  - Active Rides   : Tracks driver -> rider mapping

Design:
  - Manhattan distance for fast proximity checks
  - FIFO ensures fair request handling
  - Queue scan for ride-sharing before assigning driver
  - Standalone single-file version corresponding to cab_system.cpp
"""

from collections import deque
from dataclasses import dataclass, field
import sys
from typing import Optional, Tuple

# ─────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────
MAX_DRIVERS: int = 20
SHARE_THRESHOLD: int = 3   # max Manhattan dist to allow ride-sharing
DRIVER_IDLE: int = 0
DRIVER_ON_RIDE: int = 1

# ─────────────────────────────────────────────
#  Data Structures
# ─────────────────────────────────────────────

@dataclass
class Location:
    x: int = 0
    y: int = 0


@dataclass
class RideRequest:
    request_id: int = 0
    user_name: str = ""
    source: Location = field(default_factory=Location)
    destination: Location = field(default_factory=Location)
    wants_sharing: bool = False
    is_shared: bool = False
    shared_with: str = ""
    assigned_driver_id: int = -1  # -1 = unassigned


@dataclass
class Driver:
    driver_id: int = 0
    name: str = ""
    location: Location = field(default_factory=Location)
    state: int = DRIVER_IDLE
    is_registered: bool = False


@dataclass
class ActiveRide:
    driver_id: int = 0
    request_id: int = 0
    rider_name: str = ""
    co_rider: str = ""
    in_use: bool = False


# ─────────────────────────────────────────────
#  Global State
# ─────────────────────────────────────────────

request_queue: deque[RideRequest] = deque()
waiting_queue: deque[RideRequest] = deque()
driver_pool: list[Driver] = [Driver() for _ in range(MAX_DRIVERS)]
driver_count: int = 0
active_rides: list[ActiveRide] = [ActiveRide() for _ in range(MAX_DRIVERS)]
next_request_id: int = 1
total_rides_completed: int = 0
total_shared_rides: int = 0

_token_buffer: list[str] = []


def _next_token(prompt: str = "") -> str:
    """Read next whitespace-delimited token from standard input, matching C++ cin semantics."""
    global _token_buffer
    if prompt:
        print(prompt, end="", flush=True)
    while not _token_buffer:
        line = sys.stdin.readline()
        if not line:
            return ""
        _token_buffer = line.split()
    return _token_buffer.pop(0)


# ─────────────────────────────────────────────
#  Utility
# ─────────────────────────────────────────────

def manhattan_distance(a: Location, b: Location) -> int:
    return abs(a.x - b.x) + abs(a.y - b.y)


def print_separator(ch: str = '-', width: int = 55) -> None:
    print(ch * width)


def find_driver_index_by_id(driver_id: int) -> int:
    for i in range(driver_count):
        if driver_pool[i].is_registered and driver_pool[i].driver_id == driver_id:
            return i
    return -1


def find_nearest_driver(src: Location) -> int:
    best_index = -1
    best_distance = float("inf")
    for i in range(driver_count):
        if not driver_pool[i].is_registered:
            continue
        if driver_pool[i].state != DRIVER_IDLE:
            continue
        dist = manhattan_distance(driver_pool[i].location, src)
        if dist < best_distance:
            best_distance = dist
            best_index = i
    return best_index


# ─────────────────────────────────────────────
#  Active Ride Tracker
# ─────────────────────────────────────────────

def record_active_ride(driver_id: int, req: RideRequest) -> None:
    for i in range(MAX_DRIVERS):
        if not active_rides[i].in_use:
            active_rides[i].in_use = True
            active_rides[i].driver_id = driver_id
            active_rides[i].request_id = req.request_id
            active_rides[i].rider_name = req.user_name
            active_rides[i].co_rider = req.shared_with
            return


def clear_active_ride(driver_id: int) -> None:
    for i in range(MAX_DRIVERS):
        if active_rides[i].in_use and active_rides[i].driver_id == driver_id:
            active_rides[i].in_use = False
            return


def get_rider_for_driver(driver_id: int) -> str:
    for i in range(MAX_DRIVERS):
        if active_rides[i].in_use and active_rides[i].driver_id == driver_id:
            return active_rides[i].rider_name
    return ""


# ─────────────────────────────────────────────
#  Driver Management
# ─────────────────────────────────────────────

def register_driver(driver_id: int, name: str, x: int, y: int) -> bool:
    global driver_count
    if driver_count >= MAX_DRIVERS:
        print("[ERROR] Driver pool is full.")
        return False
    if find_driver_index_by_id(driver_id) != -1:
        print(f"[ERROR] Driver ID {driver_id} already exists.")
        return False

    d = Driver(
        driver_id=driver_id,
        name=name,
        location=Location(x=x, y=y),
        state=DRIVER_IDLE,
        is_registered=True,
    )
    driver_pool[driver_count] = d
    driver_count += 1
    print(f"[DRIVER REGISTERED] {name} at ({x},{y}) | ID: {driver_id}")
    return True


# ─────────────────────────────────────────────
#  Ride Completion
# ─────────────────────────────────────────────

def complete_ride(driver_id: int) -> None:
    global total_rides_completed
    print_separator('=')
    print("[RIDE COMPLETE]")

    idx = find_driver_index_by_id(driver_id)
    if idx == -1:
        print(f"[ERROR] Driver ID {driver_id} not found.")
        print_separator('=')
        return
    if driver_pool[idx].state != DRIVER_ON_RIDE:
        print(f"[ERROR] Driver {driver_pool[idx].name} is already IDLE — no active ride to complete.")
        print_separator('=')
        return

    clear_active_ride(driver_id)
    driver_pool[idx].state = DRIVER_IDLE
    print(
        f"  Driver {driver_pool[idx].name} is now IDLE at "
        f"({driver_pool[idx].location.x},{driver_pool[idx].location.y})"
    )
    total_rides_completed += 1

    try_dispatch_waiting()
    print_separator('=')


# ─────────────────────────────────────────────
#  Ride Sharing Logic
# ─────────────────────────────────────────────

def try_ride_share(new_req: RideRequest) -> Tuple[bool, Optional[RideRequest]]:
    global waiting_queue
    if not new_req.wants_sharing:
        return False, None

    temp: deque[RideRequest] = deque()
    matched_req: Optional[RideRequest] = None
    found = False

    while waiting_queue:
        candidate = waiting_queue.popleft()
        if not found and candidate.wants_sharing:
            src_dist = manhattan_distance(new_req.source, candidate.source)
            dst_dist = manhattan_distance(new_req.destination, candidate.destination)
            if (src_dist + dst_dist) <= SHARE_THRESHOLD:
                matched_req = candidate
                found = True
                continue
        temp.append(candidate)

    waiting_queue = temp
    return found, matched_req


# ─────────────────────────────────────────────
#  Core Assignment Logic
# ─────────────────────────────────────────────

def assign_driver_to_request(req: RideRequest, verbose: bool) -> None:
    global total_shared_rides
    driver_idx = find_nearest_driver(req.source)

    if driver_idx == -1:
        if verbose:
            print("\n  *** NO DRIVER AVAILABLE RIGHT NOW ***")
            print("  Your request has been queued. A driver will")
            print("  be assigned as soon as one becomes free.")
            print_separator('=')
        waiting_queue.append(req)
        return

    req.assigned_driver_id = driver_pool[driver_idx].driver_id
    driver_pool[driver_idx].state = DRIVER_ON_RIDE
    record_active_ride(driver_pool[driver_idx].driver_id, req)

    dist = manhattan_distance(driver_pool[driver_idx].location, req.source)

    if req.is_shared:
        total_shared_rides += 1

    if verbose:
        print("\n  DRIVER ASSIGNED!")
        print("  ─────────────────────────────────────────")
        print(f"  Driver Name   : {driver_pool[driver_idx].name}")
        print(f"  Driver ID     : {driver_pool[driver_idx].driver_id}")
        print(
            f"  Coming from   : ({driver_pool[driver_idx].location.x},"
            f"{driver_pool[driver_idx].location.y})"
        )
        print(f"  Your pickup   : ({req.source.x},{req.source.y})")
        print(f"  Distance away : {dist} blocks")
        if req.is_shared:
            print(f"  Co-passenger  : {req.shared_with}")
        print(
            f"  >> To mark complete: option 3 -> Driver ID: "
            f"{driver_pool[driver_idx].driver_id}"
        )
        print("  ─────────────────────────────────────────")
        print_separator('=')
    else:
        print(
            f"  [ASSIGNED] Request #{req.request_id} ({req.user_name}) -> "
            f"Driver {driver_pool[driver_idx].name} "
            f"(ID: {driver_pool[driver_idx].driver_id}) | {dist} blocks away"
        )
        print(
            f"  >> To complete: option 3 -> Driver ID: "
            f"{driver_pool[driver_idx].driver_id}"
        )

    driver_pool[driver_idx].location = Location(
        x=req.destination.x, y=req.destination.y
    )


# ─────────────────────────────────────────────
#  Auto-dispatch Waiting Queue
# ─────────────────────────────────────────────

def try_dispatch_waiting() -> None:
    global waiting_queue
    if not waiting_queue:
        return

    print(f"\n  Checking waiting queue ({len(waiting_queue)} riders)...")
    still_waiting: deque[RideRequest] = deque()

    while waiting_queue:
        w = waiting_queue.popleft()
        idx = find_nearest_driver(w.source)
        if idx == -1:
            still_waiting.append(w)
        else:
            assign_driver_to_request(w, False)

    waiting_queue = still_waiting

    if not waiting_queue:
        print("  All waiting riders have been assigned.")
    else:
        print(f"  {len(waiting_queue)} rider(s) still waiting.")


# ─────────────────────────────────────────────
#  Request Submission
# ─────────────────────────────────────────────

def submit_and_dispatch(
    user_name: str,
    src_x: int,
    src_y: int,
    dst_x: int,
    dst_y: int,
    wants_sharing: bool,
    show_booking_header: bool,
) -> None:
    global next_request_id
    if src_x == dst_x and src_y == dst_y:
        print("[ERROR] Source and destination cannot be the same location.")
        return

    req = RideRequest()
    req.request_id = next_request_id
    next_request_id += 1
    req.user_name = user_name
    req.source = Location(x=src_x, y=src_y)
    req.destination = Location(x=dst_x, y=dst_y)
    req.wants_sharing = wants_sharing
    req.is_shared = False
    req.shared_with = ""
    req.assigned_driver_id = -1

    print(
        f"[REQUEST] #{req.request_id} | {user_name} | "
        f"({src_x},{src_y}) -> ({dst_x},{dst_y}) | "
        f"Share: {'YES' if wants_sharing else 'NO'}"
    )

    if show_booking_header:
        print_separator('=')
        print(f"  BOOKING STATUS FOR REQUEST #{req.request_id}")
        print_separator('=')

    share_found, matched = try_ride_share(req)
    if share_found and matched is not None:
        req.is_shared = True
        req.shared_with = matched.user_name
        matched.is_shared = True
        matched.shared_with = req.user_name
        print(
            f"  Ride-share match found with {matched.user_name} "
            f"(Request #{matched.request_id})"
        )

    assign_driver_to_request(req, show_booking_header)


# ─────────────────────────────────────────────
#  Batch Process
# ─────────────────────────────────────────────

def process_pending_queue() -> None:
    if not request_queue:
        print("  No pending requests in queue.")
        return

    print_separator('=')
    print(f"  BATCH PROCESSING ({len(request_queue)} pending)")
    print_separator('=')
    while request_queue:
        req = request_queue.popleft()
        print_separator()
        print(f"[PROCESSING] Request #{req.request_id} for {req.user_name}")
        share_found, matched = try_ride_share(req)
        if share_found and matched is not None:
            req.is_shared = True
            req.shared_with = matched.user_name
            matched.is_shared = True
            matched.shared_with = req.user_name
            print(f"  Share match with {matched.user_name}")
        assign_driver_to_request(req, False)


# ─────────────────────────────────────────────
#  Status Display
# ─────────────────────────────────────────────

def display_driver_status() -> None:
    print_separator('=')
    print("  DRIVER STATUS BOARD")
    print_separator('=')
    print("  ID  | Name            | Location | State    | Carrying")
    print_separator()
    for i in range(driver_count):
        if not driver_pool[i].is_registered:
            continue
        state_str = "IDLE    " if driver_pool[i].state == DRIVER_IDLE else "ON RIDE "
        rider = (
            get_rider_for_driver(driver_pool[i].driver_id)
            if driver_pool[i].state == DRIVER_ON_RIDE
            else "-"
        )
        pad = max(0, 15 - len(driver_pool[i].name))
        name_part = driver_pool[i].name + (" " * pad)
        print(
            f"  {driver_pool[i].driver_id}   | {name_part} | "
            f"({driver_pool[i].location.x},{driver_pool[i].location.y})    | "
            f"{state_str} | {rider}"
        )
    print_separator()


def display_queue_status() -> None:
    print_separator('=')
    print("  QUEUE STATUS")
    print_separator('=')

    idle_count = 0
    for i in range(driver_count):
        if driver_pool[i].is_registered and driver_pool[i].state == DRIVER_IDLE:
            idle_count += 1

    print(
        f"  Drivers          : {driver_count} total, "
        f"{idle_count} idle, "
        f"{driver_count - idle_count} on ride"
    )
    print(f"  Pending Queue    : {len(request_queue)} requests")
    print(f"  Waiting Queue    : {len(waiting_queue)} riders")
    print(f"  Rides Completed  : {total_rides_completed}")
    print(f"  Shared Rides     : {total_shared_rides}")

    if waiting_queue:
        print_separator()
        print("  Waiting riders:")
        for w in waiting_queue:
            share_tag = " [share ok]" if w.wants_sharing else ""
            print(
                f"    #{w.request_id} {w.user_name} | "
                f"({w.source.x},{w.source.y}) -> ({w.destination.x},{w.destination.y})"
                f"{share_tag}"
            )

    print_separator('=')


def display_active_rides() -> None:
    print_separator('=')
    print("  ACTIVE RIDES")
    print_separator('=')
    any_active = False
    for i in range(MAX_DRIVERS):
        if not active_rides[i].in_use:
            continue
        any_active = True
        idx = find_driver_index_by_id(active_rides[i].driver_id)
        dname = driver_pool[idx].name if idx != -1 else "?"
        line = (
            f"  Driver : {dname} (ID: {active_rides[i].driver_id}) | "
            f"Rider: {active_rides[i].rider_name} | "
            f"Req #{active_rides[i].request_id}"
        )
        if active_rides[i].co_rider:
            line += f" [shared with {active_rides[i].co_rider}]"
        print(line)
        print(f"    >> To complete: option 3 -> Driver ID: {active_rides[i].driver_id}")
    if not any_active:
        print("  No active rides right now.")
    print_separator('=')


# ─────────────────────────────────────────────
#  Cancel a Waiting Request
# ─────────────────────────────────────────────

def cancel_waiting_request(request_id: int) -> None:
    global waiting_queue
    temp: deque[RideRequest] = deque()
    found = False
    while waiting_queue:
        w = waiting_queue.popleft()
        if not found and w.request_id == request_id:
            found = True
            print(
                f"  [CANCELLED] Request #{request_id} "
                f"({w.user_name}) removed from waiting queue."
            )
        else:
            temp.append(w)
    waiting_queue = temp
    if not found:
        print(f"  [ERROR] Request #{request_id} not found in waiting queue.")


# ─────────────────────────────────────────────
#  Interactive Menu
# ─────────────────────────────────────────────

def show_menu() -> None:
    print_separator('=')
    print("  CAB ALLOCATION SYSTEM")
    print_separator('=')
    print("  1. Submit a Ride Request")
    print("  2. Process Pending Queue (batch)")
    print("  3. Mark a Ride as Complete")
    print("  4. View Driver Status")
    print("  5. View Queue & Stats")
    print("  6. Add a New Driver")
    print("  7. View Active Rides")
    print("  8. Cancel a Waiting Request")
    print("  0. Exit")
    print_separator()
    print("  Enter choice: ", end="", flush=True)


def menu_submit_request() -> None:
    name = _next_token("\n  User Name         : ")
    if not name:
        return
    sx_str = _next_token("  Source X Y        : ")
    sy_str = _next_token("")
    dx_str = _next_token("  Destination X Y   : ")
    dy_str = _next_token("")
    share_ch = _next_token("  Want ride sharing? (y/n): ")

    try:
        sx, sy = int(sx_str), int(sy_str)
        dx, dy = int(dx_str), int(dy_str)
    except ValueError:
        print("[ERROR] Coordinates must be valid integers.")
        return

    share = share_ch.lower() == "y"
    submit_and_dispatch(name, sx, sy, dx, dy, share, True)


def menu_complete_ride() -> None:
    d_str = _next_token("\n  Driver ID (shown when ride was assigned): ")
    if not d_str:
        return
    try:
        driver_id = int(d_str)
    except ValueError:
        print("[ERROR] Driver ID must be an integer.")
        return
    complete_ride(driver_id)


def menu_add_driver() -> None:
    id_str = _next_token("\n  Driver ID    : ")
    if not id_str:
        return
    name = _next_token("  Driver Name  : ")
    x_str = _next_token("  Location X Y : ")
    y_str = _next_token("")

    try:
        driver_id = int(id_str)
        x = int(x_str)
        y = int(y_str)
    except ValueError:
        print("[ERROR] ID and coordinates must be valid integers.")
        return

    register_driver(driver_id, name, x, y)


def menu_cancel_request() -> None:
    req_str = _next_token("\n  Request ID to cancel: ")
    if not req_str:
        return
    try:
        req_id = int(req_str)
    except ValueError:
        print("[ERROR] Request ID must be an integer.")
        return
    cancel_waiting_request(req_id)


# ─────────────────────────────────────────────
#  Demo Seed Data
# ─────────────────────────────────────────────

def load_demo_data() -> None:
    print("\n[DEMO] Setting up 3 drivers and 5 ride requests...\n")

    register_driver(101, "Ravi", 2, 3)
    register_driver(102, "Priya", 8, 1)
    register_driver(103, "Arjun", 5, 7)
    print()

    # Each request is submitted and immediately dispatched
    submit_and_dispatch("Alice", 1, 2, 6, 8, True, False)
    submit_and_dispatch("Bob", 2, 3, 6, 9, True, False)
    submit_and_dispatch("Charlie", 9, 0, 3, 3, False, False)
    submit_and_dispatch("Diana", 5, 6, 1, 1, True, False)
    submit_and_dispatch("Eve", 10, 10, 0, 0, False, False)
    print()


# ─────────────────────────────────────────────
#  Main
# ─────────────────────────────────────────────

def main() -> None:
    for i in range(MAX_DRIVERS):
        active_rides[i].in_use = False

    print()
    print_separator('=')
    print("   QUEUE-BASED CAB ALLOCATION & RIDE SHARING SYSTEM")
    print_separator('=')

    load_demo_data()
    display_driver_status()
    display_queue_status()

    choice = -1
    while choice != 0:
        show_menu()
        token = _next_token()
        if not token:
            break
        try:
            choice = int(token)
        except ValueError:
            choice = -1

        print()

        if choice == 1:
            menu_submit_request()
        elif choice == 2:
            process_pending_queue()
            display_driver_status()
        elif choice == 3:
            menu_complete_ride()
        elif choice == 4:
            display_driver_status()
        elif choice == 5:
            display_queue_status()
        elif choice == 6:
            menu_add_driver()
        elif choice == 7:
            display_active_rides()
        elif choice == 8:
            menu_cancel_request()
        elif choice == 0:
            print("  Exiting. Goodbye!")
        else:
            print("  [ERROR] Invalid option.")

        print()


if __name__ == "__main__":
    main()
