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

  // Loading state
  generateBtn.disabled = true;
  btnLabel.textContent = 'Creating…';
  btnSpinner.hidden = false;
  showOnly(resultLoading);
  loadingText.textContent = 'Working on your video…';

  try {
    const videoUrl = await generateVideo(topic);
    if (videoUrl) {
      videoPlayer.src = videoUrl;
      videoTopic.textContent = 'Explainer: ' + topic;
      showOnly(resultVideo);
    } else {
      // Backend not wired up yet — show the honest placeholder
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

// Step 1: no backend yet. Step 2 will wire this to the real video pipeline.
async function generateVideo(topic) {
  // Simulate a short processing delay so the flow is visible end to end.
  await new Promise((r) => setTimeout(r, 1500));
  return null; // null = backend not connected yet
}
