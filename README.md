# Mood-Based Smart Tourist Recommendation and Navigation System

Flask + SQLite project for mood-based tourist recommendation and itinerary planning.

## Current Build Status

- Project structure created.
- Feature 1 started: SQLAlchemy models for `User`, `Place`, `Trip`, and `Review`.
- Feature 1 auth implemented: signup, login, logout using Flask sessions.
- Feature 2 implemented: trip setup form with city, mood, budget, and number of days.
- Feature 3 implemented as standalone Python modules under `algorithms/`:
  - `knapsack.py` chooses places for the city, mood, budget, and time limit.
  - `tsp.py` orders selected places with Nearest Neighbor plus 2-opt.
  - `scheduler.py` assigns visits to valid opening-hour intervals.
  - `itinerary.py` chains the full `generate_itinerary(...)` pipeline.
- Web app flow implemented:
  - Dashboard for saved trips.
  - Trip setup form.
  - Generated itinerary detail page with saved stops and timings.
- Graph + Maps implemented:
  - Graph creation for selected places.
  - Dijkstra and A* shortest-path estimates.
  - Prim's MST for the minimum connected route network.
  - Floyd-Warshall for all-pairs shortest-path analysis.
  - KD-tree nearest-neighbour alternatives for nearby replacement ideas.
  - Google Maps route rendering when `GOOGLE_MAPS_API_KEY` is configured.
  - Distance Matrix live travel-time estimate when the key is configured.
- Live re-planning implemented:
  - Simulate a place issue from itinerary detail.
  - Priority Queue chooses the next-best replacement by mood score within remaining budget/time.
- ML endpoints implemented:
  - `POST /api/predict/category`
  - `POST /api/predict/cost`
  - `POST /api/plan-insights`
- Trie search implemented:
  - `GET /api/search?q=...`
- Extra DSA features implemented:
  - Heap ranking for top mood-matched places.
  - Binary search budget feasibility on sorted place costs.
  - Prim's MST route network.
  - Floyd-Warshall all-pairs route analysis.
  - KD-tree nearby alternative suggestions.
- Profile implemented:
  - My Trips, Favourites, My Reviews, Ratings, and Settings sections.
- UI upgraded:
  - Split landing page inspired by modern product-site layouts.
  - Claymorphism, glassmorphism, neumorphism, and soft paper-style cards.
  - Visible ML + DSA intelligence cards on trip setup.

## Folder Structure

```text
MoodBasedTouristGuide/
  app/                 Flask backend code
  algorithms/          DSA algorithms used by the itinerary engine
  data/                CSV datasets used by the app and ML models
  scripts/             Simple scripts for testing algorithms
  static/              CSS and later JavaScript files
  templates/           Jinja HTML pages
  run.py               Flask entry point
```

## Setup

1. Create a virtual environment and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env`.

3. Create the SQLite database tables:

   ```powershell
   flask init-db
   ```

4. Import the tourist destination dataset:
   
   ```powershell
   flask import-places
   ```

5. Run the app:

   ```powershell
   flask run
   ```

If port 5000 is already busy:

```powershell
flask run --port 5001
```

## Google Maps API Key

The itinerary page embeds a live Google Map and also offers **Open in Google Maps**.

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create/select a project and enable billing (Maps needs a billing account; free credits apply).
3. Enable these APIs:
   - Maps JavaScript API
   - Directions API
   - Distance Matrix API
   - Places API
4. Create an API key under **Credentials**.
5. Open `.env` and set:

   ```text
   GOOGLE_MAPS_API_KEY=your-real-key-here
   ```

6. Restart Flask (`Ctrl+C`, then `flask run`).

Until a real key is added, the itinerary page still shows route analytics and an **Open in Google Maps** link built from your stops.

## Currency (INR / USD)

On **New trip**, choose **₹ Indian Rupee** or **$ US Dollar**. Place costs in the dataset are stored in USD and converted for display using `INR_PER_USD` from `.env` (default `83.5`).

## Web App Flow

1. Sign up or log in.
2. Open **New trip**.
3. Choose city, mood, currency, budget level, maximum spend, and number of days.
4. Submit the form to generate an itinerary.
5. View live cost/mood insights before submitting.
6. Open the trip to favourite stops, open Google Maps, and leave ratings after marking complete.

## Extra DSA features

Already included beyond the core knapsack / TSP / scheduler pipeline:

- Trie + edit-distance fuzzy search in the navbar
- Heap top mood matches
- Binary-search budget feasibility
- Graph shortest paths (Dijkstra / A*), Prim MST, Floyd-Warshall
- KD-tree nearby alternatives
- Priority-queue live re-plan
- Union-Find nearby place clusters
- Sliding-window best mood stretch
- Hash-map category frequency
- Two-pointer budget pair suggestions

## Dataset Preprocessing

`flask import-places` reads `data/places.csv`, converts numeric fields, converts Yes/No values to booleans, and inserts or updates `Place` rows in SQLite.

The ML training dataset is stored at `data/trip_records.csv`. The app uses it to predict preferred category and estimated total trip cost. These predictions appear on the trip setup page and are saved with each generated trip.

## Algorithm Smoke Test

Run the standalone DSA pipeline without Flask or SQLite:

```powershell
python scripts/test_algorithms.py
```
