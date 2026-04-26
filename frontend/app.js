const API_BASE = (window.APP_CONFIG && window.APP_CONFIG.apiBase) || "http://localhost:8000";

const form = document.getElementById("query-form");
const queryEl = document.getElementById("query");
const resultEl = document.getElementById("result");
const answerEl = document.getElementById("answer");
const sourcesEl = document.getElementById("sources");
const pathUsedEl = document.getElementById("path-used");
const topScoreEl = document.getElementById("top-score");

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
