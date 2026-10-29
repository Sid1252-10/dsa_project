"""
dispatch.py
-----------
Ride sharing scan, driver assignment logic,
queue dispatch, request submission, and cancellation.
Corresponds to dispatch.cpp in the C++ implementation.
"""

from collections import deque
from typing import Optional, Tuple
import cab_types as ct
import driver


def try_ride_share(new_req: ct.RideRequest) -> Tuple[bool, Optional[ct.RideRequest]]:
    """
    Scans the waiting_queue for a compatible co-passenger.
    Both must want sharing AND combined src+dst distance <= SHARE_THRESHOLD.
    Returns (True, matched_req) if found and removes candidate from waiting_queue.
    """
    if not new_req.wants_sharing:
        return False, None

    temp: deque[ct.RideRequest] = deque()
    matched_req: Optional[ct.RideRequest] = None
    found = False

    while ct.waiting_queue:
        candidate = ct.waiting_queue.popleft()
        if not found and candidate.wants_sharing:
            src_dist = ct.manhattan_distance(new_req.source, candidate.source)
            dst_dist = ct.manhattan_distance(new_req.destination, candidate.destination)
            if (src_dist + dst_dist) <= ct.SHARE_THRESHOLD:
                matched_req = candidate
                found = True
                continue  # don't re-queue — it's being matched
        temp.append(candidate)

    ct.waiting_queue = temp
    return found, matched_req


def assign_driver_to_request(req: ct.RideRequest, verbose: bool) -> None:
    """
    Finds the nearest idle driver for req.source.
    If found: marks driver ON_RIDE, records the active ride,
              moves driver position to destination, prints result.
    If not found: pushes req to waiting_queue.

    verbose = True  -> full booking confirmation block (for user submissions)
    verbose = False -> compact one-line log (for batch/auto dispatch)
    """
    driver_idx = driver.find_nearest_driver(req.source)

    if driver_idx == -1:
        if verbose:
            print("\n  *** NO DRIVER AVAILABLE RIGHT NOW ***")
            print("  Your request has been queued. A driver will")
            print("  be assigned as soon as one becomes free.")
            ct.print_separator('=')
        ct.waiting_queue.append(req)
        return

    req.assigned_driver_id = ct.driver_pool[driver_idx].driver_id
    driver.mark_driver_on_ride(driver_idx)
    driver.record_active_ride(ct.driver_pool[driver_idx].driver_id, req)

    dist = ct.manhattan_distance(ct.driver_pool[driver_idx].location, req.source)

    if req.is_shared:
        ct.total_shared_rides += 1

    if verbose:
        print("\n  DRIVER ASSIGNED!")
        print("  ─────────────────────────────────────────")
        print(f"  Driver Name   : {ct.driver_pool[driver_idx].name}")
        print(f"  Driver ID     : {ct.driver_pool[driver_idx].driver_id}")
        print(
            f"  Coming from   : ({ct.driver_pool[driver_idx].location.x},"
            f"{ct.driver_pool[driver_idx].location.y})"
        )
        print(f"  Your pickup   : ({req.source.x},{req.source.y})")
        print(f"  Distance away : {dist} blocks")
        if req.is_shared:
            print(f"  Co-passenger  : {req.shared_with}")
        print(
            f"  >> To mark complete: option 3 -> Driver ID: "
            f"{ct.driver_pool[driver_idx].driver_id}"
        )
        print("  ─────────────────────────────────────────")
        ct.print_separator('=')
    else:
        print(
            f"  [ASSIGNED] Request #{req.request_id} ({req.user_name}) -> "
            f"Driver {ct.driver_pool[driver_idx].name} "
            f"(ID: {ct.driver_pool[driver_idx].driver_id}) | {dist} blocks away"
        )
        print(
            f"  >> To complete: option 3 -> Driver ID: "
            f"{ct.driver_pool[driver_idx].driver_id}"
        )

    # Advance driver's position to the drop-off point
    ct.driver_pool[driver_idx].location = ct.Location(
        x=req.destination.x, y=req.destination.y
    )


def try_dispatch_waiting() -> None:
    """Auto-assign waiting riders with newly freed drivers."""
    if not ct.waiting_queue:
        return

    print(f"\n  Checking waiting queue ({len(ct.waiting_queue)} riders)...")
    still_waiting: deque[ct.RideRequest] = deque()

    while ct.waiting_queue:
        w = ct.waiting_queue.popleft()
        idx = driver.find_nearest_driver(w.source)
        if idx == -1:
            still_waiting.append(w)
        else:
            assign_driver_to_request(w, False)

    ct.waiting_queue = still_waiting

    if not ct.waiting_queue:
        print("  All waiting riders have been assigned.")
    else:
        print(f"  {len(ct.waiting_queue)} rider(s) still waiting.")


def submit_and_dispatch(
    user_name: str,
    src_x: int,
    src_y: int,
    dst_x: int,
    dst_y: int,
    wants_sharing: bool,
    show_booking_header: bool,
) -> None:
    """Full request lifecycle: validate -> share-match -> assign."""
    # Validate: source must differ from destination
    if src_x == dst_x and src_y == dst_y:
        print("[ERROR] Source and destination cannot be the same location.")
        return

    req = ct.RideRequest()
    req.request_id = ct.next_request_id
    ct.next_request_id += 1
    req.user_name = user_name
    req.source = ct.Location(x=src_x, y=src_y)
    req.destination = ct.Location(x=dst_x, y=dst_y)
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
        ct.print_separator('=')
        print(f"  BOOKING STATUS FOR REQUEST #{req.request_id}")
        ct.print_separator('=')

    # Try ride-share match before assigning a driver
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


def process_pending_queue() -> None:
    """Batch process requests left in request_queue."""
    if not ct.request_queue:
        print("  No pending requests in queue.")
        return

    ct.print_separator('=')
    print(f"  BATCH PROCESSING ({len(ct.request_queue)} pending)")
    ct.print_separator('=')
    while ct.request_queue:
        req = ct.request_queue.popleft()
        ct.print_separator()
        print(f"[PROCESSING] Request #{req.request_id} for {req.user_name}")
        share_found, matched = try_ride_share(req)
        if share_found and matched is not None:
            req.is_shared = True
            req.shared_with = matched.user_name
            matched.is_shared = True
            matched.shared_with = req.user_name
            print(f"  Share match with {matched.user_name}")
        assign_driver_to_request(req, False)


def cancel_waiting_request(request_id: int) -> None:
    """Cancel a specific waiting request by request_id."""
    temp: deque[ct.RideRequest] = deque()
    found = False
    while ct.waiting_queue:
        w = ct.waiting_queue.popleft()
        if not found and w.request_id == request_id:
            found = True
            print(
                f"  [CANCELLED] Request #{request_id} "
                f"({w.user_name}) removed from waiting queue."
            )
        else:
            temp.append(w)
    ct.waiting_queue = temp
    if not found:
        print(f"  [ERROR] Request #{request_id} not found in waiting queue.")
