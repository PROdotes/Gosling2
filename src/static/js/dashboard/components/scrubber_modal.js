import { wasMousedownInside } from "./utils.js";
const overlay     = document.getElementById("scrubber-modal");
const titleEl     = document.getElementById("scrubber-modal-title");
const audio       = document.getElementById("scrubber-audio");
const waveformBox = document.getElementById("scrubber-waveform-box");
const playBtn     = document.getElementById("scrubber-play-pause");
const volumeBar   = document.getElementById("scrubber-volume");
const timeCurrent = document.getElementById("scrubber-time-current");
const timeTotal   = document.getElementById("scrubber-time-total");
const tagsBtn     = document.getElementById("scrubber-tags-btn");

let _currentId = null;
let _currentTitle = null;
let _onTagsClick = null;

// Playhead indicator inside the waveform box
const playhead = document.createElement("div");
playhead.style.cssText = `
    position: absolute; top: 0; left: 0; width: 2px; height: 100%;
    background: var(--accent, #7c6af7); pointer-events: none;
`;
waveformBox.style.position = "relative";
waveformBox.appendChild(playhead);

function fmt(secs) {
    if (!isFinite(secs)) return "0:00";
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
}

function updatePlayhead() {
    const pct = audio.duration ? (audio.currentTime / audio.duration) * 100 : 0;
    playhead.style.left = `${pct}%`;
}

function updatePlayBtn() {
    playBtn.textContent = audio.paused ? "▶" : "⏸";
}

audio.addEventListener("timeupdate", () => {
    if (!audio.duration) return;
    updatePlayhead();
    timeCurrent.textContent = fmt(audio.currentTime);
});

audio.addEventListener("loadedmetadata", () => {
    timeTotal.textContent = fmt(audio.duration);
    updatePlayhead();
});

audio.addEventListener("play", updatePlayBtn);
audio.addEventListener("pause", updatePlayBtn);
audio.addEventListener("ended", updatePlayBtn);

// Click anywhere on the box to seek
waveformBox.addEventListener("click", (e) => {
    if (!audio.duration) return;
    const rect = waveformBox.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    audio.currentTime = pct * audio.duration;
});

waveformBox.style.cursor = "pointer";

playBtn.addEventListener("click", () => {
    if (audio.paused) {
        audio.play();
    } else {
        audio.pause();
    }
});

volumeBar.addEventListener("input", () => {
    audio.volume = volumeBar.value;
});

function seek(delta) {
    audio.currentTime = Math.max(0, Math.min(audio.duration || 0, audio.currentTime + delta));
}

document.addEventListener("keydown", (e) => {
    if (overlay.style.display === "none") return;
    if (e.target.tagName === "INPUT") return;
if (e.key === " ") { e.preventDefault(); playBtn.click(); }
    if (e.key === "ArrowLeft" || e.key === "a") { e.preventDefault(); seek(-10); }
    if (e.key === "ArrowRight" || e.key === "d") { e.preventDefault(); seek(10); }
    if (e.key === "+" || e.key === "NumpadAdd") { e.preventDefault(); tagsBtn.click(); }
});

tagsBtn?.addEventListener("click", () => {
    if (_onTagsClick && _currentId) _onTagsClick(_currentId, _currentTitle);
});
 
export function openScrubberModal(songId, title, { autoPlay = false, onTagsClick = null } = {}) {
    _currentId = songId;
    _currentTitle = title;
    _onTagsClick = onTagsClick;
 
    audio.pause();
    audio.src = `/api/v1/songs/${songId}/audio`;
    timeCurrent.textContent = "0:00";
    timeTotal.textContent = "0:00";
    updatePlayhead();
    updatePlayBtn();
    titleEl.textContent = title || "Player";
    overlay.style.display = "flex";
    
    if (autoPlay) {
        audio.play().catch(err => console.warn("Auto-play blocked by browser:", err));
    }
}
 
export function closeScrubberModal() {
    audio.pause();
    audio.src = "";
    _currentId = null;
    _currentTitle = null;
    _onTagsClick = null;
    overlay.style.display = "none";
}
 
// Close on overlay click outside modal box
overlay.addEventListener("click", (e) => {
    if (wasMousedownInside(overlay.querySelector(".link-modal"))) return;
    if (e.target === overlay) closeScrubberModal();
});
