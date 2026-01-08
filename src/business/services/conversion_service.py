import os
import subprocess
import tempfile
from typing import Optional, Callable
from ...core.vfs import VFS
# (Mutagen imports removed, logic now handled by MetadataService)

class ConversionService:
    """Service for handling audio format conversions (e.g., WAV to MP3)."""
    
    def __init__(self, settings_manager):
        self.settings = settings_manager

    def is_ffmpeg_available(self) -> bool:
        """Checks if FFmpeg is available and executable."""
        ffmpeg_path = self.settings.get_ffmpeg_path() or "ffmpeg"
        try:
            # Try to run ffmpeg -version
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            subprocess.run(
                [ffmpeg_path, "-version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                startupinfo=startupinfo,
                check=True
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, OSError):
            return False

    def convert_wav_to_mp3(self, wav_path: str, progress_callback: Optional[Callable[[int], None]] = None) -> Optional[str]:
        """
        Converts a WAV file to MP3 based on settings.
        Returns the path to the new MP3 file on success, None on failure.
        """
        # Handle Virtual or Physical Existence
        is_virtual = VFS.is_virtual(wav_path)
        if not is_virtual and not os.path.exists(wav_path):
            return None
            
        if not wav_path.lower().endswith(".wav"):
            return None

        ffmpeg_path = self.settings.get_ffmpeg_path() or "ffmpeg"
        quality_setting = self.settings.get_conversion_bitrate() or "320k"
        
        # 1. Surgical Extraction for Virtual WAVs
        temp_wav = None
        if is_virtual:
            try:
                # Extract to a temp file that FFmpeg can read
                suffix = os.path.splitext(wav_path)[1]
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
                    tf.write(VFS.read_bytes(wav_path))
                    temp_wav = tf.name
            except Exception as e:
                from src.core import logger
                logger.error(f"Failed to extract virtual WAV for conversion: {e}")
                return None
        
        # Use temp_wav if we extracted one, else the original path
        source_path = temp_wav or wav_path
        
        # 1. Parse Quality args
        # VBR (V0) -> -q:a 0
        # 320k -> -b:a 320k
        quality_args = []
        if "VBR" in quality_setting.upper():
            quality_args = ["-q:a", "0"]
        else:
            # Strip standard 'k' if user accidentally included it, FFmpeg handles '320k' fine though
            quality_args = ["-b:a", quality_setting]

        # Output path (Always physical)
        if is_virtual:
             # For virtual ZIPs, we place the MP3 next to the ZIP file itself
             zip_file = wav_path.split("|")[0]
             mp3_path = os.path.splitext(zip_file)[0] + "_" + os.path.basename(wav_path.split("|")[1]).replace(".wav", ".mp3")
        else:
             mp3_path = os.path.splitext(wav_path)[0] + ".mp3"
        
        if os.path.exists(mp3_path):
            return None

        try:
            # Run FFmpeg
            cmd = [
                ffmpeg_path,
                "-i", source_path,
                "-vn",             # No video
                "-ar", "44100",    # Standard sample rate
                "-ac", "2",        # Stereo
            ]
            cmd.extend(quality_args)
            cmd.extend([
                "-y",              # Overwrite output
                mp3_path
            ])
            
            # Hide console on Windows
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                startupinfo=startupinfo,
                text=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                from src.core import logger
                logger.error(f"FFmpeg failed (Code {process.returncode}): {stderr}")
                return None
                
            return mp3_path
            
        except Exception as e:
            from src.core import logger
            logger.error(f"Conversion Error: {e}")
            return None
        finally:
            # Cleanup temp file
            if temp_wav and os.path.exists(temp_wav):
                try: os.remove(temp_wav)
                except: pass

    def sync_tags(self, source_song, target_mp3_path: str) -> bool:
        """
        Copies metadata from the database/Song object to the newly created MP3.
        Reuses MetadataService.write_tags for DRY consistency.
        """
        # We need to temporarily point the song's path to the new MP3
        original_path = source_song.path
        source_song.path = target_mp3_path
        
        try:
            from .metadata_service import MetadataService
            return MetadataService.write_tags(source_song)
        except Exception as e:
            from src.core import logger
            logger.error(f"Tag Sync Error: {e}")
            return False
        finally:
            # Restore original path
            source_song.path = original_path

    def prompt_and_convert(self, wav_path: str) -> Optional[str]:
        """
        Interactively prompt the user to convert a WAV file to MP3.
        If accepted, performs conversion and returns the new MP3 path.
        If rejected or failed, returns None.
        """
        try:
            from PyQt6.QtWidgets import QMessageBox, QApplication
            
            # Ensure we have an application instance
            app = QApplication.instance()
            if not app:
                return None
                
            # If strictly headless or no windows, we might need a parent. 
            # Using None parent creates a modal top-level app window.
            # Check settings for auto-deletion
            should_delete = self.settings.get_delete_wav_after_conversion()
            
            # Dynamic prompt text
            disclaimer = "(Original WAV will be DELETED)" if should_delete else "(Original WAV will remain untouched)"
            
            fname = os.path.basename(wav_path)
            reply = QMessageBox.question(
                None, 
                "Format Conversion Required",
                f"The file '{fname}' is in WAV format.\n\n"
                "Gosling2 requires MP3s for the library.\n"
                "Would you like to convert it to high-quality MP3 now?\n\n"
                f"{disclaimer}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                mp3_path = self.convert_wav_to_mp3(wav_path)
                
                # Logic: Delete only if successful conversion AND setting is strictly enabled
                if mp3_path and os.path.exists(mp3_path) and should_delete:
                    from src.core import logger
                    try:
                        os.remove(wav_path)
                        logger.info(f"Deleted original WAV after conversion: {wav_path}")
                    except OSError as e:
                        logger.error(f"Failed to delete original WAV: {e}")
                        
                return mp3_path
            else:
                return None
                
        except ImportError:
            # Fallback for headless/test environments without PyQt
            from src.core import logger
            logger.warning("PyQt6 not found, cannot prompt for conversion.")
            return None
