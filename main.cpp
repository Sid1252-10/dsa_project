/*
 * main.cpp  —  Global variable definitions, demo seed data, and main().
 */

#include "types.h"

// ─────────────────────────────────────────────
//  Global Variable Definitions
// ─────────────────────────────────────────────
queue<RideRequest> request_queue;
queue<RideRequest> waiting_queue;
Driver             driver_pool[MAX_DRIVERS];
int                driver_count        = 0;
ActiveRide         active_rides[MAX_DRIVERS];
int                next_request_id      = 1;
int                total_rides_completed = 0;
int                total_shared_rides    = 0;

// ─────────────────────────────────────────────
//  Demo Seed Data
// ─────────────────────────────────────────────
void load_demo_data() {
    register_driver(101, "Ravi",  2, 3);
    register_driver(102, "Priya", 8, 1);
    register_driver(103, "Arjun", 5, 7);

    submit_and_dispatch("Alice",   1, 2,  6, 8,  true);
    submit_and_dispatch("Bob",     2, 3,  6, 9,  true);
    submit_and_dispatch("Charlie", 9, 0,  3, 3,  false);
    submit_and_dispatch("Diana",   5, 6,  1, 1,  true);
    submit_and_dispatch("Eve",    10,10,  0, 0,  false);
}

// ─────────────────────────────────────────────
//  Main
// ─────────────────────────────────────────────
int main() {
    for (int i = 0; i < MAX_DRIVERS; i++)
        active_rides[i].in_use = false;

    load_demo_data();
    return 0;
}
