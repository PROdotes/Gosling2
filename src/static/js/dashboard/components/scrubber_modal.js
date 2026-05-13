import { wasMousedownInside } from "./utils.js";
import { createModalLifecycle } from "./modal_lifecycle.js";

const overlay = document.getElementById("scrubber-modal");
const titleEl = document.getElementById("scrubber-modal-title");
const audio = document.getElementById("scrubber-audio");
const waveformBox = document.getElementById("scrubber-waveform-box");
const playBtn = document.getElementById("scrubber-play-pause");
const volumeBar = document.getElementById("scrubber-volume");
const timeCurrent = document.getElementById("scrubber-time-current");
const timeTotal = document.getElementById("scrubber-time-total");
const tagsBtn = document.getElementById("scrubber-tags-btn");

let _currentId = null;
let _currentTitle = null;
let _onTagsClick = null;
let _onClose = null;
let modal;

// Waveform canvas + playhead inside the waveform box
waveformBox.style.position = "relative";

const waveformCanvas = document.createElement("canvas");
waveformCanvas.style.cssText = `
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    display: block; pointer-events: none;
`;
waveformBox.appendChild(waveformCanvas);

const playhead = document.createElement("div");
playhead.style.cssText = `
    position: absolute; top: 0; left: 0; width: 2px; height: 100%;
    background: var(--accent, #7c6af7); pointer-events: none;
`;
waveformBox.appendChild(playhead);

let _peaks = null;
let _peaksRequestId = 0;

function downsample(peaks, targetCount) {
    if (targetCount >= peaks.length) return peaks.slice();
    const out = new Array(targetCount);
    const ratio = peaks.length / targetCount;
    for (let i = 0; i < targetCount; i++) {
        const start = Math.floor(i * ratio);
        const end = Math.floor((i + 1) * ratio);
        let sum = 0;
        const n = Math.max(1, end - start);
        for (let j = start; j < end; j++) sum += peaks[j];
        out[i] = sum / n;
    }
    return out;
}

function _setupCanvas() {
    const dpr = window.devicePixelRatio || 1;
    const cssW = waveformBox.clientWidth;
    const cssH = waveformBox.clientHeight;
    if (cssW === 0 || cssH === 0) return null;
    waveformCanvas.width = Math.floor(cssW * dpr);
    waveformCanvas.height = Math.floor(cssH * dpr);
    const ctx = waveformCanvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssW, cssH);
    return { ctx, cssW, cssH };
}

function renderPlaceholder() {
    const setup = _setupCanvas();
    if (!setup) return;
    const { ctx, cssW, cssH } = setup;

    const barPx = 2;
    const gapPx = 1;
    const stride = barPx + gapPx;
    const barCount = Math.max(1, Math.floor(cssW / stride));

    const styles = getComputedStyle(document.documentElement);
    const color = styles.getPropertyValue("--accent").trim() || "#7c6af7";
    ctx.fillStyle = color;
    ctx.globalAlpha = 0.18;

    const mid = cssH / 2;
    for (let i = 0; i < barCount; i++) {
        ctx.fillRect(i * stride, mid - 1, barPx, 2);
    }
    ctx.globalAlpha = 1;
}

function renderWaveform() {
    if (!_peaks) return;
    const setup = _setupCanvas();
    if (!setup) return;
    const { ctx, cssW, cssH } = setup;

    const barPx = 2;
    const gapPx = 1;
    const stride = barPx + gapPx;
    const barCount = Math.max(1, Math.floor(cssW / stride));
    const bars = downsample(_peaks, barCount);

    const styles = getComputedStyle(document.documentElement);
    const color = styles.getPropertyValue("--accent").trim() || "#7c6af7";
    ctx.fillStyle = color;

    const mid = cssH / 2;
    const maxHalf = cssH / 2 - 1;
    for (let i = 0; i < bars.length; i++) {
        const h = Math.max(1, bars[i] * maxHalf);
        const x = i * stride;
        ctx.fillRect(x, mid - h, barPx, h * 2);
    }
}

async function loadWaveform(songId) {
    _peaks = null;
    renderPlaceholder();

    const requestId = ++_peaksRequestId;
    try {
        const res = await fetch(`/api/v1/songs/${songId}/waveform`);
        if (!res.ok) return;
        const data = await res.json();
        if (requestId !== _peaksRequestId) return; // stale
        _peaks = data.peaks;
        renderWaveform();
    } catch (err) {
        console.warn("Waveform load failed:", err);
    }
}

window.addEventListener("resize", () => {
    if (overlay.style.display === "none") return;
    if (_peaks) renderWaveform();
    else renderPlaceholder();
});

function fmt(secs) {
    if (!isFinite(secs)) return "0:00";
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60)
        .toString()
        .padStart(2, "0");
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
    audio.currentTime = Math.max(
        0,
        Math.min(audio.duration || 0, audio.currentTime + delta),
    );
}

// Scrubber keydown handler — only active when modal is open
function handleScrubberKeydown(e) {
    if (overlay.style.display === "none") return;
    if (e.target.tagName === "INPUT") return;

    // Safety: ignore if a sub-modal is open on top of the scrubber
    const subModals = ["link-modal", "edit-modal", "confirm-modal", "spotify-modal", "splitter-modal", "filename-parser-modal"];
    if (subModals.some(id => document.getElementById(id)?.style.display === "flex")) return;
    if (e.key === " ") {
        e.preventDefault();
        e.stopImmediatePropagation();
        playBtn.click();
    }
    if (e.key === "ArrowLeft" || e.key === "a") {
        e.preventDefault();
        e.stopImmediatePropagation();
        seek(-10);
    }
    if (e.key === "ArrowRight" || e.key === "d") {
        e.preventDefault();
        e.stopImmediatePropagation();
        seek(10);
    }
    if (e.key === "+" || e.key === "NumpadAdd") {
        e.preventDefault();
        e.stopImmediatePropagation();
        tagsBtn.click();
    }
    if (e.key === "Enter") {
        e.preventDefault();
        e.stopImmediatePropagation();
        closeScrubberModal();
    }
}

tagsBtn?.addEventListener("click", () => {
    if (_onTagsClick && _currentId) _onTagsClick(_currentId, _currentTitle);
});

export function openScrubberModal(
    songId,
    title,
    { autoPlay = false, onTagsClick = null, onClose = null } = {},
) {
    modal.open(songId, title, { autoPlay, onTagsClick, onClose });
}

export function closeScrubberModal() {
    modal.close();
}

// ─── Modal Lifecycle ──────────────────────────────────────────

modal = createModalLifecycle(overlay, {
    onOpen: (songId, title, { autoPlay, onTagsClick, onClose }) => {
        _currentId = songId;
        _currentTitle = title;
        _onTagsClick = onTagsClick;
        _onClose = onClose;

        audio.pause();
        audio.src = `/api/v1/songs/${songId}/audio`;
        timeCurrent.textContent = "0:00";
        timeTotal.textContent = "0:00";
        updatePlayhead();
        updatePlayBtn();
        titleEl.textContent = title || "Player";

        loadWaveform(songId);

        document.addEventListener("keydown", handleScrubberKeydown);

        if (autoPlay) {
            audio
                .play()
                .catch((err) => console.warn("Auto-play blocked by browser:", err));
        }
    },
    onClose: () => {
        document.removeEventListener("keydown", handleScrubberKeydown);
        audio.pause();
        audio.src = "";
        _peaksRequestId++;
        _peaks = null;
        const ctx = waveformCanvas.getContext("2d");
        ctx.clearRect(0, 0, waveformCanvas.width, waveformCanvas.height);
        _currentId = null;
        _currentTitle = null;
        _onTagsClick = null;
        const cb = _onClose;
        _onClose = null;
        if (cb) cb();
    },
    overlayClickCheck: (e) => {
        if (wasMousedownInside(overlay.querySelector(".link-modal"))) return false;
        return e.target === overlay;
    }
});
