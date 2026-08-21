async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

const searchInput = document.querySelector("#placeSearch");
const searchResults = document.querySelector("#searchResults");

searchInput?.addEventListener("input", async () => {
  const query = searchInput.value.trim();
  if (query.length < 2) {
    searchResults.innerHTML = "";
    searchResults.classList.remove("is-open");
    return;
  }

  const places = await fetchJson(`/api/search?q=${encodeURIComponent(query)}`);
  searchResults.innerHTML = places
    .map(
      (place) => `
        <button type="button" class="search-result" data-setup-url="${place.setup_url}">
          <strong>${place.name}</strong>
          <span>${place.city} · ${place.category} · ${place.rating.toFixed(1)}</span>
        </button>
      `
    )
    .join("");
  searchResults.classList.toggle("is-open", places.length > 0);
});

searchResults?.addEventListener("click", (event) => {
  const item = event.target.closest("[data-setup-url]");
  if (!item) return;
  window.location.href = item.dataset.setupUrl;
});

document.addEventListener("click", (event) => {
  if (!searchResults || !searchInput) return;
  if (event.target === searchInput || searchResults.contains(event.target)) return;
  searchResults.classList.remove("is-open");
});

function paintStars(picker, value, hoverValue = null) {
  picker.querySelectorAll("[data-star]").forEach((button) => {
    const star = Number(button.dataset.star);
    const filled = hoverValue !== null ? star <= hoverValue : star <= value;
    button.classList.toggle("is-active", filled);
    button.classList.toggle("is-hover", hoverValue !== null && star <= hoverValue);
  });
}

function initStarPickers() {
  document.querySelectorAll("[data-star-form]").forEach((form) => {
    const picker = form.querySelector("[data-star-picker]");
    const ratingInput = form.querySelector('input[name="rating"]');
    if (!picker || !ratingInput) return;

    let value = Number(picker.dataset.value || ratingInput.value || 5);
    paintStars(picker, value);

    picker.querySelectorAll("[data-star]").forEach((button) => {
      const star = Number(button.dataset.star);
      button.addEventListener("mouseenter", () => paintStars(picker, value, star));
      button.addEventListener("mouseleave", () => paintStars(picker, value));
      button.addEventListener("click", () => {
        value = star;
        ratingInput.value = String(star);
        picker.dataset.value = String(star);
        paintStars(picker, value);
      });
    });
  });
}

window.initTripMap = async function initTripMap() {
  const mapElement = document.querySelector("#map");
  if (!mapElement || !window.google) return;

  const data = await fetchJson(mapElement.dataset.mapUrl);
  renderRouteInsights(data);
  if (!data.points.length) return;

  const center = { lat: data.points[0].lat, lng: data.points[0].lng };
  const map = new google.maps.Map(mapElement, {
    center,
    zoom: 12,
    mapTypeControl: false,
    streetViewControl: false,
    fullscreenControl: false,
  });

  const bounds = new google.maps.LatLngBounds();
  const path = data.points.map((point) => {
    const position = { lat: point.lat, lng: point.lng };
    bounds.extend(position);
    new google.maps.Marker({
      position,
      map,
      label: String(point.order),
      title: point.name,
    });
    return position;
  });

  if (path.length > 1) {
    const directionsService = new google.maps.DirectionsService();
    const directionsRenderer = new google.maps.DirectionsRenderer({
      map,
      suppressMarkers: true,
      polylineOptions: {
        strokeColor: "#111318",
        strokeOpacity: 0.85,
        strokeWeight: 4,
      },
    });

    directionsService.route(
      {
        origin: path[0],
        destination: path[path.length - 1],
        waypoints: path.slice(1, -1).map((location) => ({ location, stopover: true })),
        travelMode: google.maps.TravelMode.DRIVING,
        optimizeWaypoints: false,
      },
      (result, status) => {
        if (status === "OK") {
          directionsRenderer.setDirections(result);
        } else {
          new google.maps.Polyline({
            path,
            geodesic: true,
            strokeColor: "#111318",
            strokeOpacity: 0.85,
            strokeWeight: 4,
            map,
          });
        }
      }
    );

    const distanceService = new google.maps.DistanceMatrixService();
    distanceService.getDistanceMatrix(
      {
        origins: path.slice(0, -1),
        destinations: path.slice(1),
        travelMode: google.maps.TravelMode.DRIVING,
      },
      (matrix, status) => {
        if (status !== "OK") return;
        const liveMinutes = matrix.rows.reduce((total, row, index) => {
          const element = row.elements[index];
          return total + (element?.duration?.value || 0) / 60;
        }, 0);
        const stats = document.querySelector("#routeStats");
        if (stats && liveMinutes > 0) {
          const shortest = data.shortest_path;
          stats.textContent =
            `Live travel estimate: ${Math.round(liveMinutes)} mins` +
            (shortest ? ` · Planned route about ${shortest.dijkstra_minutes} mins` : "");
        }
      }
    );
  }

  map.fitBounds(bounds);

  const stats = document.querySelector("#routeStats");
  if (stats && data.shortest_path) {
    stats.textContent = `Planned route about ${data.shortest_path.dijkstra_minutes} mins between first and last stop.`;
  }
};

document.addEventListener("DOMContentLoaded", async () => {
  initStarPickers();
  initCurrencyControls();
  if (setupForm) {
    updatePlanInsights();
  }

  const mapElement = document.querySelector("#map");
  if (!mapElement?.dataset.mapUrl) return;

  try {
    const data = await fetchJson(mapElement.dataset.mapUrl);
    renderRouteInsights(data);
    const stats = document.querySelector("#routeStats");
    if (stats && data.shortest_path) {
      stats.textContent = `Planned route about ${data.shortest_path.dijkstra_minutes} mins between first and last stop.`;
    }
  } catch (error) {
    const mstStat = document.querySelector("#mstStat");
    if (mstStat) mstStat.textContent = "Unavailable";
  }
});

function renderRouteInsights(data) {
  const mstStat = document.querySelector("#mstStat");
  const allPairsStat = document.querySelector("#allPairsStat");
  const kdTreeStat = document.querySelector("#kdTreeStat");

  if (mstStat && data.mst) {
    mstStat.textContent = `${data.mst.minutes} mins network`;
  }
  if (allPairsStat && data.all_pairs) {
    allPairsStat.textContent = `${data.all_pairs.average_minutes} mins avg`;
  }
  if (kdTreeStat) {
    kdTreeStat.textContent = data.alternatives?.length
      ? data.alternatives.map((place) => place.name).slice(0, 2).join(", ")
      : "No nearby alternatives";
  }
}

const setupForm = document.querySelector("#tripSetupForm");
const budgetSelect = document.querySelector("#budget_level");
const amountInput = document.querySelector("#budget_amount");
const currencySelect = document.querySelector("#currency");
const currencyPrefix = document.querySelector("#currencyPrefix");
const planPreviewStatus = document.querySelector("#planPreviewStatus");

function currentDefaults() {
  if (!setupForm) return {};
  const currency = currencySelect?.value || "USD";
  const raw =
    currency === "INR" ? setupForm.dataset.defaultsInr : setupForm.dataset.defaultsUsd;
  try {
    return JSON.parse(raw || "{}");
  } catch (error) {
    return {};
  }
}

function syncBudgetDefault(force = false) {
  if (!budgetSelect || !amountInput) return;
  const defaults = currentDefaults();
  const selected = budgetSelect.value;
  if (!selected || !defaults[selected]) return;
  if (force || !amountInput.value) {
    amountInput.value = defaults[selected];
  }
}

function initCurrencyControls() {
  if (!currencySelect) return;
  const applyPrefix = () => {
    if (currencyPrefix) {
      currencyPrefix.textContent = currencySelect.value === "INR" ? "₹" : "$";
    }
    syncBudgetDefault(true);
    updatePlanInsights();
  };
  currencySelect.addEventListener("change", applyPrefix);
  applyPrefix();
}

function missingPlanFields(payload) {
  const labels = {
    city: "city",
    mood_preference: "mood",
    budget_level: "budget level",
    budget_amount: "maximum spend",
    num_days: "days",
    num_people: "people",
  };
  return Object.entries(labels).filter(([key]) => !payload[key]).map(([, label]) => label);
}

budgetSelect?.addEventListener("change", () => {
  syncBudgetDefault(true);
  updatePlanInsights();
});

setupForm?.addEventListener("change", () => {
  updatePlanInsights();
});

setupForm?.addEventListener("input", () => {
  updatePlanInsights();
});

async function updatePlanInsights() {
  if (!setupForm) return;

  const form = new FormData(setupForm);
  const payload = {
    city: form.get("city"),
    mood_preference: form.get("mood"),
    budget_level: form.get("budget_level"),
    budget_amount: form.get("budget_amount"),
    currency: form.get("currency") || "INR",
    num_days: form.get("num_days"),
    num_people: form.get("num_people"),
  };

  const missing = missingPlanFields(payload);
  if (missing.length) {
    if (planPreviewStatus) {
      planPreviewStatus.textContent = `Still need: ${missing.join(", ")}`;
    }
    return;
  }

  if (planPreviewStatus) {
    planPreviewStatus.textContent = "Updating preview…";
  }

  try {
    const response = await fetch("/api/plan-insights", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(`Preview failed (${response.status})`);
    }
    const data = await response.json();

    const categoryEl = document.querySelector("#mlCategory");
    const categoryTitle = document.querySelector("#mlCategoryTitle");
    const costEl = document.querySelector("#mlCost");
    const heapTitle = document.querySelector("#heapTitle");
    const heapSummary = document.querySelector("#heapSummary");
    const budgetSummary = document.querySelector("#budgetSummary");
    const pairSummary = document.querySelector("#pairSummary");

    if (categoryTitle) categoryTitle.textContent = data.preferred_category || "Your vibe";
    if (categoryEl) {
      categoryEl.textContent = `${data.preferred_category} suits ${payload.mood_preference} in ${payload.city}`;
    }
    if (costEl) {
      costEl.textContent =
        data.estimated_total_trip_cost_formatted || `${Math.round(data.estimated_total_trip_cost)}`;
    }
    if (heapTitle && data.top_places?.[0]) {
      heapTitle.textContent = data.top_places[0].name;
    }
    if (heapSummary) {
      const names = data.top_places?.slice(0, 2).map((place) => place.name).join(", ");
      heapSummary.textContent = names || "No mood matches in this city";
    }
    if (budgetSummary) {
      budgetSummary.textContent = `${data.budget.affordable_count} of ${data.budget.total_count} fit`;
    }
    if (pairSummary) {
      const topCategory = data.categories?.[0];
      const pairHint = data.pairs?.best_pair
        ? `Try ${data.pairs.best_pair.left} + ${data.pairs.best_pair.right}`
        : `${data.pairs?.pair_count || 0} pairs under budget`;
      pairSummary.textContent = topCategory
        ? `${topCategory.category} (${topCategory.count} places) · ${pairHint}`
        : pairHint;
    }
    if (planPreviewStatus) {
      planPreviewStatus.textContent =
        data.cache === "hit" ? "Preview loaded from cache (instant)." : "Preview updated.";
    }
  } catch (error) {
    if (planPreviewStatus) {
      planPreviewStatus.textContent = "Could not load preview. Check that Flask is running.";
    }
    console.error(error);
  }
}
