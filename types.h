/*
 * types.h  —  Shared structs, constants, globals, and function prototypes.
 *
 *  DSA Concepts Used:
 *    - FIFO Queue          : request_queue, waiting_queue
 *    - Greedy Matching     : find_nearest_driver (Manhattan distance)
 *    - Ride-Share Heuristic: try_ride_share (threshold-based scan)
 */

#ifndef TYPES_H
#define TYPES_H

#include <iostream>
#include <string>
#include <queue>
#include <cmath>
#include <climits>
#include <iomanip>

using namespace std;

// ─────────────────────────────────────────────
//  Constants
// ─────────────────────────────────────────────
const int MAX_DRIVERS     = 20;
const int SHARE_THRESHOLD = 3;
const int DRIVER_IDLE     = 0;
const int DRIVER_ON_RIDE  = 1;

// ─────────────────────────────────────────────
//  Core Structs
// ─────────────────────────────────────────────

struct Location {
    int x, y;
};

struct RideRequest {
    int    request_id;
    string user_name;
    Location source;
    Location destination;
    bool   wants_sharing;
    bool   is_shared;
    string shared_with;
    int    assigned_driver_id;   // -1 = not yet assigned
};

struct Driver {
    int    driver_id;
    string name;
    Location location;
    int    state;                // DRIVER_IDLE or DRIVER_ON_RIDE
    bool   is_registered;
};

struct ActiveRide {
    int    driver_id;
    int    request_id;
    string rider_name;
    string co_rider;             // empty if solo ride
    bool   in_use;
};

// ─────────────────────────────────────────────
//  Global State  (defined in main.cpp)
// ─────────────────────────────────────────────
extern queue<RideRequest> request_queue;
extern queue<RideRequest> waiting_queue;
extern Driver             driver_pool[MAX_DRIVERS];
extern int                driver_count;
extern ActiveRide         active_rides[MAX_DRIVERS];
extern int                next_request_id;
extern int                total_rides_completed;
extern int                total_shared_rides;

// ─────────────────────────────────────────────
//  Inline Utilities
// ─────────────────────────────────────────────

inline int manhattan_distance(Location a, Location b) {
    return abs(a.x - b.x) + abs(a.y - b.y);
}

// ─────────────────────────────────────────────
//  Function Prototypes
// ─────────────────────────────────────────────

// driver.cpp
bool   register_driver(int id, string name, int x, int y);
int    find_driver_index_by_id(int driver_id);
int    find_nearest_driver(Location src);
void   mark_driver_on_ride(int pool_index);
void   record_active_ride(int driver_id, RideRequest req);
void   clear_active_ride(int driver_id);
string get_rider_for_driver(int driver_id);
void   complete_ride(int driver_id);

// dispatch.cpp
bool try_ride_share(RideRequest &new_req, RideRequest &matched_req);
void assign_driver_to_request(RideRequest req);
void try_dispatch_waiting();
void submit_and_dispatch(string user_name,
                         int src_x, int src_y,
                         int dst_x, int dst_y,
                         bool wants_sharing);
void process_pending_queue();
void cancel_waiting_request(int request_id);

// main.cpp
void load_demo_data();

#endif
