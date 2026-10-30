"""
cab_types.py
------------
Shared dataclasses, constants, global state variables,
and utilities for the Cab Allocation & Ride Sharing System.
Corresponds to types.h in the C++ implementation.
"""

from dataclasses import dataclass, field
from collections import deque
import types as _stdlib_types

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
    state: int = DRIVER_IDLE      # DRIVER_IDLE or DRIVER_ON_RIDE
    is_registered: bool = False


@dataclass
class ActiveRide:
    driver_id: int = 0
    request_id: int = 0
    rider_name: str = ""
    co_rider: str = ""   # empty if solo
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


def reset_state() -> None:
    """Reset all global state to startup defaults."""
    global driver_count, next_request_id, total_rides_completed, total_shared_rides
    request_queue.clear()
    waiting_queue.clear()
    for i in range(MAX_DRIVERS):
        driver_pool[i] = Driver()
        active_rides[i] = ActiveRide()
    driver_count = 0
    next_request_id = 1
    total_rides_completed = 0
    total_shared_rides = 0


# ─────────────────────────────────────────────
#  Utilities
# ─────────────────────────────────────────────

def manhattan_distance(a: Location, b: Location) -> int:
    return abs(a.x - b.x) + abs(a.y - b.y)


def print_separator(ch: str = '-', width: int = 55) -> None:
    print(ch * width)


# Expose symbols safely onto sys.modules['types'] to support `import types`
for _k, _v in list(globals().items()):
    if not _k.startswith('_'):
        setattr(_stdlib_types, _k, _v)
