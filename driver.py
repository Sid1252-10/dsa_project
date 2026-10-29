"""
driver.py
---------
Driver registration, active ride tracking,
ride completion, and driver status display.
Corresponds to driver.cpp in the C++ implementation.
"""

import cab_types as ct
import dispatch


def register_driver(driver_id: int, name: str, x: int, y: int) -> bool:
    """Register a new driver in the driver pool."""
    if ct.driver_count >= ct.MAX_DRIVERS:
        print("[ERROR] Driver pool is full.")
        return False
    if find_driver_index_by_id(driver_id) != -1:
        print(f"[ERROR] Driver ID {driver_id} already exists.")
        return False

    d = ct.Driver(
        driver_id=driver_id,
        name=name,
        location=ct.Location(x=x, y=y),
        state=ct.DRIVER_IDLE,
        is_registered=True,
    )
    ct.driver_pool[ct.driver_count] = d
    ct.driver_count += 1
    print(f"[DRIVER REGISTERED] {name} at ({x},{y}) | ID: {driver_id}")
    return True


def find_driver_index_by_id(driver_id: int) -> int:
    """Returns pool index for driver_id, or -1 if not found."""
    for i in range(ct.driver_count):
        if ct.driver_pool[i].is_registered and ct.driver_pool[i].driver_id == driver_id:
            return i
    return -1


def find_nearest_driver(src: ct.Location) -> int:
    """Returns pool index of nearest IDLE driver to src, or -1 if none."""
    best_index = -1
    best_distance = float("inf")
    for i in range(ct.driver_count):
        if not ct.driver_pool[i].is_registered:
            continue
        if ct.driver_pool[i].state != ct.DRIVER_IDLE:
            continue
        dist = ct.manhattan_distance(ct.driver_pool[i].location, src)
        if dist < best_distance:
            best_distance = dist
            best_index = i
    return best_index


def mark_driver_on_ride(pool_index: int) -> None:
    """Mark driver at pool_index as ON_RIDE."""
    ct.driver_pool[pool_index].state = ct.DRIVER_ON_RIDE


def record_active_ride(driver_id: int, req: ct.RideRequest) -> None:
    """Record an active ride in the tracker."""
    for i in range(ct.MAX_DRIVERS):
        if not ct.active_rides[i].in_use:
            ct.active_rides[i].in_use = True
            ct.active_rides[i].driver_id = driver_id
            ct.active_rides[i].request_id = req.request_id
            ct.active_rides[i].rider_name = req.user_name
            ct.active_rides[i].co_rider = req.shared_with
            return


def clear_active_ride(driver_id: int) -> None:
    """Clear the active ride associated with driver_id."""
    for i in range(ct.MAX_DRIVERS):
        if ct.active_rides[i].in_use and ct.active_rides[i].driver_id == driver_id:
            ct.active_rides[i].in_use = False
            return


def get_rider_for_driver(driver_id: int) -> str:
    """Returns name of rider in driver's cab, or empty string if idle."""
    for i in range(ct.MAX_DRIVERS):
        if ct.active_rides[i].in_use and ct.active_rides[i].driver_id == driver_id:
            return ct.active_rides[i].rider_name
    return ""


def complete_ride(driver_id: int) -> None:
    """Complete an active ride, free the driver, and dispatch waiting riders."""
    ct.print_separator('=')
    print("[RIDE COMPLETE]")

    idx = find_driver_index_by_id(driver_id)
    if idx == -1:
        print(f"[ERROR] Driver ID {driver_id} not found.")
        ct.print_separator('=')
        return
    if ct.driver_pool[idx].state != ct.DRIVER_ON_RIDE:
        print(f"[ERROR] Driver {ct.driver_pool[idx].name} is already IDLE — no active ride to complete.")
        ct.print_separator('=')
        return

    clear_active_ride(driver_id)
    ct.driver_pool[idx].state = ct.DRIVER_IDLE
    # Location is already set to the drop-off point from when ride was assigned
    print(f"  Driver {ct.driver_pool[idx].name} is now IDLE at ({ct.driver_pool[idx].location.x},{ct.driver_pool[idx].location.y})")
    ct.total_rides_completed += 1

    # Auto-assign waiting riders with the newly freed driver
    dispatch.try_dispatch_waiting()
    ct.print_separator('=')


def display_driver_status() -> None:
    """Print the Driver Status Board."""
    ct.print_separator('=')
    print("  DRIVER STATUS BOARD")
    ct.print_separator('=')
    print("  ID  | Name            | Location | State    | Carrying")
    ct.print_separator()
    for i in range(ct.driver_count):
        if not ct.driver_pool[i].is_registered:
            continue
        state_str = "IDLE    " if ct.driver_pool[i].state == ct.DRIVER_IDLE else "ON RIDE "
        rider = (
            get_rider_for_driver(ct.driver_pool[i].driver_id)
            if ct.driver_pool[i].state == ct.DRIVER_ON_RIDE
            else "-"
        )
        pad = max(0, 15 - len(ct.driver_pool[i].name))
        name_part = ct.driver_pool[i].name + (" " * pad)
        print(
            f"  {ct.driver_pool[i].driver_id}   | {name_part} | "
            f"({ct.driver_pool[i].location.x},{ct.driver_pool[i].location.y})    | "
            f"{state_str} | {rider}"
        )
    ct.print_separator()


def display_active_rides() -> None:
    """Print the Active Rides Dashboard."""
    ct.print_separator('=')
    print("  ACTIVE RIDES")
    ct.print_separator('=')
    any_active = False
    for i in range(ct.MAX_DRIVERS):
        if not ct.active_rides[i].in_use:
            continue
        any_active = True
        idx = find_driver_index_by_id(ct.active_rides[i].driver_id)
        dname = ct.driver_pool[idx].name if idx != -1 else "?"
        line = (
            f"  Driver : {dname} (ID: {ct.active_rides[i].driver_id}) | "
            f"Rider: {ct.active_rides[i].rider_name} | "
            f"Req #{ct.active_rides[i].request_id}"
        )
        if ct.active_rides[i].co_rider:
            line += f" [shared with {ct.active_rides[i].co_rider}]"
        print(line)
        print(f"    >> To complete: option 3 -> Driver ID: {ct.active_rides[i].driver_id}")
    if not any_active:
        print("  No active rides right now.")
    ct.print_separator('=')
