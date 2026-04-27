const API_BASE = (window.APP_CONFIG && window.APP_CONFIG.apiBase) || "http://localhost:8000";

const form = document.getElementById("query-form");
const queryEl = document.getElementById("query");
const resultEl = document.getElementById("result");
const answerEl = document.getElementById("answer");
const sourcesEl = document.getElementById("sources");
const pathUsedEl = document.getElementById("path-used");
const topScoreEl = document.getElementById("top-score");
const uploadForm = document.getElementById("upload-form");
const fileEl = document.getElementById("file");
const refreshJobsBtn = document.getElementById("refresh-jobs");
const jobsPanelEl = document.getElementById("jobs-panel");
const jobsEl = document.getElementById("jobs");

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const query = queryEl.value.trim();
    if (!query) {
        return;
    }

    answerEl.textContent = "Running...";
    sourcesEl.innerHTML = "";
    resultEl.classList.remove("hidden");

    try {
        const response = await fetch(`${API_BASE}/query`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query, k: 5 }),
        });

        if (!response.ok) {
            const detail = await response.text();
            throw new Error(detail || "query failed");
        }

        const data = await response.json();
        pathUsedEl.textContent = data.path_used;
        topScoreEl.textContent = `top score: ${Number(data.top_score).toFixed(3)}`;
        answerEl.textContent = data.answer;

        for (const src of data.sources || []) {
            const li = document.createElement("li");
            li.textContent = `[${src.source}] (${src.score.toFixed(3)}) ${src.text}`;
            sourcesEl.appendChild(li);
        }
    } catch (error) {
        answerEl.textContent = `Error: ${error.message}`;
    }
});

async function refreshJobs() {
    const response = await fetch(`${API_BASE}/ingest/jobs`);
    if (!response.ok) {
        throw new Error("failed to fetch jobs");
    }
    const data = await response.json();
    jobsEl.innerHTML = "";
    for (const job of data.jobs || []) {
        const li = document.createElement("li");
        li.textContent = `#${job.id} ${job.filename} - ${job.status} (attempts=${job.attempts})${job.error ? ` - ${job.error}` : ""}`;
        jobsEl.appendChild(li);
    }
    jobsPanelEl.classList.remove("hidden");
}

uploadForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = fileEl.files && fileEl.files[0];
    if (!file) {
        return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch(`${API_BASE}/ingest/file`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const detail = await response.text();
            throw new Error(detail || "upload failed");
        }

        await refreshJobs();
    } catch (error) {
        alert(`Upload error: ${error.message}`);
    }
});

refreshJobsBtn.addEventListener("click", async () => {
    try {
        await refreshJobs();
    } catch (error) {
        alert(`Jobs error: ${error.message}`);
    }
});
