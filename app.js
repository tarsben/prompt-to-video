const form = document.getElementById('prompt-form');
const promptInput = document.getElementById('prompt');
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

// Example topic chips fill the text box
document.querySelectorAll('.chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    promptInput.value = chip.dataset.topic;
    promptInput.focus();
  });
});

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
    const videoUrl = await generateVideo(topic, (stage, extra) => {
      let label = STAGE_LABELS[stage] || 'Working on your video…';
      if (stage === 'animating' && extra.sceneCount) {
        label = `Animating the scenes (${extra.sceneDone || 0}/${extra.sceneCount})…`;
      }
      loadingText.textContent = label;
    });
    if (videoUrl) {
      videoPlayer.src = videoUrl;
      videoTopic.textContent = 'Explainer: ' + topic;
      downloadBtn.href = videoUrl;
      downloadBtn.setAttribute('download', 'explainer.mp4');
      showOnly(resultVideo);
    } else {
      showOnly(resultSoon);
    }
  } catch (err) {
    console.error(err);
    showOnly(resultSoon);
  } finally {
    generateBtn.disabled = false;
    btnLabel.textContent = 'Create explainer video';
    btnSpinner.hidden = true;
  }
});

async function generateVideo(topic, onStage) {
  // 1. Kick off the job
  const startRes = await fetch('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic }),
  });
  if (startRes.status === 503) return null; // backend not configured yet
  if (!startRes.ok) throw new Error('Failed to start job');
  const { jobId } = await startRes.json();

  // 2. Poll until done (jobs take minutes; poll every 4s, give up after 30 min).
  // Transient network failures are retried, not fatal: a single failed
  // status check (common on mobile) must not kill the whole wait.
  const deadline = Date.now() + 30 * 60 * 1000;
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
    if (state.stage === 'error') throw new Error(state.error || 'Video job failed');
    onStage(state.stage, state);
  }
  throw new Error('Timed out waiting for video');
}
