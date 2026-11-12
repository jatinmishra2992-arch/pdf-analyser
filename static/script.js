const $ = (id) => document.getElementById(id);
const show = (el, yes) => el.classList.toggle("hidden", !yes);

function showError(msg) {
  $("error").textContent = msg;
  show($("error"), true);
  $("error").scrollIntoView({ behavior: "smooth", block: "center" });
}

function esc(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function formatSize(bytes) {
  if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + " MB";
  return Math.max(1, Math.round(bytes / 1024)) + " KB";
}

function resetStats() {
  ["statPages", "statSize", "statType", "statParts"].forEach((id) => {
    $(id).textContent = "–";
  });
}

function setStats(file, data) {
  $("statPages").textContent = data.pages;
  $("statSize").textContent = formatSize(file.size);
  $("statType").textContent = data.is_scanned ? "Scanned" : "Text";
  $("statParts").textContent = Math.max(1, Math.ceil(data.pages / 10));
}

function renderSummary(text) {
  let html = "";
  let inList = false;
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    const isBullet = line.startsWith("- ");
    if (inList && !isBullet) { html += "</ul>"; inList = false; }
    if (!line) continue;
    if (line.startsWith("## ")) html += "<h4>" + esc(line.slice(3)) + "</h4>";
    else if (line.startsWith("# ")) html += "<h3>" + esc(line.slice(2)) + "</h3>";
    else if (isBullet) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += "<li>" + esc(line.slice(2)) + "</li>";
    }
    else if (line.startsWith("[Diagram") || line.startsWith("[Pages"))
      html += '<p class="diagram-note">' + esc(line) + "</p>";
    else html += "<p>" + esc(line) + "</p>";
  }
  if (inList) html += "</ul>";
  return html;
}

$("pdfInput").addEventListener("change", () => {
  const file = $("pdfInput").files[0];
  if (!file) return;

  show($("error"), false);
  show($("info"), false);
  show($("resultCard"), false);
  resetStats();

  if (!file.name.toLowerCase().endsWith(".pdf")) {
    return showError("Please choose a PDF file.");
  }

  $("preview").src = URL.createObjectURL(file);
  show($("previewCard"), true);

  const form = new FormData();
  form.append("pdf", file);

  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/upload");

  xhr.upload.onprogress = (e) => {
    if (!e.lengthComputable) return;
    const pct = Math.round((e.loaded / e.total) * 100);
    $("bar").style.width = pct + "%";
    $("progressText").textContent =
      pct < 100 ? "Uploading... " + pct + "%" : "Reading your PDF...";
  };

  xhr.onload = () => {
    show($("progressBox"), false);
    let data = {};
    try { data = JSON.parse(xhr.responseText); } catch (e) {}
    if (xhr.status !== 200) return showError(data.error || "Upload failed.");

    $("fileName").textContent = data.name;
    $("pageCount").textContent = data.pages;
    show($("scanNote"), data.is_scanned);
    show($("info"), true);
    setStats(file, data);
  };

  xhr.onerror = () => {
    show($("progressBox"), false);
    showError("Could not reach the server.");
  };

  $("bar").style.width = "0%";
  show($("progressBox"), true);
  xhr.send(form);
});

$("detailBtn").addEventListener("click", async () => {
  const file = $("pdfInput").files[0];
  if (!file) return showError("Please choose a PDF first.");

  show($("error"), false);
  show($("resultCard"), false);
  $("detailBtn").disabled = true;
  show($("aiBusy"), true);

  let secs = 0;
  let note = "Sending your PDF...";
  const timer = setInterval(() => {
    secs++;
    $("aiBusyText").textContent = note + " (" + secs + "s)";
  }, 1000);

  const wait = (ms) => new Promise((r) => setTimeout(r, ms));

  try {
    const form = new FormData();
    form.append("pdf", file);
    const res = await fetch("/summarize", { method: "POST", body: form });
    const start = await res.json().catch(() => ({}));
    if (!res.ok || !start.job_id) {
      throw new Error(start.error || "Could not start. Please try again.");
    }

    let finished = false;
    for (let i = 0; i < 200 && !finished; i++) {
      await wait(3000);
      let job = {};
      try {
        const r = await fetch("/status/" + start.job_id);
        job = await r.json();
      } catch (e) {
        continue; // the server may be waking up, keep trying
      }
      if (job.note) note = job.note;
      if (job.status === "done") {
        $("summaryBox").innerHTML = renderSummary(job.summary);
        show($("resultCard"), true);
        $("resultCard").scrollIntoView({ behavior: "smooth" });
        finished = true;
      } else if (job.status === "error") {
        throw new Error(job.error || "Something went wrong.");
      }
    }
    if (!finished) throw new Error("It took too long. Please try again.");
  } catch (e) {
    showError(e.message);
  } finally {
    clearInterval(timer);
    show($("aiBusy"), false);
    $("detailBtn").disabled = false;
  }
});