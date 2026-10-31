"""
main.py
-------
Global variable management, queue/stats display,
interactive menu, demo seed data, and main().
Corresponds to main.cpp in the C++ implementation.
"""

import sys
import cab_types as ct
import driver
import dispatch

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


def display_queue_status() -> None:
    """Print queue sizes and aggregate system statistics."""
    ct.print_separator('=')
    print("  QUEUE STATUS")
    ct.print_separator('=')

    idle_count = 0
    for i in range(ct.driver_count):
        if ct.driver_pool[i].is_registered and ct.driver_pool[i].state == ct.DRIVER_IDLE:
            idle_count += 1

    print(
        f"  Drivers          : {ct.driver_count} total, "
        f"{idle_count} idle, "
        f"{ct.driver_count - idle_count} on ride"
    )
    print(f"  Pending Queue    : {len(ct.request_queue)} requests")
    print(f"  Waiting Queue    : {len(ct.waiting_queue)} riders")
    print(f"  Rides Completed  : {ct.total_rides_completed}")
    print(f"  Shared Rides     : {ct.total_shared_rides}")

    if ct.waiting_queue:
        ct.print_separator()
        print("  Waiting riders:")
        for w in ct.waiting_queue:
            share_tag = " [share ok]" if w.wants_sharing else ""
            print(
                f"    #{w.request_id} {w.user_name} | "
                f"({w.source.x},{w.source.y}) -> ({w.destination.x},{w.destination.y})"
                f"{share_tag}"
            )

    ct.print_separator('=')


def show_menu() -> None:
    """Display the interactive command menu."""
    ct.print_separator('=')
    print("  YARIVO RIDE SYSTEM")
    ct.print_separator('=')
    print("  1. Submit a Ride Request")
    print("  2. Process Pending Queue (batch)")
    print("  3. Mark a Ride as Complete")
    print("  4. View Driver Status")
    print("  5. View Queue & Stats")
    print("  6. Add a New Driver")
    print("  7. View Active Rides")
    print("  8. Cancel a Waiting Request")
    print("  0. Exit")
    ct.print_separator()
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
    dispatch.submit_and_dispatch(name, sx, sy, dx, dy, share, True)


def menu_complete_ride() -> None:
    d_str = _next_token("\n  Driver ID (shown when ride was assigned): ")
    if not d_str:
        return
    try:
        driver_id = int(d_str)
    except ValueError:
        print("[ERROR] Driver ID must be an integer.")
        return
    driver.complete_ride(driver_id)


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

    driver.register_driver(driver_id, name, x, y)


def menu_cancel_request() -> None:
    req_str = _next_token("\n  Request ID to cancel: ")
    if not req_str:
        return
    try:
        req_id = int(req_str)
    except ValueError:
        print("[ERROR] Request ID must be an integer.")
        return
    dispatch.cancel_waiting_request(req_id)


def load_demo_data() -> None:
    """Seed initial demo drivers and ride requests."""
    print("\n[DEMO] Setting up 3 drivers and 5 ride requests...\n")

    driver.register_driver(101, "Ravi", 2, 3)
    driver.register_driver(102, "Priya", 8, 1)
    driver.register_driver(103, "Arjun", 5, 7)
    print()

    # Each request is submitted and immediately dispatched
    dispatch.submit_and_dispatch("Alice", 1, 2, 6, 8, True, False)
    dispatch.submit_and_dispatch("Bob", 2, 3, 6, 9, True, False)
    dispatch.submit_and_dispatch("Charlie", 9, 0, 3, 3, False, False)
    dispatch.submit_and_dispatch("Diana", 5, 6, 1, 1, True, False)
    dispatch.submit_and_dispatch("Eve", 10, 10, 0, 0, False, False)
    print()


def main() -> None:
    """Main program entry point."""
    # Zero out active rides array
    for i in range(ct.MAX_DRIVERS):
        ct.active_rides[i].in_use = False

    print()
    ct.print_separator('=')
    print("   YARIVO RIDE BOOKING & SHARING")
    ct.print_separator('=')

    load_demo_data()
    driver.display_driver_status()
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
            dispatch.process_pending_queue()
            driver.display_driver_status()
        elif choice == 3:
            menu_complete_ride()
        elif choice == 4:
            driver.display_driver_status()
        elif choice == 5:
            display_queue_status()
        elif choice == 6:
            menu_add_driver()
        elif choice == 7:
            driver.display_active_rides()
        elif choice == 8:
            menu_cancel_request()
        elif choice == 0:
            print("  Exiting. Goodbye!")
        else:
            print("  [ERROR] Invalid option.")

        print()


if __name__ == "__main__":
    main()
