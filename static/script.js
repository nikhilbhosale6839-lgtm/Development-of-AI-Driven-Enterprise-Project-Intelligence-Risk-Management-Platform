
// ===================================
// AI PROJECT INTELLIGENCE DASHBOARD
// MILESTONE 2 - UPDATED SCRIPT
// ===================================

let riskChart = null;
let healthChart = null;
let currentAnalysis = null;


// ===================================
// SAFE HTML DISPLAY
// ===================================

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, function(character) {
        const entities = {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        };

        return entities[character];
    });
}


// ===================================
// UPLOAD PROJECT DOCUMENTS
// ===================================

document.getElementById("uploadForm").addEventListener("submit", async function(e) {

    e.preventDefault();

    const fileInput = document.getElementById("fileInput");
    const status = document.getElementById("uploadStatus");
    const uploadedFiles = document.getElementById("uploadedFiles");

    if (!fileInput.files.length) {
        status.textContent = "Please select project documents.";
        return;
    }

    const formData = new FormData();

    for (let file of fileInput.files) {
        formData.append("files", file);
    }

    status.textContent = "Uploading documents...";

    try {

        const response = await fetch("/upload", {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        if (!response.ok || result.error) {
            throw new Error(result.error || "Upload failed.");
        }

        status.textContent = result.message || "Upload successful.";

        uploadedFiles.innerHTML = "";

        if (Array.isArray(result.files)) {
            uploadedFiles.innerHTML =
                "<strong>Uploaded Files:</strong><br>" +
                result.files.map(file => escapeHTML(file)).join("<br>");
        }

        fileInput.value = "";

        status.textContent = "Documents uploaded. Analyzing project...";

        await loadAnalysis();

        status.textContent = "Project analysis completed.";

    } catch (error) {

        status.textContent = "Error: " + error.message;
        console.error(error);

    }

});


// ===================================
// LOAD PROJECT ANALYSIS
// ===================================

async function loadAnalysis() {

    try {

        const response = await fetch("/api/analyze");

        const data = await response.json();

        if (!response.ok || data.error || data.success === false) {
            throw new Error(data.error || data.message || "Analysis failed.");
        }

        currentAnalysis = data;

        console.log("PROJECT ANALYSIS:", data);

        updateDashboard(data);

        return data;

    } catch (error) {

        console.error("Analysis Error:", error);

        const status = document.getElementById("uploadStatus");

        if (status) {
            status.textContent = "Analysis Error: " + error.message;
        }

        return null;

    }

}


// ===================================
// UPDATE DASHBOARD
// ===================================

function updateDashboard(data) {

    const health = data.health || {};
    const forecast = data.forecast || {};

    const risks = Array.isArray(data.risks) ? data.risks : [];
    const blockers = Array.isArray(data.blockers) ? data.blockers : [];
    const actions = Array.isArray(data.action_items) ? data.action_items : [];

    // HEALTH SCORE

    document.getElementById("healthScore").textContent =
        health.health_score ?? "--";

    document.getElementById("healthStatus").textContent =
        health.health_status || "Waiting for analysis";


    // COUNTS

    document.getElementById("riskCount").textContent =
        risks.length;

    document.getElementById("blockerCount").textContent =
        blockers.length;

    document.getElementById("actionCount").textContent =
        actions.length;


    // DELIVERY FORECAST

    const completion = document.getElementById("completionPercentage");
    const delivery = document.getElementById("deliveryStatus");
    const remaining = document.getElementById("remainingDays");

    if (completion) {
        completion.textContent = "N/A";
    }

    if (delivery) {
        delivery.textContent =
            forecast.message || "Forecast analysis completed";
    }

    if (remaining) {
        remaining.textContent =
            forecast.tasks_analyzed ?? 0;
    }


    // UPDATE TABLES

    updateRiskTable(risks);

    updateBlockerTable(blockers);

    updateActionTable(actions);


    // UPDATE FORECAST TABLE

    updateForecastTable(forecast);


    // UPDATE CHARTS

    updateCharts(risks, health);

}


// ===================================
// RISK ANALYSIS TABLE
// ===================================

function updateRiskTable(risks) {

    const table = document.getElementById("riskTable");

    if (!table) return;

    if (!risks.length) {

        table.innerHTML =
            '<tr><td colspan="4">No risks identified in uploaded documents.</td></tr>';

        return;
    }

    table.innerHTML = risks.map(risk => `

        <tr>
            <td>${escapeHTML(risk.risk_type)}</td>

            <td>${escapeHTML(risk.evidence)}</td>

            <td>${escapeHTML(risk.severity)}</td>

            <td>${escapeHTML(risk.recommendation)}</td>
        </tr>

    `).join("");

}


// ===================================
// BLOCKER ANALYSIS TABLE
// ===================================

function updateBlockerTable(blockers) {

    const table = document.getElementById("blockerTable");

    if (!table) return;

    if (!blockers.length) {

        table.innerHTML =
            '<tr><td colspan="4">No blockers identified in uploaded documents.</td></tr>';

        return;
    }

    table.innerHTML = blockers.map(item => `

        <tr>
            <td>${escapeHTML(item.blocker_type)}</td>

            <td>${escapeHTML(item.description)}</td>

            <td>${escapeHTML(item.potential_impact)}</td>

            <td>${escapeHTML(item.recommended_action)}</td>
        </tr>

    `).join("");

}


// ===================================
// ACTION ITEMS TABLE
// ===================================

function updateActionTable(actions) {

    const table = document.getElementById("actionTable");

    if (!table) return;

    if (!actions.length) {

        table.innerHTML =
            '<tr><td colspan="4">No action items identified in uploaded documents.</td></tr>';

        return;
    }

    table.innerHTML = actions.map(item => `

        <tr>
            <td>${escapeHTML(item.action_item)}</td>

            <td>${escapeHTML(item.owner || "Not Assigned")}</td>

            <td>${escapeHTML(item.due_date || "Not Specified")}</td>

            <td>${escapeHTML(item.status || "Pending")}</td>
        </tr>

    `).join("");

}


// ===================================
// DELIVERY FORECAST TABLE
// ===================================

function updateForecastTable(forecast) {

    const table = document.getElementById("forecastTable");

    if (!table) return;

    const forecasts = Array.isArray(forecast.forecasts)
        ? forecast.forecasts
        : [];

    if (!forecasts.length) {

        table.innerHTML =
            '<tr><td colspan="5">No task forecast available. Add Task and Due Date details in your document.</td></tr>';

        return;
    }

    table.innerHTML = forecasts.map(item => `

        <tr>
            <td>${escapeHTML(item.task)}</td>

            <td>${escapeHTML(item.status)}</td>

            <td>${escapeHTML(item.due_date)}</td>

            <td>${escapeHTML(item.assessment)}</td>

            <td>${escapeHTML(item.recommendations)}</td>
        </tr>

    `).join("");

}


// ===================================
// UPDATE CHARTS
// ===================================

function updateCharts(risks, health) {

    const riskCanvas = document.getElementById("riskChart");
    const healthCanvas = document.getElementById("healthChart");

    if (typeof Chart === "undefined") {
        console.error("Chart.js is not loaded.");
        return;
    }

    if (riskCanvas) {

        const categories = {};

        risks.forEach(risk => {

            const category = risk.risk_type || "Other";

            categories[category] = (categories[category] || 0) + 1;

        });

        const labels = Object.keys(categories);
        const values = Object.values(categories);

        if (riskChart) {
            riskChart.destroy();
        }

        riskChart = new Chart(riskCanvas, {

            type: "doughnut",

            data: {
                labels: labels.length ? labels : ["No Risks"],

                datasets: [{
                    data: values.length ? values : [1],

                    backgroundColor: [
                        "#2563eb",
                        "#8b5cf6",
                        "#f59e0b",
                        "#ef4444",
                        "#10b981",
                        "#06b6d4"
                    ],

                    borderWidth: 1
                }]
            },

            options: {
                responsive: true,
                maintainAspectRatio: true
            }

        });

    }


    if (healthCanvas) {

        const score = Math.max(
            0,
            Math.min(100, Number(health.health_score ?? 0))
        );

        if (healthChart) {
            healthChart.destroy();
        }

        healthChart = new Chart(healthCanvas, {

            type: "doughnut",

            data: {

                labels: ["Health Score", "Remaining"],

                datasets: [{
                    data: [score, 100 - score],

                    backgroundColor: [
                        "#10b981",
                        "#e2e8f0"
                    ],

                    borderWidth: 1
                }]

            },

            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: "70%"
            }

        });

    }

}


// ===================================
// AI PROJECT ASSISTANT
// ===================================

document.getElementById("chatForm").addEventListener("submit", async function(e) {

    e.preventDefault();

    const input = document.getElementById("questionInput");
    const messages = document.getElementById("chatMessages");

    const question = input.value.trim();

    if (!question) return;

    messages.innerHTML += `
        <div class="user-message">
            ${escapeHTML(question)}
        </div>
    `;

    input.value = "";

    const loading = document.createElement("div");

    loading.className = "bot-message";
    loading.textContent = "AI is thinking...";

    messages.appendChild(loading);

    messages.scrollTop = messages.scrollHeight;

    try {

        const response = await fetch("/ask", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                question: question
            })

        });

        const result = await response.json();

        if (!response.ok || result.error) {
            throw new Error(result.error || "Unable to get answer.");
        }

        loading.textContent =
            result.answer || result.response || "No answer received.";

    } catch (error) {

        loading.textContent = "Error: " + error.message;

    }

    messages.scrollTop = messages.scrollHeight;

});


// ===================================
// INITIAL DASHBOARD LOAD
// ===================================

document.addEventListener("DOMContentLoaded", function() {

    loadAnalysis();

});

