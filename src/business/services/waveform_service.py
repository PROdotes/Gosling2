"""Waveform generation service using FFmpeg subprocess"""
import os
import json
import hashlib
import struct
import subprocess
import tempfile
from typing import List, Optional
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from ...core.vfs import VFS


class _WaveformWorker(QObject):
    """Worker that runs FFmpeg in a background thread."""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, source_path: str, temp_file: Optional[str],
                 target_peaks: int, ffmpeg_path: str):
        super().__init__()
        self._source_path = source_path
        self._temp_file = temp_file
        self._target_peaks = target_peaks
        self._ffmpeg_path = ffmpeg_path

    def run(self):
        try:
            peaks = self._extract_peaks()
            if peaks:
                self.finished.emit(peaks)
            else:
                self.error.emit("No audio data decoded")
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self._cleanup()

    def _extract_peaks(self) -> List[float]:
        """Decode entire file to raw PCM via FFmpeg, compute peaks."""
        path = self._source_path

        # FFmpeg: decode to mono 16-bit 8kHz raw PCM on stdout
        # 8kHz is enough for waveform visuals and keeps data small
        cmd = [
            self._ffmpeg_path,
            "-i", path,
            "-vn",
            "-ac", "1",
            "-ar", "8000",
            "-f", "s16le",
            "-acodec", "pcm_s16le",
            "pipe:1"
        ]

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            startupinfo=startupinfo
        )
        raw_data, stderr = proc.communicate()

        if proc.returncode != 0 or not raw_data:
            err = stderr.decode(errors='replace') if stderr else "Unknown"
            raise RuntimeError(f"FFmpeg decode failed: {err[:200]}")

        # Parse raw 16-bit signed samples
        num_samples = len(raw_data) // 2
        if num_samples == 0:
            return []

        samples = struct.unpack(f"<{num_samples}h", raw_data)

        # Resample into target_peaks bins
        samples_per_peak = max(1, num_samples // self._target_peaks)
        peaks = []
        for i in range(self._target_peaks):
            start = i * samples_per_peak
            end = min(start + samples_per_peak, num_samples)
            if start >= num_samples:
                peaks.append(0.0)
                continue
            chunk = samples[start:end]
            peak = max(max(chunk), -min(chunk)) / 32768.0
            peaks.append(min(1.0, peak))

        return peaks

    def _cleanup(self):
        if self._temp_file and os.path.exists(self._temp_file):
            try:
                os.remove(self._temp_file)
            except Exception:
                pass


class WaveformService(QObject):
    """
    Service for extracting peak data from audio files.
    Uses FFmpeg to decode audio and compute peaks in a background thread.
    Handles VFS (ZIP) paths by extracting to temp files.
    """
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, cache_dir: Optional[str] = None,
                 settings_manager=None):
        super().__init__()
        self._settings_manager = settings_manager

        if not cache_dir:
            cache_dir = os.path.join(
                os.getenv('LOCALAPPDATA', '.'),
                'Gosling2', 'Waveforms'
            )
        self._cache_dir = cache_dir
        os.makedirs(self._cache_dir, exist_ok=True)

        self._target_peak_count = 500
        self._current_path = ""
        self._thread: Optional[QThread] = None
        self._worker: Optional[_WaveformWorker] = None

    def stop(self):
        """Cancel any in-progress decode."""
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(2000)
        self._thread = None
        self._worker = None

    def load_waveform(self, file_path: str) -> bool:
        """
        Request waveform for a file.
        Returns True if cache hit (emits finished immediately).
        Returns False if background decode started.
        """
        self.stop()
        self._current_path = file_path

        # Check cache
        cache_file = self._get_cache_path(file_path)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    peaks = json.load(f)
                    self.finished.emit(peaks)
                    return True
            except Exception:
                pass

        # Resolve source (VFS or physical)
        temp_file = None
        source_path = file_path
        try:
            if VFS.is_virtual(file_path):
                ext = os.path.splitext(file_path)[1] or ".mp3"
                fd, temp_path = tempfile.mkstemp(
                    suffix=ext, prefix="gosling_wf_"
                )
                os.close(fd)
                with open(temp_path, 'wb') as f:
                    f.write(VFS.read_bytes(file_path))
                source_path = temp_path
                temp_file = temp_path
        except Exception as e:
            self.error.emit(f"Source preparation failed: {e}")
            return False

        # Resolve ffmpeg path
        ffmpeg_path = "ffmpeg"
        if self._settings_manager:
            ffmpeg_path = (
                self._settings_manager.get_ffmpeg_path() or "ffmpeg"
            )

        # Launch worker thread
        self._thread = QThread()
        self._worker = _WaveformWorker(
            source_path, temp_file,
            self._target_peak_count, ffmpeg_path
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.error.connect(self._on_worker_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)

        self._thread.start()
        return False

    def _on_worker_finished(self, peaks: List[float]):
        """Cache and forward the result."""
        cache_file = self._get_cache_path(self._current_path)
        try:
            with open(cache_file, 'w') as f:
                json.dump(peaks, f)
        except Exception:
            pass
        self.finished.emit(peaks)

    def _on_worker_error(self, msg: str):
        self.error.emit(msg)

    def _get_cache_path(self, file_path: str) -> str:
        h = hashlib.md5(file_path.encode()).hexdigest()
        return os.path.join(self._cache_dir, f"{h}.json")
