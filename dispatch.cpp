#include "types.h"

// ─── Algorithm 1: Ride-Share Scan ───────────────────────────────────────────
bool try_ride_share(RideRequest &new_req, RideRequest &matched_req) {
    if (!new_req.wants_sharing) return false;

    queue<RideRequest> temp;
    bool found = false;

    while (!waiting_queue.empty()) {
        RideRequest candidate = waiting_queue.front();
        waiting_queue.pop();

        if (!found && candidate.wants_sharing) {
            int dist = manhattan_distance(new_req.source,      candidate.source)
                     + manhattan_distance(new_req.destination, candidate.destination);
            if (dist <= SHARE_THRESHOLD) {
                matched_req = candidate;
                found = true;
                continue;   // don't re-queue — this ride is matched
            }
        }
        temp.push(candidate);
    }
    waiting_queue = temp;
    return found;
}

// Helper: mark both requests as shared with each other.
static void apply_share_labels(RideRequest &a, RideRequest &b) {
    a.is_shared = b.is_shared = true;
    a.shared_with = b.user_name;
    b.shared_with = a.user_name;
}

// ─── Algorithm 2: Driver Assignment ─────────────────────────────────────────
void assign_driver_to_request(RideRequest req) {
    int idx = find_nearest_driver(req.source);

    if (idx == -1) {
        waiting_queue.push(req);   // no driver — join FIFO waiting queue
        return;
    }

    req.assigned_driver_id = driver_pool[idx].driver_id;
    mark_driver_on_ride(idx);
    record_active_ride(driver_pool[idx].driver_id, req);
    if (req.is_shared) total_shared_rides++;

    driver_pool[idx].location = req.destination;  // driver moves to drop-off
}

// ─── Algorithm 3: Auto-dispatch Waiting Queue ───────────────────────────────
void try_dispatch_waiting() {
    queue<RideRequest> still_waiting;
    while (!waiting_queue.empty()) {
        RideRequest w = waiting_queue.front();
        waiting_queue.pop();
        if (find_nearest_driver(w.source) == -1)
            still_waiting.push(w);
        else
            assign_driver_to_request(w);
    }
    waiting_queue = still_waiting;
}

// ─── Entry Point: Submit a New Request ──────────────────────────────────────
void submit_and_dispatch(string user_name,
                         int src_x, int src_y,
                         int dst_x, int dst_y,
                         bool wants_sharing) {
    if (src_x == dst_x && src_y == dst_y) return;

    RideRequest req;
    req.request_id         = next_request_id++;
    req.user_name          = user_name;
    req.source             = { src_x, src_y };
    req.destination        = { dst_x, dst_y };
    req.wants_sharing      = wants_sharing;
    req.is_shared          = false;
    req.shared_with        = "";
    req.assigned_driver_id = -1;

    // Step 1: try sharing match from waiting queue
    RideRequest matched;
    if (try_ride_share(req, matched))
        apply_share_labels(req, matched);

    // Step 2: assign driver (or queue if none available)
    assign_driver_to_request(req);
}

// ─── Batch Process Pending Queue ────────────────────────────────────────────
void process_pending_queue() {
    while (!request_queue.empty()) {
        RideRequest req = request_queue.front();
        request_queue.pop();
        RideRequest matched;
        if (try_ride_share(req, matched))
            apply_share_labels(req, matched);
        assign_driver_to_request(req);
    }
}

// ─── Cancel a Waiting Request ────────────────────────────────────────────────
void cancel_waiting_request(int request_id) {
    queue<RideRequest> temp;
    while (!waiting_queue.empty()) {
        RideRequest w = waiting_queue.front();
        waiting_queue.pop();
        if (w.request_id != request_id)
            temp.push(w);
    }
    waiting_queue = temp;
}
