#include "types.h"

bool register_driver(int id, string name, int x, int y) {
    if (driver_count >= MAX_DRIVERS) return false;
    if (find_driver_index_by_id(id) != -1) return false;
    driver_pool[driver_count++] = { id, name, {x, y}, DRIVER_IDLE, true };
    return true;
}

// Returns pool index for driver_id, or -1 if not found.
int find_driver_index_by_id(int driver_id) {
    for (int i = 0; i < driver_count; i++)
        if (driver_pool[i].is_registered && driver_pool[i].driver_id == driver_id)
            return i;
    return -1;
}

// Greedy nearest-driver search — O(n) scan using Manhattan distance.
int find_nearest_driver(Location src) {
    int best = -1, best_dist = INT_MAX;
    for (int i = 0; i < driver_count; i++) {
        if (!driver_pool[i].is_registered || driver_pool[i].state != DRIVER_IDLE) continue;
        int dist = manhattan_distance(driver_pool[i].location, src);
        if (dist < best_dist) { best_dist = dist; best = i; }
    }
    return best;
}

void mark_driver_on_ride(int pool_index) {
    driver_pool[pool_index].state = DRIVER_ON_RIDE;
}

// Active ride slot map — finds first free slot and stores ride info.
void record_active_ride(int driver_id, RideRequest req) {
    for (int i = 0; i < MAX_DRIVERS; i++)
        if (!active_rides[i].in_use) {
            active_rides[i] = { driver_id, req.request_id,
                                req.user_name, req.shared_with, true };
            return;
        }
}

void clear_active_ride(int driver_id) {
    for (int i = 0; i < MAX_DRIVERS; i++)
        if (active_rides[i].in_use && active_rides[i].driver_id == driver_id) {
            active_rides[i].in_use = false;
            return;
        }
}

string get_rider_for_driver(int driver_id) {
    for (int i = 0; i < MAX_DRIVERS; i++)
        if (active_rides[i].in_use && active_rides[i].driver_id == driver_id)
            return active_rides[i].rider_name;
    return "";
}

void complete_ride(int driver_id) {
    int idx = find_driver_index_by_id(driver_id);
    if (idx == -1 || driver_pool[idx].state != DRIVER_ON_RIDE) return;

    clear_active_ride(driver_id);
    driver_pool[idx].state = DRIVER_IDLE;
    total_rides_completed++;

    try_dispatch_waiting();   // assign waiting riders to this freed driver
}
