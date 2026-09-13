const form = document.getElementById('prompt-form');
const promptInput = document.getElementById('prompt');
const notesInput = document.getElementById('notes');
const generateBtn = document.getElementById('generate-btn');
const btnLabel = generateBtn.querySelector('.btn-label');
const btnSpinner = generateBtn.querySelector('.btn-spinner');

const result = document.getElementById('result');
const resultEmpty = document.getElementById('result-empty');
const resultLoading = document.getElementById('result-loading');
const resultVideo = document.getElementById('result-video');
const resultSoon = document.getElementById('result-soon');
const loadingText = document.getElementById('loading-text');
const videoPlayer = document.getElementById('video-player');
const videoTopic = document.getElementById('video-topic');
const downloadBtn = document.getElementById('download-btn');

const STAGE_LABELS = {
  queued: 'Getting started…',
  planning: 'Planning your lesson…',
  scripting: 'Writing the script…',
  storyboarding: 'Designing the visuals…',
  voice: 'Recording the narration…',
  animating: 'Animating the scenes…',
  assembling: 'Putting it all together…',
  uploading: 'Finishing up…',
};

function showOnly(el) {
  [resultEmpty, resultLoading, resultVideo, resultSoon].forEach((s) => {
    s.hidden = s !== el;
  });
  result.hidden = false;
  result.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Video format toggle
let videoMode = 'short';
document.querySelectorAll('.mode-option').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.mode-option').forEach((b) => b.classList.remove('selected'));
    btn.classList.add('selected');
    videoMode = btn.dataset.mode;
  });
});

// Narration language toggle
let narrationLang = 'en';
document.querySelectorAll('.lang-option').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.lang-option').forEach((b) => b.classList.remove('selected'));
    btn.classList.add('selected');
    narrationLang = btn.dataset.lang;
  });
});

// Example topic chips fill the text box
document.querySelectorAll('.chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    promptInput.value = chip.dataset.topic;
    promptInput.focus();
  });
});

const LAST_JOB_KEY = 'ptv-last-job';
const LAST_JOB_TTL_MS = 24 * 60 * 60 * 1000; // forget jobs older than 24h

function saveLastJob(jobId, topic) {
  try {
    localStorage.setItem(LAST_JOB_KEY, JSON.stringify({ jobId, topic, startedAt: Date.now() }));
  } catch (e) { /* storage unavailable: resume just won't work */ }
}

function loadLastJob() {
  try {
    const raw = localStorage.getItem(LAST_JOB_KEY);
    if (!raw) return null;
    const job = JSON.parse(raw);
    if (!job || !job.jobId || Date.now() - (job.startedAt || 0) > LAST_JOB_TTL_MS) return null;
    return job;
  } catch (e) { return null; }
}

function clearLastJob() {
  try { localStorage.removeItem(LAST_JOB_KEY); } catch (e) {}
}

function stageLabel(stage, extra) {
  let label = STAGE_LABELS[stage] || 'Working on your video…';
  if (stage === 'animating' && extra.sceneCount) {
    label = `Animating the scenes (${extra.sceneDone || 0}/${extra.sceneCount})…`;
  }
  return label;
}

function showVideo(videoUrl, topic) {
  videoPlayer.src = videoUrl;
  videoTopic.textContent = 'Explainer: ' + topic;
  downloadBtn.href = videoUrl;
  downloadBtn.setAttribute('download', 'explainer.mp4');
  showOnly(resultVideo);
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const topic = promptInput.value.trim();
  if (!topic) {
    promptInput.focus();
    return;
  }

  generateBtn.disabled = true;
  btnLabel.textContent = 'Creating…';
  btnSpinner.hidden = false;
  showOnly(resultLoading);
  loadingText.textContent = STAGE_LABELS.queued;

  try {
    const jobId = await startJob(topic, notesInput.value.trim());
    const startedAt = Date.now();
    saveLastJob(jobId, topic); // so the page can resume if closed/backgrounded
    await trackJob(jobId, topic, startedAt);
  } catch (err) {
    console.error(err);
    showError('Could not start your video. Please check your connection and try again.');
  } finally {
    generateBtn.disabled = false;
    btnLabel.textContent = 'Create explainer video';
    btnSpinner.hidden = true;
  }
});

async function startJob(topic, notes) {
  const startRes = await fetch('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic, lang: narrationLang, mode: videoMode, notes }),
  });
  if (startRes.status === 503) throw new Error('Backend not configured yet');
  if (!startRes.ok) throw new Error('Failed to start job');
  const { jobId } = await startRes.json();
  if (!jobId) throw new Error('No job id returned');
  return jobId;
}

async function pollJob(jobId, onStage, startedAt) {
  // The backend itself times out after 60 minutes, so a job older than that
  // can never finish — bound the wait to the job's whole life, not the
  // visible session (backgrounded tabs freeze timers but not the clock).
  const deadline = (startedAt || Date.now()) + 60 * 60 * 1000;
  let failures = 0;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 4000));
    let state;
    try {
      const res = await fetch(`/api/status?jobId=${encodeURIComponent(jobId)}`);
      if (!res.ok) throw new Error('Status check failed');
      state = await res.json();
      failures = 0;
    } catch (e) {
      failures++;
      if (failures >= 5) throw e; // persistent failure: give up for real
      continue; // transient blip: keep polling
    }
    if (state.stage === 'done' && state.videoUrl) return state.videoUrl;
    if (state.stage === 'error') {
      const err = new Error(state.error || 'Video job failed');
      err.jobFailed = true;
      throw err;
    }
    onStage(state.stage, state);
  }
  const err = new Error('Timed out waiting for video');
  err.timedOut = true;
  throw err;
}

function showWaiting() {
  document.getElementById('soon-icon').textContent = '⏳';
  document.getElementById('soon-title').textContent = 'Still working on your video…';
  document.getElementById('soon-sub').textContent =
    'This one is taking longer than usual. You can leave and come back — it will be here when it finishes.';
  showOnly(resultSoon);
}

function showError(msg) {
  document.getElementById('soon-icon').textContent = '⚠️';
  document.getElementById('soon-title').textContent = 'Something went wrong';
  document.getElementById('soon-sub').textContent = msg;
  showOnly(resultSoon);
}

let pollActive = false;

// Poll a job to completion. Timeout keeps the saved job (the video may still
// land — a reload picks it up); a real backend failure clears it and says so.
async function trackJob(jobId, topic, startedAt) {
  if (pollActive) return;
  // A job older than ~65min can never finish: the backend kills work at 60min.
  if (startedAt && Date.now() - startedAt > 65 * 60 * 1000) {
    clearLastJob();
    showError('This video got stuck on our end and will not finish. Please try again with a new topic.');
    return;
  }
  pollActive = true;
  try {
    const videoUrl = await pollJob(jobId, (stage, extra) => {
      loadingText.textContent = stageLabel(stage, extra);
    }, startedAt);
    clearLastJob();
    if (videoUrl) {
      showVideo(videoUrl, topic);
    } else {
      showWaiting();
    }
    loadHistory(); // the shelf just gained (or updated) an entry
  } catch (err) {
    console.error(err);
    if (err.timedOut) {
      showWaiting(); // keep the saved job: the video may still arrive
    } else if (!err.jobFailed) {
      showWaiting(); // network died: keep the job, retry on return
    } else {
      clearLastJob();
      showError(err.message);
      loadHistory(); // surface the failed entry in history
    }
  } finally {
    pollActive = false;
  }
}

// Resume an in-progress job when the page is (re)opened: the user may have
// switched apps or closed the tab while the video was being made.
function resumeSavedJob() {
  const last = loadLastJob();
  if (!last) return;
  showOnly(resultLoading);
  loadingText.textContent = 'Picking up where you left off…';
  trackJob(last.jobId, last.topic, last.startedAt);
}

document.addEventListener('DOMContentLoaded', resumeSavedJob);

// If the tab was backgrounded and polling died (mobile browsers freeze
// timers), pick the saved job back up when the user returns.
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') resumeSavedJob();
});

// ---- My videos history ----
const historySection = document.getElementById('history');
const historyList = document.getElementById('history-list');
const historyRefresh = document.getElementById('history-refresh');

function timeAgo(ts) {
  if (!ts) return '';
  const s = Math.floor(Date.now() / 1000) - ts;
  if (s < 60) return 'just now';
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return d === 1 ? 'yesterday' : `${d}d ago`;
}

function historyStatus(job) {
  if (job.stage === 'done' && job.videoUrl) return ['ready', 'Ready'];
  if (job.stage === 'error') return ['failed', 'Failed'];
  return ['working', 'Rendering…'];
}

async function loadHistory() {
  let jobs = [];
  try {
    const res = await fetch('/api/jobs');
    if (res.ok) {
      const data = await res.json();
      jobs = data.jobs || [];
    }
  } catch (e) { /* history is a bonus: never break the page */ }
  renderHistory(jobs);
}

function renderHistory(jobs) {
  historyList.innerHTML = '';
  if (!jobs.length) {
    historySection.hidden = true;
    return;
  }
  historySection.hidden = false;
  for (const job of jobs) {
    const [cls, label] = historyStatus(job);
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'history-item';
    const play = document.createElement('span');
    play.className = 'history-play';
    play.textContent = '▶';
    const meta = document.createElement('span');
    meta.className = 'history-meta';
    const title = document.createElement('span');
    title.className = 'history-title';
    title.textContent = job.title || 'Untitled';
    const sub = document.createElement('span');
    sub.className = 'history-sub';
    const modeNames = { reel: '📱 Reels', short: 'Short', deep: '🎓 Deep dive' };
    const mode = document.createElement('span');
    mode.className = 'mode-badge';
    mode.textContent = modeNames[job.mode] || 'Short';
    const lang = document.createElement('span');
    lang.className = 'lang-badge';
    lang.textContent = job.lang === 'ta' ? 'தமிழ்' : 'English';
    const when = document.createElement('span');
    when.textContent = timeAgo(job.createdAt);
    const chip = document.createElement('span');
    chip.className = `status-chip status-${cls}`;
    chip.textContent = label;
    sub.append(mode, lang, when, chip);
    meta.append(title, sub);
    btn.append(play, meta);
    btn.addEventListener('click', () => openHistoryJob(job));
    historyList.appendChild(btn);
  }
}

function openHistoryJob(job) {
  if (job.stage === 'done' && job.videoUrl) {
    showVideo(job.videoUrl, job.title);
    return;
  }
  if (job.stage === 'error') {
    showError(job.error || 'This video failed to render.');
    return;
  }
  // Still in progress: make it the tracked job and follow it.
  saveLastJob(job.jobId, job.title);
  showOnly(resultLoading);
  loadingText.textContent = 'Picking up where you left off…';
  trackJob(job.jobId, job.title, job.createdAt ? job.createdAt * 1000 : Date.now());
}

historyRefresh.addEventListener('click', async () => {
  historyRefresh.classList.add('spinning');
  try { await loadHistory(); } finally { historyRefresh.classList.remove('spinning'); }
});

document.addEventListener('DOMContentLoaded', loadHistory);
