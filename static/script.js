// ===================================
// AI PROJECT INTELLIGENCE DASHBOARD
// ===================================

let riskChart = null;
let healthChart = null;

let currentAnalysis = null;


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

    status.textContent = "Uploading and analyzing documents...";

    try {

        const response = await fetch("/upload", {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        if (!response.ok || result.error) {
            throw new Error(result.error || "Upload failed.");
        }

        status.textContent = result.message || "Documents uploaded successfully.";

        uploadedFiles.innerHTML = "";

        if (result.files && Array.isArray(result.files)) {
            uploadedFiles.innerHTML =
                "<strong>Uploaded Files:</strong><br>" +
                result.files.map(file => escapeHTML(file)).join("<br>");
        }

        // Get updated analysis
        await loadAnalysis();

        fileInput.value = "";

    } catch (error) {

        status.textContent = "Error: " + error.message;

    }

});


// ===================================
// LOAD PROJECT ANALYSIS
// ===================================

async function loadAnalysis() {

    try {

        const response = await fetch("/api/analyze");

        const data = await response.json();

        if (!response.ok || data.error) {
            throw new Error(data.error || "Analysis failed.");
        }

        currentAnalysis = data;

        updateDashboard(data);

    } catch (error) {

        console.error("Analysis Error:", error);

    }

}


// ===================================
// UPDATE DASHBOARD CARDS
// ===================================

function updateDashboard(data) {

    const health = data.health || {};
    const forecast = data.forecast || {};

    const risks = data.risks || [];
    const blockers = data.blockers || [];
    const actions = data.action_items || [];

    document.getElementById("healthScore").textContent =
        health.health_score ?? "--";

    document.getElementById("healthStatus").textContent =
        health.health_status || "Waiting for analysis";

    document.getElementById("riskCount").textContent =
        risks.length;

    document.getElementById("blockerCount").textContent =
        blockers.length;

    document.getElementById("actionCount").textContent =
        actions.length;

    document.getElementById("completionPercentage").textContent =
        (forecast.completion_percentage ?? 0) + "%";

    document.getElementById("deliveryStatus").textContent =
        forecast.delivery_status || "Waiting for analysis";

    document.getElementById("remainingDays").textContent =
        forecast.estimated_remaining_days ?? "--";

    updateRiskTable(risks);
    updateBlockerTable(blockers);
    updateActionTable(actions);

    updateCharts(risks, health);

}


// ===================================
// UPDATE RISK TABLE
// ===================================

function updateRiskTable(risks) {

    const table = document.getElementById("riskTable");

    if (!risks.length) {

        table.innerHTML =
            '<tr><td colspan="4">No risks identified.</td></tr>';

        return;
    }

    table.innerHTML = risks.map(risk => `

        <tr>
            <td>${escapeHTML(risk.risk)}</td>
            <td>${escapeHTML(risk.category)}</td>
            <td>${escapeHTML(risk.severity)}</td>
            <td>${escapeHTML(risk.recommendation)}</td>
        </tr>

    `).join("");

}


// ===================================
// UPDATE BLOCKER TABLE
// ===================================

function updateBlockerTable(blockers) {

    const table = document.getElementById("blockerTable");

    if (!blockers.length) {

        table.innerHTML =
            '<tr><td colspan="4">No blockers identified.</td></tr>';

        return;
    }

    table.innerHTML = blockers.map(item => `

        <tr>
            <td>${escapeHTML(item.blocker)}</td>
            <td>${escapeHTML(item.status)}</td>
            <td>${escapeHTML(item.priority)}</td>
            <td>${escapeHTML(item.suggested_action)}</td>
        </tr>

    `).join("");

}


// ===================================
// UPDATE ACTION ITEMS TABLE
// ===================================

function updateActionTable(actions) {

    const table = document.getElementById("actionTable");

    if (!actions.length) {

        table.innerHTML =
            '<tr><td colspan="4">No action items identified.</td></tr>';

        return;
    }

    table.innerHTML = actions.map(item => `

        <tr>
            <td>${escapeHTML(item.task)}</td>
            <td>${escapeHTML(item.status)}</td>
            <td>${escapeHTML(item.priority)}</td>
            <td>${escapeHTML(item.recommendation)}</td>
        </tr>

    `).join("");

}


// ===================================
// UPDATE CHARTS
// ===================================

function updateCharts(risks, health) {

    const categories = {};

    risks.forEach(risk => {

        const category = risk.category || "Other";

        categories[category] = (categories[category] || 0) + 1;

    });

    const riskLabels = Object.keys(categories);
    const riskValues = Object.values(categories);

    if (riskChart) {
        riskChart.destroy();
    }

    riskChart = new Chart(
        document.getElementById("riskChart"),
        {
            type: "doughnut",

            data: {
                labels: riskLabels.length ? riskLabels : ["No Risks"],
                datasets: [{
                    data: riskValues.length ? riskValues : [1],
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
        }
    );


    const score = Number(health.health_score || 0);

    if (healthChart) {
        healthChart.destroy();
    }

    healthChart = new Chart(
        document.getElementById("healthChart"),
        {
            type: "doughnut",

            data: {
                labels: ["Health Score", "Remaining"],
                datasets: [{
                    data: [score, 100 - score],
                    backgroundColor: ["#10b981", "#e2e8f0"],
                    borderWidth: 1
                }]
            },

            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: "70%"
            }
        }
    );

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
// INITIAL DASHBOARD LOAD
// ===================================

document.addEventListener("DOMContentLoaded", function() {

    loadAnalysis();

});
