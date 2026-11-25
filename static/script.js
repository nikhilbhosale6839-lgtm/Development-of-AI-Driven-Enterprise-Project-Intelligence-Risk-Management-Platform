"use strict";

/* ============================================================
   PROJECT RISK ADVISOR
   Complete Frontend JavaScript
   Compatible with Flask app.py
============================================================ */


/* ============================================================
   1. GLOBAL VARIABLES
============================================================ */

let dashboardData = {};
let uploadedFiles = [];
let riskChartInstance = null;
let healthChartInstance = null;
let analyticsRiskChartInstance = null;
let analyticsProgressChartInstance = null;

let isUploading = false;
let isAnalyzing = false;


/* ============================================================
   2. COMMON HELPERS
============================================================ */

function $(id) {
    return document.getElementById(id);
}


function setText(id, value) {
    const element = $(id);

    if (!element) return;

    const text = value === null || value === undefined
        ? ""
        : String(value);

    if (
        element.tagName === "INPUT" ||
        element.tagName === "TEXTAREA"
    ) {
        element.value = text;
    } else {
        element.textContent = text;
    }
}


function getArray(data, key) {
    if (!data || !Array.isArray(data[key])) {
        return [];
    }

    return data[key];
}


function escapeHTML(value) {
    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


function formatDate(value) {
    if (!value) return "-";

    const date = new Date(value);

    if (isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleString("en-IN");
}


function showStatus(id, message, type = "info") {
    const element = $(id);

    if (!element) return;

    element.textContent = message;

    element.className = "status-message " + type;
}


function showNotification(message, type = "success") {

    let notification = $("appNotification");

    if (!notification) {

        notification = document.createElement("div");

        notification.id = "appNotification";

        notification.style.position = "fixed";
        notification.style.top = "20px";
        notification.style.right = "20px";
        notification.style.zIndex = "99999";
        notification.style.padding = "14px 22px";
        notification.style.borderRadius = "10px";
        notification.style.color = "#ffffff";
        notification.style.fontSize = "14px";
        notification.style.fontWeight = "600";
        notification.style.boxShadow =
            "0 5px 20px rgba(0,0,0,0.15)";

        document.body.appendChild(notification);
    }

    notification.style.background =
        type === "error" ? "#dc3545" :
        type === "warning" ? "#f59e0b" :
        "#198754";

    notification.textContent = message;

    notification.style.display = "block";

    setTimeout(() => {
        notification.style.display = "none";
    }, 3500);
}


/* ============================================================
   3. API REQUEST HANDLER
============================================================ */

async function apiRequest(url, options = {}) {

    try {

        const response = await fetch(url, options);

        let result;

        try {
            result = await response.json();
        } catch {
            throw new Error("Server returned an invalid response.");
        }

        if (!response.ok) {

            throw new Error(
                result.error ||
                result.message ||
                "Request failed. HTTP " + response.status
            );
        }

        if (result.success === false) {

            throw new Error(
                result.error ||
                result.message ||
                "Operation failed."
            );
        }

        return result;

    } catch (error) {

        console.error("API Error:", error);

        throw error;
    }
}


/* ============================================================
   4. NAVIGATION
============================================================ */

function initializeNavigation() {

    const navLinks = document.querySelectorAll(".nav-link");

    navLinks.forEach(link => {

        link.addEventListener("click", function (event) {

            event.preventDefault();

            const target =
                this.dataset.page ||
                this.getAttribute("href");

            if (!target) return;

            const pageId = target.replace("#", "");

            navigateToPage(pageId);

        });

    });

}


function navigateToPage(pageId) {

    document.querySelectorAll(".page-section").forEach(section => {

        section.style.display = "none";

        section.classList.remove("active");

    });

    const targetPage = $(pageId);

    if (targetPage) {

        targetPage.style.display = "block";

        targetPage.classList.add("active");

    }

    document.querySelectorAll(".nav-link").forEach(link => {

        link.classList.remove("active");

        const target =
            link.dataset.page ||
            link.getAttribute("href");

        if (
            target === pageId ||
            target === "#" + pageId
        ) {
            link.classList.add("active");
        }

    });

    const title = pageId
        .replace(/([A-Z])/g, " $1")
        .replace(/^./, char => char.toUpperCase());

    setText("pageTitle", title);
    setText("headerHeading", title);

}


window.navigateToPage = navigateToPage;


/* ============================================================
   5. CURRENT DATE
============================================================ */

function initializeDate() {

    const dateElement = $("currentDate");

    if (!dateElement) return;

    dateElement.textContent =
        new Date().toLocaleDateString("en-IN", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric"
        });

}


/* ============================================================
   6. FILE UPLOAD INITIALIZATION
============================================================ */

function initializeFileUpload() {

    const fileInput = $("fileInput");

    const uploadForm = $("uploadForm");

    if (fileInput) {

        fileInput.addEventListener("change", function () {

            uploadedFiles = Array.from(this.files || []);

            displaySelectedFiles();

        });

    }

    if (uploadForm) {

        uploadForm.addEventListener("submit", function (event) {

            event.preventDefault();

            uploadDocuments();

        });

    }

}


function displaySelectedFiles() {

    const container = $("selectedFiles");

    if (!container) return;

    if (!uploadedFiles.length) {

        container.innerHTML = "";

        return;
    }

    container.innerHTML = uploadedFiles.map(file => {

        return `
            <div class="selected-file-item">
                <span>
                    <i class="fas fa-file"></i>
                    ${escapeHTML(file.name)}
                </span>

                <span>
                    ${(file.size / 1024).toFixed(1)} KB
                </span>
            </div>
        `;

    }).join("");

}


/* ============================================================
   7. DOCUMENT UPLOAD
============================================================ */

async function uploadDocuments() {

    if (isUploading) return;

    const fileInput = $("fileInput");

    if (!fileInput || !fileInput.files.length) {

        showNotification(
            "Please select documents before uploading.",
            "warning"
        );

        return;
    }

    isUploading = true;

    const formData = new FormData();

    Array.from(fileInput.files).forEach(file => {

        formData.append("files", file);

    });

    const uploadButton =
        document.querySelector('[onclick="uploadDocuments()"]') ||
        $("uploadButton");

    if (uploadButton) {

        uploadButton.disabled = true;

        uploadButton.textContent = "Uploading...";

    }

    showStatus(
        "uploadStatus",
        "Uploading documents...",
        "info"
    );

    try {

        const result = await apiRequest("/upload", {

            method: "POST",

            body: formData

        });

        showStatus(
            "uploadStatus",
            result.message || "Documents uploaded successfully.",
            "success"
        );

        showNotification(
            "Documents uploaded successfully."
        );

        fileInput.value = "";

        uploadedFiles = [];

        displaySelectedFiles();

        await refreshDashboard();

    } catch (error) {

        showStatus(
            "uploadStatus",
            error.message,
            "error"
        );

        showNotification(
            error.message,
            "error"
        );

    } finally {

        isUploading = false;

        if (uploadButton) {

            uploadButton.disabled = false;

            uploadButton.textContent = "Upload Documents";

        }

    }

}


window.uploadDocuments = uploadDocuments;


/* ============================================================
   8. ANALYZE PROJECT
============================================================ */

async function analyzeProject() {

    if (isAnalyzing) return;

    isAnalyzing = true;

    const analyzeButton =
        document.querySelector('[onclick="analyzeProject()"]') ||
        $("analyzeButton");

    if (analyzeButton) {

        analyzeButton.disabled = true;

        analyzeButton.textContent = "Analyzing Project...";

    }

    showNotification(
        "Project analysis started.",
        "info"
    );

    showStatus(
        "analysisStatus",
        "Analysis in progress...",
        "info"
    );

    try {

        const result = await apiRequest("/api/analyze", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({})

        });

        dashboardData = result.data || result;

        showNotification(
            result.message || "Project analysis completed."
        );

        showStatus(
            "analysisStatus",
            "Analysis Completed",
            "success"
        );

        await refreshDashboard();

        navigateToPage("dashboard");

    } catch (error) {

        console.error("Analysis Error:", error);

        showNotification(
            error.message,
            "error"
        );

        showStatus(
            "analysisStatus",
            error.message,
            "error"
        );

    } finally {

        isAnalyzing = false;

        if (analyzeButton) {

            analyzeButton.disabled = false;

            analyzeButton.textContent = "Analyze Project";

        }

    }

}


window.analyzeProject = analyzeProject;


/* ============================================================
   9. REFRESH DASHBOARD
============================================================ */

async function refreshDashboard() {

    try {

        const result = await apiRequest("/api/dashboard");

        dashboardData = result.data || result;

        updateDashboard(dashboardData);

        updateAnalytics(dashboardData);

        updateRiskTable(
            getArray(dashboardData, "risks")
        );

        updateRiskRegister(
            getArray(dashboardData, "risks")
        );

        updateBlockerTable(
            getArray(dashboardData, "blockers")
        );

        updateActionTable(
            getArray(dashboardData, "actions")
        );

        updateForecast(dashboardData.forecast || {});

        updateDocumentation(dashboardData);

        updateUploadedFiles(dashboardData);

        updateUserStories(
            getArray(dashboardData, "user_stories")
        );

    } catch (error) {

        console.error("Dashboard Refresh Error:", error);

    }

}


window.refreshDashboard = refreshDashboard;


/* ============================================================
   10. MAIN DASHBOARD
============================================================ */

function updateDashboard(data) {

    if (!data) return;

    const health = data.health || {};

    const risks = getArray(data, "risks");

    const blockers = getArray(data, "blockers");

    const actions = getArray(data, "actions");

    const inScope = getArray(data, "in_scope");

    const outOfScope = getArray(data, "out_of_scope");

    const deliverables = getArray(data, "deliverables");

    const healthScore = Number(health.score || 0);

    setText(
        "healthScore",
        healthScore + "%"
    );

    setText(
        "healthStatus",
        health.status || "Not Analyzed"
    );

    setText(
        "riskCount",
        risks.length
    );

    setText(
        "blockerCount",
        blockers.length
    );

    setText(
        "actionCount",
        actions.length
    );

    setText(
        "dashboardInScope",
        inScope.join("\n") || "No scope identified."
    );

    setText(
        "dashboardOutOfScope",
        outOfScope.join("\n") || "No out-of-scope items."
    );

    setText(
        "dashboardDeliverables",
        deliverables.join("\n") || "No deliverables identified."
    );

    const progress = Number(
        data.progress?.percentage ?? 0
    );

    setText(
        "projectProgress",
        progress + "%"
    );

    setText(
        "progressPercentage",
        progress + "%"
    );

    setText(
        "progressStatus",
        data.progress?.status || "Not Started"
    );

    const progressBar = $("progressBar");

    if (progressBar) {

        progressBar.style.width =
            Math.max(0, Math.min(100, progress)) + "%";

    }

    setText(
        "sessionId",
        data.session_id || "-"
    );

    setText(
        "documentCount",
        data.document_summary?.total_documents ??
        data.documents?.length ??
        data.uploaded_files?.length ??
        0
    );

    setText(
        "analysisStatus",
        data.analysis_status || "Waiting"
    );

    setText(
        "lastUpdated",
        formatDate(data.analyzed_at)
    );

    renderCharts(data);

}


/* ============================================================
   11. ANALYTICS
============================================================ */

function updateAnalytics(data) {

    if (!data) return;

    const risks = getArray(data, "risks");

    const blockers = getArray(data, "blockers");

    const actions = getArray(data, "actions");

    const forecast = data.forecast || {};

    setText(
        "analyticsRiskCount",
        risks.length
    );

    setText(
        "analyticsBlockerCount",
        blockers.length
    );

    setText(
        "analyticsActionCount",
        actions.length
    );

    setText(
        "analyticsHealthScore",
        (data.health?.score || 0) + "%"
    );

    const progress = Number(
        data.progress?.percentage || 0
    );

    setText(
        "analyticsProgress",
        progress + "%"
    );

    renderCharts(data);

}


/* ============================================================
   12. CHARTS
============================================================ */

function createChart(canvasId, type, labels, values, label) {

    const canvas = $(canvasId);

    if (!canvas || typeof Chart === "undefined") {
        return null;
    }

    return new Chart(canvas, {

        type: type,

        data: {

            labels: labels,

            datasets: [{

                label: label,

                data: values,

                borderWidth: 2,

                tension: 0.3,

                fill: type === "line"

            }]

        },

        options: {

            responsive: true,

            maintainAspectRatio: false,

            plugins: {

                legend: {
                    display: true
                }

            }

        }

    });

}


function renderCharts(data) {

    const risks = getArray(data, "risks");

    const severityCounts = {
        High: 0,
        Medium: 0,
        Low: 0
    };

    risks.forEach(risk => {

        const severity =
            String(risk.severity || "Low").toLowerCase();

        if (severity === "high" || severity === "critical") {

            severityCounts.High++;

        } else if (severity === "medium") {

            severityCounts.Medium++;

        } else {

            severityCounts.Low++;

        }

    });

    const healthScore =
        Number(data.health?.score || 0);

    const progress =
        Number(data.progress?.percentage || 0);


    if (riskChartInstance) {

        riskChartInstance.destroy();

        riskChartInstance = null;

    }

    if (healthChartInstance) {

        healthChartInstance.destroy();

        healthChartInstance = null;

    }

    if (analyticsRiskChartInstance) {

        analyticsRiskChartInstance.destroy();

        analyticsRiskChartInstance = null;

    }

    if (analyticsProgressChartInstance) {

        analyticsProgressChartInstance.destroy();

        analyticsProgressChartInstance = null;

    }


    riskChartInstance = createChart(
        "riskChart",
        "doughnut",
        ["High", "Medium", "Low"],
        [
            severityCounts.High,
            severityCounts.Medium,
            severityCounts.Low
        ],
        "Risk Severity"
    );


    healthChartInstance = createChart(
        "healthChart",
        "bar",
        ["Health Score", "Progress"],
        [healthScore, progress],
        "Project Status"
    );


    analyticsRiskChartInstance = createChart(
        "analyticsRiskChart",
        "pie",
        ["High", "Medium", "Low"],
        [
            severityCounts.High,
            severityCounts.Medium,
            severityCounts.Low
        ],
        "Risk Distribution"
    );


    analyticsProgressChartInstance = createChart(
        "analyticsProgressChart",
        "bar",
        ["Health Score", "Progress"],
        [healthScore, progress],
        "Project Metrics"
    );

}


/* ============================================================
   13. RISK TABLE
============================================================ */

function updateRiskTable(risks) {

    const tableBody = $("riskTableBody");

    if (!tableBody) return;

    if (!risks.length) {

        tableBody.innerHTML = `
            <tr>
                <td colspan="7">
                    No risks identified yet.
                </td>
            </tr>
        `;

        return;
    }

    tableBody.innerHTML = risks.map((risk, index) => {

        return `

            <tr>

                <td>${escapeHTML(risk.id || index + 1)}</td>

                <td>
                    ${escapeHTML(risk.title || "Untitled Risk")}
                </td>

                <td>
                    ${escapeHTML(risk.description || "-")}
                </td>

                <td>
                    <span class="severity-badge ${escapeHTML(
                        String(risk.severity || "Low").toLowerCase()
                    )}">
                        ${escapeHTML(risk.severity || "Low")}
                    </span>
                </td>

                <td>
                    ${escapeHTML(risk.status || "Open")}
                </td>

                <td>
                    ${escapeHTML(risk.mitigation || "-")}
                </td>

            </tr>

        `;

    }).join("");

}


/* ============================================================
   14. RISK REGISTER
============================================================ */

function updateRiskRegister(risks) {

    const tableBody = $("riskRegisterBody");

    if (!tableBody) return;

    if (!risks.length) {

        tableBody.innerHTML = `
            <tr>
                <td colspan="6">
                    No risk register records available.
                </td>
            </tr>
        `;

        return;
    }

    tableBody.innerHTML = risks.map((risk, index) => {

        return `

            <tr>

                <td>${escapeHTML(risk.id || index + 1)}</td>

                <td>${escapeHTML(risk.title || "-")}</td>

                <td>${escapeHTML(risk.category || "-")}</td>

                <td>${escapeHTML(risk.severity || "-")}</td>

                <td>${escapeHTML(risk.status || "Open")}</td>

                <td>${escapeHTML(risk.mitigation || "-")}</td>

            </tr>

        `;

    }).join("");

}


/* ============================================================
   15. BLOCKER TABLE
============================================================ */

function updateBlockerTable(blockers) {

    const tableBody = $("blockerTableBody");

    if (!tableBody) return;

    if (!blockers.length) {

        tableBody.innerHTML = `
            <tr>
                <td colspan="7">
                    No blockers identified.
                </td>
            </tr>
        `;

        return;
    }

    tableBody.innerHTML = blockers.map((blocker, index) => {

        return `

            <tr>

                <td>${escapeHTML(blocker.id || index + 1)}</td>

                <td>${escapeHTML(blocker.title || "-")}</td>

                <td>${escapeHTML(blocker.description || "-")}</td>

                <td>${escapeHTML(blocker.severity || "-")}</td>

                <td>${escapeHTML(blocker.owner || "-")}</td>

                <td>${escapeHTML(blocker.status || "Open")}</td>

                <td>${escapeHTML(blocker.resolution || "-")}</td>

            </tr>

        `;

    }).join("");

}


/* ============================================================
   16. ACTION ITEMS TABLE
============================================================ */

function updateActionTable(actions) {

    const tableBody = $("actionTableBody");

    if (!tableBody) return;

    if (!actions.length) {

        tableBody.innerHTML = `
            <tr>
                <td colspan="7">
                    No action items available.
                </td>
            </tr>
        `;

        return;
    }

    tableBody.innerHTML = actions.map((action, index) => {

        return `

            <tr>

                <td>${escapeHTML(action.id || index + 1)}</td>

                <td>${escapeHTML(action.title || "-")}</td>

                <td>${escapeHTML(action.description || "-")}</td>

                <td>${escapeHTML(action.owner || "-")}</td>

                <td>${escapeHTML(action.priority || "-")}</td>

                <td>${escapeHTML(action.status || "Pending")}</td>

                <td>${escapeHTML(action.due_date || "-")}</td>

            </tr>

        `;

    }).join("");

}


/* ============================================================
   17. PROJECT FORECAST
============================================================ */

function updateForecast(forecast) {

    if (!forecast) return;

    setText(
        "forecastStatus",
        forecast.delivery_status || "Not Available"
    );

    setText(
        "forecastPrediction",
        forecast.prediction || "No prediction available."
    );

    setText(
        "forecastCompletion",
        (forecast.completion_rate || 0) + "%"
    );

    setText(
        "completedActions",
        forecast.completed_actions || 0
    );

    setText(
        "pendingActionCount",
        forecast.pending_actions?.length || 0
    );

    setText(
        "forecastHighRisks",
        forecast.high_risks || 0
    );

    setText(
        "forecastMediumRisks",
        forecast.medium_risks || 0
    );

    setText(
        "forecastBlockers",
        forecast.blockers || 0
    );


    const recommendations =
        Array.isArray(forecast.recommendations)
            ? forecast.recommendations
            : [];

    const recommendationElement = $("forecastRecommendations");

    if (recommendationElement) {

        recommendationElement.innerHTML = recommendations.length

            ? recommendations.map(item => `
                <li>${escapeHTML(item)}</li>
            `).join("")

            : "<li>No recommendations available.</li>";

    }


    const pendingActions =
        Array.isArray(forecast.pending_actions)
            ? forecast.pending_actions
            : [];

    const forecastTable = $("forecastTableBody");

    if (forecastTable) {

        if (!pendingActions.length) {

            forecastTable.innerHTML = `
                <tr>
                    <td colspan="4">
                        No pending actions.
                    </td>
                </tr>
            `;

        } else {

            forecastTable.innerHTML = pendingActions.map(
                (action, index) => {

                    return `

                        <tr>

                            <td>
                                ${escapeHTML(action.id || index + 1)}
                            </td>

                            <td>
                                ${escapeHTML(action.title || "-")}
                            </td>

                            <td>
                                ${escapeHTML(action.owner || "-")}
                            </td>

                            <td>
                                ${escapeHTML(action.status || "Pending")}
                            </td>

                        </tr>

                    `;

                }
            ).join("");

        }

    }

}


/* ============================================================
   18. DOCUMENTATION
============================================================ */

function updateDocumentation(data) {

    if (!data) return;

    const scope = getArray(data, "in_scope");

    const outOfScope = getArray(data, "out_of_scope");

    const deliverables = getArray(data, "deliverables");

    const risks = getArray(data, "risks");

    const blockers = getArray(data, "blockers");

    const actions = getArray(data, "actions");


    setText(
        "documentationInScope",
        scope.join("\n") || "No scope information available."
    );

    setText(
        "documentationOutOfScope",
        outOfScope.join("\n") || "No out-of-scope information available."
    );

    setText(
        "documentationDeliverables",
        deliverables.join("\n") || "No deliverables available."
    );

    setText(
        "documentationRiskCount",
        risks.length
    );

    setText(
        "documentationBlockerCount",
        blockers.length
    );

    setText(
        "documentationActionCount",
        actions.length
    );

    setText(
        "documentationSummary",
        data.summary ||
        data.scope?.summary ||
        "Project documentation analysis is available after document processing."
    );

}


/* ============================================================
   19. UPLOADED DOCUMENTS
============================================================ */

function updateUploadedFiles(data) {

    const container = $("uploadedFiles");

    if (!container) return;

    let documents = [];

    if (Array.isArray(data.documents)) {

        documents = data.documents;

    } else if (Array.isArray(data.uploaded_files)) {

        documents = data.uploaded_files;

    } else if (Array.isArray(data.document_summary?.documents)) {

        documents = data.document_summary.documents;

    }

    if (!documents.length) {

        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-folder-open"></i>
                <p>No documents uploaded yet.</p>
            </div>
        `;

        return;
    }

    container.innerHTML = documents.map((document, index) => {

        const name =
            typeof document === "string"
                ? document
                : document.filename ||
                  document.name ||
                  document.original_filename ||
                  "Document " + (index + 1);

        return `

            <div class="uploaded-file-card">

                <div class="file-icon">
                    <i class="fas fa-file-alt"></i>
                </div>

                <div class="file-info">

                    <h4>${escapeHTML(name)}</h4>

                    <small>
                        ${escapeHTML(
                            typeof document === "object"
                                ? document.status || "Uploaded"
                                : "Uploaded"
                        )}
                    </small>

                </div>

            </div>

        `;

    }).join("");

}


/* ============================================================
   20. USER STORY GENERATION
============================================================ */

async function generateUserStory() {

    const requirementInput = $("requirementInput");

    if (!requirementInput) {

        showNotification(
            "Requirement input field not found.",
            "error"
        );

        return;
    }

    const requirement = requirementInput.value.trim();

    if (!requirement) {

        showNotification(
            "Please enter a requirement.",
            "warning"
        );

        return;
    }

    const button = $("generateStoryButton");

    if (button) {

        button.disabled = true;

        button.textContent = "Generating...";

    }

    showStatus(
        "storyStatus",
        "Generating user story...",
        "info"
    );

    try {

        const result = await apiRequest("/api/user-story", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({

                title: requirement,

                description: requirement

            })

        });

        const story = result.data || result.story || result;

        displayGeneratedStory(story);

        showStatus(
            "storyStatus",
            "User story generated successfully.",
            "success"
        );

        showNotification(
            "User story generated successfully."
        );

        await refreshDashboard();

    } catch (error) {

        showStatus(
            "storyStatus",
            error.message,
            "error"
        );

        showNotification(
            error.message,
            "error"
        );

    } finally {

        if (button) {

            button.disabled = false;

            button.textContent = "Generate User Story";

        }

    }

}


function displayGeneratedStory(story) {

    if (!story) return;

    setText(
        "userStoryOutput",
        story.user_story ||
        story.story ||
        story.title ||
        story.description ||
        JSON.stringify(story, null, 2)
    );

    const criteria = $("acceptanceCriteria");

    if (criteria) {

        const acceptanceCriteria =
            story.acceptance_criteria ||
            story.acceptanceCriteria ||
            [];

        if (Array.isArray(acceptanceCriteria)) {

            criteria.innerHTML = acceptanceCriteria.map(item => {

                return `
                    <li>${escapeHTML(item)}</li>
                `;

            }).join("");

        } else {

            criteria.textContent =
                String(acceptanceCriteria || "No acceptance criteria available.");

        }

    }

}


function updateUserStories(stories) {

    const container = $("userStoriesList");

    if (!container) return;

    if (!stories.length) {

        container.innerHTML = `
            <p>No user stories generated yet.</p>
        `;

        return;
    }

    container.innerHTML = stories.map((story, index) => {

        return `

            <div class="user-story-card">

                <h4>
                    ${escapeHTML(
                        story.title || "User Story " + (index + 1)
                    )}
                </h4>

                <p>
                    ${escapeHTML(
                        story.description || story.user_story || ""
                    )}
                </p>

            </div>

        `;

    }).join("");

}


window.generateUserStory = generateUserStory;


/* ============================================================
   21. AI ASSISTANT
============================================================ */

function initializeChat() {

    const chatForm = $("chatForm");

    if (chatForm) {

        chatForm.addEventListener("submit", function (event) {

            event.preventDefault();

            sendChatMessage();

        });

    }

    document.querySelectorAll(".suggestion-button").forEach(button => {

        button.addEventListener("click", function () {

            const question =
                this.dataset.question ||
                this.textContent.trim();

            const input = $("questionInput");

            if (input) {

                input.value = question;

                sendChatMessage();

            }

        });

    });

}


function addChatMessage(message, sender = "user") {

    const container = $("chatMessages");

    if (!container) return;

    const messageElement = document.createElement("div");

    messageElement.className =
        "chat-message " + sender;

    const content = document.createElement("div");

    content.className = "message-content";

    content.textContent = message;

    messageElement.appendChild(content);

    container.appendChild(messageElement);

    container.scrollTop = container.scrollHeight;

}


async function sendChatMessage() {

    const input = $("questionInput");

    if (!input) return;

    const message = input.value.trim();

    if (!message) return;

    addChatMessage(message, "user");

    input.value = "";

    showStatus(
        "chatStatus",
        "Assistant is thinking...",
        "info"
    );

    try {

        const result = await apiRequest("/ask", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({

                message: message,

                query: message,

                question: message

            })

        });

        const answer =
            result.answer ||
            result.response ||
            result.message ||
            "No answer received.";

        addChatMessage(answer, "assistant");

        showStatus(
            "chatStatus",
            "Response received.",
            "success"
        );

    } catch (error) {

        addChatMessage(
            "Sorry, I could not process your question. " + error.message,
            "assistant"
        );

        showStatus(
            "chatStatus",
            error.message,
            "error"
        );

    }

}


window.sendChatMessage = sendChatMessage;


/* ============================================================
   22. EXPORT PDF
============================================================ */

async function exportPDF() {

    try {

        showNotification(
            "Generating PDF report...",
            "info"
        );

        const response = await fetch("/api/export/pdf");

        if (!response.ok) {

            const result = await response.json();

            throw new Error(
                result.error || "PDF export failed."
            );

        }

        const blob = await response.blob();

        downloadBlob(
            blob,
            "Project_Risk_Advisor_Report.pdf"
        );

        showNotification(
            "PDF report downloaded successfully."
        );

    } catch (error) {

        showNotification(
            error.message,
            "error"
        );

    }

}


window.exportPDF = exportPDF;


/* ============================================================
   23. EXPORT EXCEL
============================================================ */

async function exportExcel() {

    try {

        showNotification(
            "Generating Excel report...",
            "info"
        );

        const response = await fetch("/api/export/excel");

        if (!response.ok) {

            const result = await response.json();

            throw new Error(
                result.error || "Excel export failed."
            );

        }

        const blob = await response.blob();

        downloadBlob(
            blob,
            "Project_Risk_Advisor_Report.xlsx"
        );

        showNotification(
            "Excel report downloaded successfully."
        );

    } catch (error) {

        showNotification(
            error.message,
            "error"
        );

    }

}


window.exportExcel = exportExcel;


/* ============================================================
   24. DOWNLOAD HELPER
============================================================ */

function downloadBlob(blob, filename) {

    const url = window.URL.createObjectURL(blob);

    const link = document.createElement("a");

    link.href = url;

    link.download = filename;

    document.body.appendChild(link);

    link.click();

    link.remove();

    window.URL.revokeObjectURL(url);

}


/* ============================================================
   25. SYSTEM TEST
============================================================ */

async function runSystemTest() {

    const button = $("runSystemTest");

    if (button) {

        button.disabled = true;

        button.textContent = "Testing...";

    }

    showStatus(
        "systemTestStatus",
        "Running system tests...",
        "info"
    );

    try {

        const result = await apiRequest("/health");

        showStatus(
            "systemTestStatus",
            JSON.stringify(result, null, 2),
            "success"
        );

        showNotification(
            "System health check completed."
        );

    } catch (error) {

        showStatus(
            "systemTestStatus",
            error.message,
            "error"
        );

    } finally {

        if (button) {

            button.disabled = false;

            button.textContent = "Run System Test";

        }

    }

}


window.runSystemTest = runSystemTest;


/* ============================================================
   26. EXPORT BUTTON INITIALIZATION
============================================================ */

function initializeExportButtons() {

    const pdfButton = $("exportPdf");

    const excelButton = $("exportExcel");

    if (pdfButton) {

        pdfButton.addEventListener("click", exportPDF);

    }

    if (excelButton) {

        excelButton.addEventListener("click", exportExcel);

    }

}


/* ============================================================
   27. ANALYZE BUTTON INITIALIZATION
============================================================ */

function initializeAnalyzeButton() {

    const button = $("analyzeButton");

    if (button) {

        button.addEventListener("click", function (event) {

            event.preventDefault();

            analyzeProject();

        });

    }

}


/* ============================================================
   28. STORY BUTTON INITIALIZATION
============================================================ */

function initializeStoryButton() {

    const button = $("generateStoryButton");

    if (button) {

        button.addEventListener("click", function (event) {

            event.preventDefault();

            generateUserStory();

        });

    }

}


/* ============================================================
   29. SYSTEM TEST BUTTON INITIALIZATION
============================================================ */

function initializeSystemTestButton() {

    const button = $("runSystemTest");

    if (button) {

        button.addEventListener("click", function (event) {

            event.preventDefault();

            runSystemTest();

        });

    }

}


/* ============================================================
   30. INITIALIZE APPLICATION
============================================================ */

async function initializeApplication() {

    console.log(
        "Project Risk Advisor Initialized"
    );

    initializeDate();

    initializeNavigation();

    initializeFileUpload();

    initializeChat();

    initializeExportButtons();

    initializeAnalyzeButton();

    initializeStoryButton();

    initializeSystemTestButton();

    await refreshDashboard();

}


/* ============================================================
   31. DOM READY
============================================================ */

document.addEventListener("DOMContentLoaded", function () {

    initializeApplication();

});


/* ============================================================
   END OF PROJECT RISK ADVISOR SCRIPT
============================================================ */
