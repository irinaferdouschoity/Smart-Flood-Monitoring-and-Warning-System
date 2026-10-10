
"use strict";

const $ = (id) => document.getElementById(id);

let map = null;
let rainChart = null;
let tempChart = null;
let humChart = null;

// ---------- API helper ----------

async function api(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            ...(options.headers || {}),
            ...(options.body ? { "Content-Type": "application/json" } : {})
        }
    });

    const text = await response.text();
    let data;

    try {
        data = text ? JSON.parse(text) : null;
    } catch {
        throw new Error(`Invalid server response (${response.status}).`);
    }

    if (!response.ok) {
        throw new Error(
            data?.detail || `Request failed: ${response.status}`
        );
    }

    return data;
}

function status(message) {
    const element = $("status");
    if (element) element.textContent = message;
}

function showError(message) {
    console.error(message);
    status(`Error: ${message}`);
}

function numeric(value) {
    if (value === null || value === undefined || value === "") {
        return null;
    }

    const result = Number(value);
    return Number.isFinite(result) ? result : null;
}

function displayNumber(value, suffix = "") {
    const result = numeric(value);
    return result === null ? "--" : `${result.toFixed(2)}${suffix}`;
}

function selectedCityId() {
    return Number($("locations")?.value || 0);
}

// ---------- Graphs ----------

function drawChart(previous, canvasId, labels, values, title) {
    const canvas = $(canvasId);

    if (!canvas || typeof Chart === "undefined") {
        throw new Error(
            `Chart.js or canvas "${canvasId}" is unavailable.`
        );
    }

    if (previous) previous.destroy();

    return new Chart(canvas, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: title,
                data: values,
                borderWidth: 2,
                pointRadius: 2,
                tension: 0.2,
                spanGaps: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: {
                intersect: false,
                mode: "index"
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// ---------- Weather ----------

async function weather(id) {
    const records = await api(`/weather/${id}?limit=90`);

    if (!Array.isArray(records)) {
        throw new Error("Weather data is not in the expected format.");
    }

    // The API returns the observations oldest to newest.
    const labels = records.map(row =>
        String(row.observation_date ?? row.date ?? "")
    );

    rainChart = drawChart(
        rainChart,
        "rain",
        labels,
        records.map(row => numeric(row.precipitation)),
        "Rainfall (mm)"
    );

    tempChart = drawChart(
        tempChart,
        "temp",
        labels,
        records.map(row =>
            numeric(row.temperature_avg ?? row.temperature)
        ),
        "Temperature"
    );

    humChart = drawChart(
        humChart,
        "humidity",
        labels,
        records.map(row =>
            numeric(row.humidity_avg ?? row.humidity)
        ),
        "Humidity (%)"
    );

    const latest = records.length
        ? records[records.length - 1]
        : null;

    if ($("r24")) {
        $("r24").textContent = latest
            ? displayNumber(latest.precipitation, " mm")
            : "--";
    }

    const last7 = records.slice(-7);
    const rainValues = last7.map(row => numeric(row.precipitation));

    if ($("r7")) {
        $("r7").textContent = rainValues.some(value => value !== null)
            ? `${rainValues.reduce(
                (sum, value) => sum + (value ?? 0), 0
            ).toFixed(2)} mm`
            : "--";
    }
}

// ---------- Flood history ----------

async function history(id) {
    const records = await api(`/flood-history/${id}`);
    const container = $("history");

    if (!container) return;

    container.replaceChildren();

    if (!Array.isArray(records) || records.length === 0) {
        container.textContent = "No flood history available.";
        return;
    }

    const table = document.createElement("table");
    const header = document.createElement("tr");

    ["Date", "Severity", "Description"].forEach(text => {
        const cell = document.createElement("th");
        cell.textContent = text;
        header.appendChild(cell);
    });

    table.appendChild(header);

    records.forEach(record => {
        const row = document.createElement("tr");

        [
            record.event_date ?? "--",
            record.severity ?? "--",
            record.description ?? record.details ?? "--"
        ].forEach(value => {
            const cell = document.createElement("td");
            cell.textContent = String(value);
            row.appendChild(cell);
        });

        table.appendChild(row);
    });

    container.appendChild(table);
}

// ---------- Historical rainfall indicator ----------

async function loadRainfallIndicator(id) {
    const result = await api(`/rainfall-indicator/${id}`);

    if ($("rainfallIndicator")) {
        $("rainfallIndicator").textContent =
            result.rainfall_indicator ?? "--";
    }

    if ($("rainfallDetails")) {
        $("rainfallDetails").textContent =
            result.note
                ? `${result.note} Date: ${result.observation_date ?? "--"}`
                : `Date: ${result.observation_date ?? "--"}`;
    }
}

// ---------- Selected city ----------

async function selected() {
    const id = selectedCityId();

    if (!id) {
        status("Please select a location.");
        return;
    }

    status("Loading city data...");

    const results = await Promise.allSettled([
        weather(id),
        history(id),
        loadRainfallIndicator(id)
    ]);

    const failures = results
        .filter(result => result.status === "rejected")
        .map(result => result.reason?.message || "Unknown error");

    if (failures.length) {
        showError(failures.join(" | "));
        return;
    }

    if ($("risk")) $("risk").textContent = "--";
    if ($("prob")) $("prob").textContent = "--";

    status("City data loaded.");
}

// ---------- Load cities and map ----------

async function load() {
    status("Loading locations...");

    const locations = await api("/locations");

    if (!Array.isArray(locations)) {
        throw new Error("The locations API did not return a list.");
    }

    const select = $("locations");

    if (!select) {
        throw new Error('Missing HTML element: id="locations".');
    }

    select.replaceChildren();

    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Select a location";
    select.appendChild(placeholder);

    locations.forEach(location => {
        const option = document.createElement("option");
        option.value = String(location.location_id);
        option.textContent =
            `${location.location_name}, ${location.country}`;
        select.appendChild(option);
    });

    if (map) {
        map.eachLayer(layer => {
            if (layer instanceof L.CircleMarker) {
                map.removeLayer(layer);
            }
        });

        locations.forEach(location => {
            const latitude = numeric(location.latitude);
            const longitude = numeric(location.longitude);

            if (latitude === null || longitude === null) return;

            L.circleMarker([latitude, longitude], { radius: 6 })
                .addTo(map)
                .bindPopup(
                    `${location.location_name}, ${location.country}`
                );
        });
    }

    if (!locations.length) {
        status("No locations were returned by the API.");
        return;
    }

    select.value = String(locations[0].location_id);

    if (map) {
        const first = locations[0];
        const latitude = numeric(first.latitude);
        const longitude = numeric(first.longitude);

        if (latitude !== null && longitude !== null) {
            map.setView([latitude, longitude], 6);
        }
    }

    await selected();
}

// ---------- City-based Haor model prediction ----------

async function predict() {
    const id = selectedCityId();

    if (!id) {
        status("Please select a location.");
        return;
    }

    const button = $("predict");
    if (button) button.disabled = true;

    status("Running experimental Haor model with latest city weather...");

    try {
        const result = await api(
            `/city-haor-predict?location_id=${encodeURIComponent(id)}`,
            { method: "POST" }
        );

        const probability = Number(result.flood_probability);

        if (!Number.isFinite(probability)) {
            throw new Error("The API returned an invalid probability.");
        }

        if ($("risk")) $("risk").textContent = result.risk_level ?? "--";

        if ($("prob")) {
            $("prob").textContent =
                `${(probability * 100).toFixed(1)}%`;
        }

        status(
            `Experimental estimate for ${result.city}, based on weather ` +
            `dated ${result.weather_observation_date}.`
        );

        const resultBox = $("haor-result");

        if (resultBox) {
            resultBox.replaceChildren();

            const details = [
                ["Experimental Haor model result", true],
                [`City: ${result.city}`, false],
                [`Latest weather date: ${result.weather_observation_date}`, false],
                [`Model output: ${(probability * 100).toFixed(1)}%`, false],
                [`Model category: ${result.risk_level}`, false],
                [`Warning: ${result.warning ?? "Research estimate only."}`, false],
                [
                    "Unavailable live satellite/terrain features: " +
                    (result.missing_live_features || []).join(", "),
                    false
                ]
            ];

            details.forEach(([text, isHeading]) => {
                const element = document.createElement(
                    isHeading ? "h3" : "p"
                );
                element.textContent = text;
                resultBox.appendChild(element);
            });
        }
    } catch (error) {
        showError(`Prediction failed: ${error.message}`);
    } finally {
        if (button) button.disabled = false;
    }
}

// ---------- Refresh NASA data ----------

async function update() {
    const button = $("refresh");
    if (button) button.disabled = true;

    status("Updating NASA weather data...");

    try {
        const result = await api("/update-data", {
            method: "POST"
        });

        const failures = Array.isArray(result.results)
            ? result.results.filter(item => item.status === "error")
            : [];

        await load();

        if (failures.length) {
            status(
                `Update finished with ${failures.length} location error(s).`
            );
        } else {
            status("NASA data update completed.");
        }
    } catch (error) {
        showError(`Update failed: ${error.message}`);
    } finally {
        if (button) button.disabled = false;
    }
}

// ---------- Manual 14-feature Haor research model ----------

async function predictHaor(event) {
    event.preventDefault();

    const form = $("haor-form");
    const resultBox = $("haor-result");

    if (!form) return;

    const fields = [
        "VV", "VH", "vv_vh_ratio", "rainfall",
        "soil_moisture", "temp", "wind", "slope",
        "twi", "rain_24h", "ndwi", "upstream_vv",
        "rain_96h", "temp_anomaly"
    ];

    const features = {};

    for (const name of fields) {
        const input = form.elements.namedItem(name);

        if (!input || input.value.trim() === "") {
            if (resultBox) {
                resultBox.textContent = `Please enter ${name}.`;
            }
            return;
        }

        const value = Number(input.value);

        if (!Number.isFinite(value)) {
            if (resultBox) {
                resultBox.textContent = `${name} must be numeric.`;
            }
            return;
        }

        features[name] = value;
    }

    const button = $("haor-submit");
    if (button) button.disabled = true;

    if (resultBox) resultBox.textContent = "Running research model...";

    try {
        const result = await api("/haor-predict", {
            method: "POST",
            body: JSON.stringify({ features })
        });

        if (resultBox) {
            resultBox.replaceChildren();

            const heading = document.createElement("h3");
            heading.textContent = "Haor research model result";

            const probability = document.createElement("p");
            probability.textContent =
                `Model output: ${
                    (Number(result.flood_probability) * 100).toFixed(1)
                }%`;

            const level = document.createElement("p");
            level.textContent = `Model category: ${result.risk_level}`;

            const warning = document.createElement("p");
            warning.textContent = result.warning ?? "Experimental result.";

            resultBox.append(heading, probability, level, warning);
        }
    } catch (error) {
        if (resultBox) {
            resultBox.textContent = `Prediction failed: ${error.message}`;
        }
        showError(`Haor prediction failed: ${error.message}`);
    } finally {
        if (button) button.disabled = false;
    }
}

// ---------- Start dashboard ----------

document.addEventListener("DOMContentLoaded", async () => {
    try {
        if (typeof L === "undefined") {
            throw new Error(
                "Leaflet did not load. Check your internet connection."
            );
        }

        if (typeof Chart === "undefined") {
            throw new Error(
                "Chart.js did not load. Check your internet connection."
            );
        }

        map = L.map("map").setView([20, 0], 2);

        L.tileLayer(
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            { attribution: "© OpenStreetMap contributors" }
        ).addTo(map);

        $("locations")?.addEventListener("change", async () => {
            try {
                await selected();
            } catch (error) {
                showError(error.message);
            }
        });

        $("predict")?.addEventListener("click", predict);
        $("refresh")?.addEventListener("click", update);
        $("haor-form")?.addEventListener("submit", predictHaor);

        await load();
    } catch (error) {
        showError(`Dashboard loading failed: ${error.message}`);
    }
});
