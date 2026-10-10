const form = document.getElementById("search-form");
const input = document.getElementById("search-input");
const container = document.getElementById("results-container");
const metaContainer = document.getElementById("meta-container");
const resultCount = document.getElementById("result-count");
const searchLatency = document.getElementById("search-latency");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = input.value.trim();
  if (!query) return;

  container.innerHTML = `<div class="loading">Searching live web index...</div>`;
  metaContainer.style.display = "none";

  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    const data = await res.json();

    if (data.status !== "success" || data.results.length === 0) {
      container.innerHTML = `
        <div class="glass-card" style="text-align: center;">
          <h3 style="color: var(--accent-amber);">No matches found</h3>
          <p style="color: var(--text-muted); margin-top: 8px;">Try different keywords or verify network connectivity.</p>
        </div>
      `;
      return;
    }

    metaContainer.style.display = "flex";
    resultCount.textContent = `About ${data.total_results} results`;
    searchLatency.textContent = `Retrieved in ${data.search_time_seconds}s`;

    let html = "";

    // 1. Instant Knowledge Graph Card if available
    if (data.instant_answer) {
      html += `
        <div class="glass-card instant-card">
          <div class="instant-title">${escapeHTML(data.instant_answer.heading)}</div>
          <p class="result-snippet">${escapeHTML(data.instant_answer.text)}</p>
          ${data.instant_answer.url ? `<a href="${data.instant_answer.url}" target="_blank" rel="noopener noreferrer" class="result-url" style="margin-top: 10px; color: var(--accent-orange);">Source: ${data.instant_answer.source || 'Knowledge Base'} ↗</a>` : ''}
        </div>
      `;
    }

    // 2. Ranked Web Results
    data.results.forEach((item) => {
      html += `
        <article class="glass-card">
          <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="result-url">
            ${escapeHTML(item.url)}
          </a>
          <div>
            <a href="${item.url}" target="_blank" rel="noopener noreferrer" class="result-title">
              ${escapeHTML(item.title)}
            </a>
            <span class="score-badge">Rank ${item.relevance_score || '1.0'}</span>
          </div>
          <p class="result-snippet">${escapeHTML(item.snippet)}</p>
        </article>
      `;
    });

    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `
      <div class="glass-card" style="border-color: rgba(255, 50, 50, 0.4);">
        <h3 style="color: #ff5555;">Connection Failure</h3>
        <p style="color: var(--text-muted); margin-top: 8px;">Backend API unreachable. Ensure Uvicorn server is active on port 8000.</p>
      </div>
    `;
  }
});

function escapeHTML(str) {
  if (!str) return "";
  return str.replace(/[&<>'"]/g, 
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}
