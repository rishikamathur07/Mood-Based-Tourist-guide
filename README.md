# Mood — Mood-Based Smart Tourist Recommendation and Navigation System

A complete college-project web application built with **Python Flask**, **SQLite with SQLAlchemy**, **Jinja2 templates**, **vanilla JavaScript**, and **Bootstrap 5**.

**Mood** helps travelers generate personalized, day-by-day itineraries matching how they want to feel (Culture, Relaxation, Nature, Adventure, Nightlife). The system solves itinerary scheduling using classical Data Structures & Algorithms (DSA) and Machine Learning (ML), with optional Google Maps integration and transparent local budgeting.

---

## Key Features

1. **User Authentication & Profiles**:
   - Secure sign-up, log-in, and log-out with password hashing (`werkzeug.security`) and Flask sessions.
   - Comprehensive profile page featuring **My Trips**, **Favourites** (hearted places), **My Reviews**, **Ratings** distribution chart, and **Settings** (display name updates).

2. **Personalized Trip Creation**:
   - Customizable trip planner selecting destination city, travel mood, budget level (Low, Medium, High), spending limit, number of days, number of travelers, currency (INR ₹ or USD $), travel start date, and optional starting landmark or hotel.
   - 52 supported global and Indian destinations (including **Delhi, Goa, Jaipur, Mumbai, Agra, Varanasi, Kochi, Bengaluru, Udaipur, Kolkata**, and international hubs).

3. **Intelligent Day-by-Day Itinerary Generation**:
   - Time-slotted stops honoring venue opening and closing hours, realistic visit durations, and city transit buffers.
   - Transparent local-trip cost breakdown clearly separated into **Attractions**, **Stay**, **Meals**, and **Local Transport**. Flights are intentionally excluded from the local calculation because live flight fares vary dynamically by date and airline.

4. **Live Re-Planning & Crowd Optimization**:
   - Travelers can mark any attraction **Unavailable / Closed** or **Too Crowded** directly from their itinerary.
   - A Priority Queue algorithm instantly suggests and inserts the optimal mood-matched replacement within the remaining budget and daily time window.
   - Crowd-aware scheduling allows moving busier venues to earlier morning slots before crowds build up.

5. **Dedicated Accommodation Guide**:
   - 5 to 10 reasonable, realistic hotels per supported city spanning Low, Medium, and High budget tiers.
   - Dedicated hotel directory (`/tools/hotels`) with filtering by city and budget tier.

6. **Restrained Editorial Travel UI**:
   - Atmospheric mountain travel background on landing, login, and signup pages with readable white/cream text sitting directly on the image (no split layout or side panels).
   - Warm paper surfaces, thin borders, sharp small-radius cards, clear typography hierarchy (Fraunces serif headings and Manrope sans-serif body), and zero visible DSA jargon in the customer-facing interface.

---

## Standalone Algorithms & College Viva Guide

All algorithmic modules reside under `/algorithms` as standalone, testable Python components with detailed in-code comments for college vivas.

| Algorithm | Module | Viva Concept & Purpose | Time Complexity |
| :--- | :--- | :--- | :--- |
| **0/1 Knapsack** | `algorithms/knapsack.py` | Multi-dimensional dynamic programming using two capacities (Monetary Budget and Tour Time) to select attractions that maximize total `mood_match_score` without item duplication. | $O(N \cdot B \cdot T)$ |
| **Nearest Neighbor + 2-opt** | `algorithms/tsp.py` | Traveling Salesperson Problem (TSP) optimization. Nearest Neighbor constructs an initial greedy tour from the starting location using Haversine distance; 2-opt iteratively uncrosses overlapping route edges to minimize transit distance. | Construction: $O(N^2)$, 2-opt: $O(N^2)$ per pass |
| **Greedy Interval Scheduling** | `algorithms/scheduler.py` | Earliest-feasible finish scheduling. Assigns visits to valid opening intervals, handles transit buffers between stops, and rolls over to the next day when daily window closes. | $O(N)$ |
| **Priority Queue Replanner** | `algorithms/replanner.py` | Min-heap (`heapq`) storing negated mood scores for live venue swaps. Extracts the highest mood-match candidate matching remaining time and cost constraints in $O(\log N)$ time, with optional crowd penalties. | $O(N \log N)$ build, $O(\log N)$ pop |
| **Trie (Prefix Tree)** | `algorithms/trie.py` | In-memory prefix tree indexing attraction names. Enables instant autocompletion in $O(L)$ time (proportional to prefix length), bypassing database disk scans. | $O(L)$ search |
| **Graph Algorithms** | `algorithms/graph.py` | Models places as vertices and travel time as edge weights. Implements **Dijkstra** and **A\*** (using Haversine straight-line heuristic), **Floyd-Warshall** all-pairs shortest paths, and **Prim's MST**. Supports Google Distance Matrix edge weights when configured. | Dijkstra: $O((V+E)\log V)$, Floyd-Warshall: $O(V^3)$, MST: $O(E\log V)$ |
| **Crowd-Aware Ordering** | `algorithms/crowd.py` | Priority queue that sorts high-crowd places into earlier morning visit windows before lines form. | $O(N \log N)$ |

---

## Machine Learning Integration

- **Place Category Prediction**: A Decision Tree Classifier trained on trip records predicts preferred place category (Historical, Religious, Beach, Nature, City, Adventure) from `city`, `days`, `people`, `mood`, and `budget`.
- **Trip Cost Estimation**: A Linear Regression model trained on trip records estimates total trip cost.
- **API Endpoints**:
  - `POST /api/predict/category`: returns JSON predicted category.
  - `POST /api/predict/cost`: returns JSON estimated cost converted to selected currency.
  - `POST /api/plan-insights`: returns live preview of budget feasibility and top matches.
- **Safe Fallback**: If `scikit-learn` or C-extensions are missing or restricted, the application automatically activates pure-Python dataset-backed fallback models (`CategoryFallbackModel` and `CostFallbackModel`).

---

## Google Maps Integration

- **Configured (`GOOGLE_MAPS_API_KEY` set in `.env`)**:
  - Renders interactive Google Map with stop markers and turn-by-turn polyline route directions (`google.maps.DirectionsService`).
  - Fetches live travel estimates (`google.maps.DistanceMatrixService`).
  - Queries Google Places API for real-time venue opening hours.
- **Unconfigured (No API key)**:
  - Generates a direct **"Open route in Google Maps"** link with origin, waypoints, and destination parameters.
  - Cleanly displays route directions and turn-by-turn guidance without JavaScript errors.
  - *Never hardcode or commit API keys into source control.*

### Configure a local Google Maps key

1. In Google Cloud Console, create or select a project and attach billing.
2. In **APIs & Services**, enable **Maps JavaScript API**, **Directions API**, **Places API**, and **Distance Matrix API**. The start-location lookup uses the Maps JavaScript geocoding service; enable **Geocoding API** as well if your Cloud project requires it.
3. Open **Credentials**, create an API key, and restrict it to these APIs. For local browser use, add these website restrictions:
   ```text
   http://127.0.0.1:5000/*
   http://localhost:5000/*
   ```
4. Create `.env` from `.env.example` if it does not already exist, then replace the placeholder:
   ```env
   GOOGLE_MAPS_API_KEY=your_actual_key_here
   ```
5. Restart Flask. On Trip Setup, type a start hotel or landmark and wait for the field hint to confirm it was found before generating the itinerary.

The embedded map, route, and live opening-hours check need this key. Without it, the itinerary still works and opens the route in Google Maps. Keep `.env` private and never push it to GitHub.

---

## Project Structure

```text
MoodBasedTouristGuide/
├── backend/                    # Python application code
│   ├── app/                    # Flask blueprints, models, services, and routes
│   ├── algorithms/             # Knapsack, TSP, graph, Trie, KD-Tree, and replanning modules
│   └── scripts/                # Algorithm, workflow, catalog, and tools test scripts
├── frontend/                   # Browser-facing files
│   ├── static/                 # CSS and JavaScript
│   └── templates/              # Jinja pages for auth, trips, profile, and tools
├── database/                   # Local data layer
│   ├── data/                   # Versioned CSV datasets
│   └── tourist_guide.sqlite3   # Local SQLite database, ignored by Git
├── .env.example                # Template for environment variables
├── requirements.txt            # Python dependencies
├── run.py                      # Application entry point
├── run_local.ps1               # One-command Windows PowerShell setup and run script
└── README.md                   # Project documentation
```

---

## Local Setup & Running

### Option 1: One-Command PowerShell Setup (Recommended on Windows)

Open PowerShell in the project directory:

```powershell
.\run_local.ps1 -Setup
```

This script automatically:
1. Creates the Python virtual environment in `.venv`.
2. Upgrades `pip` and installs all packages from `requirements.txt`.
3. Handles Windows AppLocker policy by enabling pure-Python SQLAlchemy fallback.
4. Copies `.env.example` to `.env` if missing.
5. Initializes the SQLite database (`flask init-db`) and imports the destination dataset (`flask import-places`).
6. Starts the Flask server on `http://127.0.0.1:5000`.

To start the server subsequently:
```powershell
.\run_local.ps1
```

### Option 2: Manual Setup

1. **Create and activate virtual environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. **Install requirements**:
   ```powershell
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   ```powershell
   Copy-Item .env.example .env
   ```
   *(Optional)* Add your Google Maps API key in `.env`:
   ```env
   GOOGLE_MAPS_API_KEY=your_actual_api_key_here
   ```

4. **Initialize Database & Import Places**:
   ```powershell
   python -m flask --app run init-db
   python -m flask --app run import-places
   ```

5. **Start Flask Server**:
   ```powershell
   python -m flask --app run run --port 5000
   ```
   Open your browser and navigate to `http://127.0.0.1:5000`.

---

## Running Test Suites

Run the regression and algorithm verification suites:

```powershell
# 1. Test standalone DSA algorithms (Knapsack, TSP, Scheduler, Priority Queue, Trie, Graph)
.\.venv\Scripts\python.exe backend\scripts\test_algorithms.py

# 2. Test full end-to-end user workflow (Signup, Trip creation, Budget, Replanning, Profile, ML APIs)
.\.venv\Scripts\python.exe backend\scripts\test_full_workflow.py

# 3. Test explore tools and hotel catalog
.\.venv\Scripts\python.exe backend\scripts\test_explore_tools.py
```

---

## GitHub Instructions

To push the project to GitHub:

1. **Initialize Git repository** (if not already initialized):
   ```powershell
   git init
   ```

2. **Check Status & Stage Files**:
   ```powershell
   git status
   git add .
   ```

3. **Commit Changes**:
   ```powershell
   git commit -m "Build complete Mood-Based Smart Tourist Recommendation and Navigation System"
   ```

4. **Push to Remote**:
   ```powershell
   git branch -M main
   git remote add origin https://github.com/<your-username>/MoodBasedTouristGuide.git
   git push -u origin main
   ```
   *(Note: Ensure your `.env` containing any live private keys remains untracked in `.gitignore`.)*
