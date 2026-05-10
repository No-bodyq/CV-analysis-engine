// popup.js — handles all UI logic, scraping, and Groq API call

const GROQ_MODEL = "llama-3.3-70b-versatile";
const GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions";

// ── DOM refs ──
const apiKeyInput = document.getElementById("apiKeyInput");
const saveKeyBtn  = document.getElementById("saveKeyBtn");
const keyStatus   = document.getElementById("keyStatus");
const scrapeBtn   = document.getElementById("scrapeBtn");
const statusBar   = document.getElementById("statusBar");
const statusText  = document.getElementById("statusText");
const resultCard  = document.getElementById("resultCard");
const errorCard   = document.getElementById("errorCard");
const copyBtn     = document.getElementById("copyBtn");
const sendBtn     = document.getElementById("sendBtn");

let extractedData = null;

// ── Load saved API key on open ──
chrome.storage.local.get(["groqApiKey"], (res) => {
  if (res.groqApiKey) {
    apiKeyInput.value = res.groqApiKey;
    showKeyStatus("✓ Key loaded", "ok");
  }
});

// ── Save API key ──
saveKeyBtn.addEventListener("click", () => {
  const key = apiKeyInput.value.trim();
  if (!key) {
    showKeyStatus("✗ Enter a key first", "err");
    return;
  }
  chrome.storage.local.set({ groqApiKey: key }, () => {
    showKeyStatus("✓ Saved!", "ok");
  });
});

function showKeyStatus(msg, type) {
  keyStatus.textContent = msg;
  keyStatus.className = `key-status ${type}`;
}

// ── Main scrape flow ──
scrapeBtn.addEventListener("click", async () => {
  const apiKey = apiKeyInput.value.trim();
  if (!apiKey) {
    showError("Please enter and save your Groq API key first.");
    return;
  }

  resetUI();
  setLoading(true, "Extracting page content...");

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    const scrapeResult = await chrome.tabs.sendMessage(tab.id, { action: "scrapeJobPage" });

    if (!scrapeResult || !scrapeResult.success) {
      throw new Error(scrapeResult?.error || "Could not read page content. Try refreshing the page.");
    }

    setLoading(true, "Sending to Groq AI for analysis...");

    const jobData = await extractWithGroq(scrapeResult.text, scrapeResult.title, apiKey);
    extractedData = jobData;
    renderResult(jobData);

  } catch (err) {
    showError(err.message);
  } finally {
    setLoading(false);
  }
});

// ── Groq API call ──
async function extractWithGroq(pageText, pageTitle, apiKey) {
  const prompt = `Extract the job title, required skills, and qualifications from this job listing page.
Page title: ${pageTitle}

Return ONLY a valid JSON object — no markdown, no explanation, no backticks. Exactly this format:
{"title": "Job Title Here", "skills": ["skill1", "skill2"], "qualifications": ["qual1", "qual2"]}

Keep skills and qualifications concise (3-6 words each). Include up to 10 skills and 6 qualifications.
If something is not present, use an empty array [].

Page text:
${pageText}`;

  const response = await fetch(GROQ_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${apiKey}`
    },
    body: JSON.stringify({
      model: GROQ_MODEL,
      messages: [{ role: "user", content: prompt }],
      temperature: 0.1,
      max_tokens: 1024
    })
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    const msg = errData?.error?.message || `Groq API error (${response.status})`;
    throw new Error(msg);
  }

  const data = await response.json();
  const rawText = data?.choices?.[0]?.message?.content || "";
  const cleaned = rawText.replace(/```json|```/gi, "").trim();

  try {
    return JSON.parse(cleaned);
  } catch {
    throw new Error("AI returned unexpected output. Try again.");
  }
}

// ── Render result ──
function renderResult(data) {
  document.getElementById("rTitle").textContent = data.title || "Unknown";

  const skillsEl = document.getElementById("rSkills");
  skillsEl.innerHTML = "";
  (data.skills || []).forEach(s => {
    const tag = document.createElement("span");
    tag.className = "tag skill";
    tag.textContent = s;
    skillsEl.appendChild(tag);
  });
  if (!data.skills?.length) skillsEl.innerHTML = '<span style="font-size:11px;color:var(--muted)">None found</span>';

  const qualsEl = document.getElementById("rQuals");
  qualsEl.innerHTML = "";
  (data.qualifications || []).forEach(q => {
    const tag = document.createElement("span");
    tag.className = "tag qual";
    tag.textContent = q;
    qualsEl.appendChild(tag);
  });
  if (!data.qualifications?.length) qualsEl.innerHTML = '<span style="font-size:11px;color:var(--muted)">None found</span>';

  resultCard.classList.add("visible");
}

// ── Copy JSON ──
copyBtn.addEventListener("click", () => {
  if (!extractedData) return;
  navigator.clipboard.writeText(JSON.stringify(extractedData, null, 2)).then(() => {
    copyBtn.textContent = "✓ Copied!";
    setTimeout(() => { copyBtn.textContent = "📋 Copy JSON"; }, 2000);
  });
});

// ── Send to local app ──
sendBtn.addEventListener("click", async () => {
  if (!extractedData) return;
  const LOCAL_APP_URL = "http://localhost:5000/api/job-data";
  sendBtn.textContent = "Sending...";
  sendBtn.disabled = true;

  try {
    const res = await fetch(LOCAL_APP_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(extractedData)
    });
    if (res.ok) {
      sendBtn.textContent = "✓ Sent!";
      sendBtn.style.background = "#4ade80";
    } else {
      throw new Error(`App returned ${res.status}`);
    }
  } catch (err) {
    navigator.clipboard.writeText(JSON.stringify(extractedData, null, 2));
    sendBtn.textContent = "App offline — copied!";
    sendBtn.style.background = "#fbbf24";
    sendBtn.style.color = "#0a0a0f";
  } finally {
    setTimeout(() => {
      sendBtn.textContent = "→ Send to App";
      sendBtn.style.background = "";
      sendBtn.style.color = "";
      sendBtn.disabled = false;
    }, 3000);
  }
});

// ── UI helpers ──
function setLoading(on, msg = "") {
  scrapeBtn.disabled = on;
  if (on) {
    statusBar.classList.add("visible");
    statusText.textContent = msg;
  } else {
    statusBar.classList.remove("visible");
  }
}

function showError(msg) {
  errorCard.textContent = `✗ ${msg}`;
  errorCard.classList.add("visible");
}

function resetUI() {
  resultCard.classList.remove("visible");
  errorCard.classList.remove("visible");
  extractedData = null;
}
