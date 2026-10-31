# 🚖 Yarivo — Ride Booking & Sharing (DSA Project)

## Features
- Queue-based ride request handling (FIFO)
- Driver allocation using nearest distance
- Ride sharing support
- Active ride tracking

## Tech Stack
- Python / C++ (Backend logic)
- HTML + JavaScript (Frontend UI)

## How to Run

### One-Click Startup (Both Frontend & Backend):
```bash
# On Linux, macOS, or Windows (Git Bash):
chmod +x start.sh   # (first time only)
./start.sh
```
This script automatically:
1. Creates a Python virtual environment (`venv`).
2. Installs all dependencies from `requirements.txt`.
3. Starts the Web UI and API server at `http://localhost:5174` in the background.
4. Opens the passenger dashboard (including the live map) and launches the interactive CLI simulator.
5. Stops the background web server when you exit the CLI.

### Backend Only (Python):
```bash
# Run modular Python backend:
python main.py

# Or run standalone single-file backend:
python cab_system.py
```

### Backend (C++):
```bash
g++ -std=c++11 -o cab_system main.cpp driver.cpp dispatch.cpp
./cab_system
```

### Frontend / Web UI:
```bash
# Option A: Run with Node.js
cd web
npm install
npm run dev

# Option B: Run with Python server
python web/server/server.py
```

# 🚖 Yarivo — Queue-Based Ride Booking & Sharing System

A console-based cab booking simulator built in **C++** that demonstrates core **Data Structures & Algorithms** concepts — queues, greedy nearest-driver selection, and Manhattan distance geometry — in the context of a real-world ride-hailing problem.

This repo also includes a **web UI** (User view + Map + Driver view) with ride sharing + pricing to visualize and interact with a Punjab city-road network.

---

## 📌 Features

| Feature | Description |
|---|---|
| **Ride Request Submission** | Users submit rides with source/destination coordinates |
| **Nearest-Driver Dispatch** | Greedily assigns the closest idle driver using Manhattan distance |
| **Ride Sharing** | Matches two compatible riders (same direction, within threshold) into one cab |
| **Waiting Queue** | Queues riders when no driver is available; auto-dispatches on ride completion |
| **Batch Processing** | Process all pending requests at once |
| **Ride Cancellation** | Remove a waiting request before it gets dispatched |
| **Live Status Boards** | View driver states, active rides, and queue statistics in real time |
| **Demo Seed Data** | Auto-loads 3 drivers and 5 sample rides on startup |

---

## 🧠 DSA Concepts Used

- **Queue (STL `std::queue`)** — Models the request queue and waiting queue (FIFO dispatch order)
- **Arrays** — Fixed-size driver pool (`driver_pool[MAX_DRIVERS]`) and active ride tracker
- **Greedy Algorithm** — Always assigns the nearest idle driver to minimise pickup time
- **Manhattan Distance** — `|x₁−x₂| + |y₁−y₂|` used for all proximity calculations
- **Linear Search** — Driver lookup by ID and ride-share candidate scanning

---

## 📁 Project Structure

```
dsa_project/
├── cab_types.py / types.py  # (Python) Shared dataclasses, constants, globals, utilities
├── driver.py                # (Python) Driver registration, lookup, active ride tracking, completion
├── dispatch.py              # (Python) Ride-share matching, driver assignment, queue dispatch
├── main.py                  # (Python) Interactive menu loop, demo seed data, queue status
├── cab_system.py            # (Python) Standalone single-file simulator
├── types.h                  # (C++) Shared structs, constants, global externs, prototypes
├── main.cpp                 # (C++) Global variable definitions, interactive menu, main()
├── driver.cpp               # (C++) Driver registration, lookup, ride completion, dashboards
├── dispatch.cpp             # (C++) Ride-share matching, driver assignment, cancellation
├── cab_system.cpp           # (C++) (Legacy) single-file version of the simulator
├── web/                     # Web UI + API (Punjab map + user/driver panels)
│   ├── server/              # index.js (Node.js) & server.py (Python)
│   └── client/              # Frontend HTML, CSS, app.js
└── README.md
```

### File Responsibilities

#### `cab_types.py` / `types.py` & `types.h`
Defines:
- **Structs / Classes**: `Location`, `RideRequest`, `Driver`, `ActiveRide`
- **Constants**: `MAX_DRIVERS = 20`, `SHARE_THRESHOLD = 3`, `DRIVER_IDLE / DRIVER_ON_RIDE`
- **Globals**: `request_queue`, `waiting_queue`, `driver_pool`, `active_rides`, stats counters
- **Utilities**: `manhattan_distance()`, `print_separator()`

#### `driver.py` & `driver.cpp`
- `register_driver()` — Adds a new driver to the pool
- `find_nearest_driver()` — Greedy O(n) scan for the closest idle driver
- `complete_ride()` — Marks driver idle, increments stats, triggers waiting-queue dispatch
- `display_driver_status()` / `display_active_rides()` — Console dashboards

#### `dispatch.py` & `dispatch.cpp`
- `try_ride_share()` — Scans the waiting queue for a compatible share partner
- `assign_driver_to_request()` — Core assignment; pushes to waiting queue if no driver free
- `submit_and_dispatch()` — Full request lifecycle: validate → share-match → assign
- `process_pending_queue()` — Batch processes the `request_queue`
- `cancel_waiting_request()` — Removes a specific request from the waiting queue

#### `main.py` & `main.cpp`
- Global variable definitions / state initialization
- `display_queue_status()` — Queue sizes + aggregate stats
- `load_demo_data()` — Seeds 3 drivers and 5 ride requests for quick testing
- Interactive menu loop

---

## 🚀 Getting Started

### Prerequisites
- **Python**: Python 3.8+ (no third-party dependencies required for backend simulator or python web server)
- **C++ (optional)**: A C++11 (or later) compiler: `g++`, `clang++`, or MSVC

### Run with Python

```bash
# Modular Python version (driver.py, dispatch.py, main.py, cab_types.py)
python main.py

# Standalone single-file Python version (cab_system.py)
python cab_system.py
```

### Build & Run with C++

**Linux / macOS / WSL**
```bash
g++ -std=c++11 -o cab_system main.cpp driver.cpp dispatch.cpp
./cab_system
```

**Windows (MinGW / MSYS2)**
```bash
g++ -std=c++11 -o cab_system.exe main.cpp driver.cpp dispatch.cpp
cab_system.exe
```

**Windows (MSVC — Developer Command Prompt)**
```bash
cl /EHsc main.cpp driver.cpp dispatch.cpp /Fe:cab_system.exe
cab_system.exe
```

> `types.h` is included automatically; do **not** compile it separately.

---

## 🖥️ Web UI (User + Map + Driver)

The web UI implements your required layout and interactions:

- **Map (center)**: Punjab road network with major/minor cities connected by roads
- **User view (left)**:
  - Select current city + destination
  - Submit ride request
  - Enable sharing and browse matching rides
  - Sharing workflow: request share → rider in cab approves/declines
- **Driver view (right)**:
  - See pending requests and accept/decline
  - See route/path to take
  - Receive notifications when a share is approved (pickup/drop)

### Run the Web UI

```bash
cd web
npm install
npm run dev
```

Then open `http://localhost:5174`.

### Pricing rule (sharing)

If a ride is shared:
- **Each rider pays less** than a solo fare
- **Total collected is more** than a solo fare

---

## 🕹️ Using the Menu

On startup the system loads demo data (3 drivers, 5 rides) and prints the driver board and queue status. You are then presented with an interactive menu:

```
=======================================================
  YARIVO RIDE SYSTEM
=======================================================
  1. Submit a Ride Request
  2. Process Pending Queue (batch)
  3. Mark a Ride as Complete
  4. View Driver Status
  5. View Queue & Stats
  6. Add a New Driver
  7. View Active Rides
  8. Cancel a Waiting Request
  0. Exit
```

### Workflow Example

1. **Option 1** — Enter your name, source `(x y)`, destination `(x y)`, and whether you want ride sharing (`y/n`).  
   - If a driver is free, you are instantly assigned; the confirmation shows the **Driver ID** needed for step 3.  
   - If all drivers are busy, your request enters the **waiting queue** automatically.

2. **Option 3** — When the ride is physically finished, enter the Driver ID shown during booking. The driver goes back to `IDLE` and the system immediately tries to dispatch any waiting riders.

3. **Option 2** — Force-processes any requests left in the pending `request_queue` (batch mode).

4. **Option 8** — Cancel a waiting request before it is dispatched by entering its Request ID (visible in Option 5).

---

## 🔗 Ride Sharing Logic

Two riders are paired into the same cab if **all** of the following hold:

1. Both set `wants_sharing = YES`
2. `|src_A.x − src_B.x| + |src_A.y − src_B.y| + |dst_A.x − dst_B.x| + |dst_A.y − dst_B.y| ≤ SHARE_THRESHOLD (3)`

The new request scans the **waiting queue**; the first compatible candidate is removed and both rides are flagged `is_shared = true`. A single driver is then assigned to serve both passengers.

---

## 🗺️ Coordinate System

Locations are integer grid points `(x, y)`. All distances are **Manhattan** (city-block) distances. Drivers move to a ride's **destination** after each assignment, so their position updates between trips.

```
(0,0) ──── x ────►
  │
  y
  │
  ▼
```

---

## ⚙️ Configuration

Edit the constants in `types.h` to tune behaviour without changing any logic:

| Constant | Default | Effect |
|---|---|---|
| `MAX_DRIVERS` | `20` | Maximum drivers in the pool |
| `SHARE_THRESHOLD` | `3` | Max combined src+dst distance to allow ride sharing |

---

## 📊 Statistics Tracked

The system tracks across its lifetime:
- **Total rides completed** (`total_rides_completed`)
- **Total shared rides** (`total_shared_rides`)

These are printed whenever you view the Queue Status (Option 5).

---

## 📝 Limitations & Possible Extensions

| Limitation | Potential Extension |
|---|---|
| In-memory only; state lost on exit | File I/O or database persistence |
| Grid coordinates only | Real GPS coordinates + Haversine distance |
| Single-threaded | Multi-threaded async driver simulation |
| First-fit ride sharing | Optimal share matching (e.g., Hungarian algorithm) |
| No fare calculation | Dynamic pricing based on distance and sharing |

---

## 👤 Author

Developed as a **Data Structures & Algorithms** college project.  
Language: **C++11** | Paradigm: **Procedural / Multi-file**
