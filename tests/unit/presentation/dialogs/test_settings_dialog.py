import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QMessageBox
from src.presentation.dialogs.settings_dialog import SettingsDialog

@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.get_root_directory.return_value = "C:/Music"
    settings.get_database_path.return_value = "C:/db.sqlite"
    settings.get_conversion_enabled.return_value = True
    settings.get_delete_wav_after_conversion.return_value = False
    settings.get_delete_zip_after_import.return_value = False
    settings.get_rename_enabled.return_value = True
    settings.get_move_after_done.return_value = False
    settings.get_rename_pattern.return_value = "{Artist}/{Album}/{Title}"
    settings.get_conversion_bitrate.return_value = "320k"
    settings.get_ffmpeg_path.return_value = "ffmpeg"
    settings.get_search_provider.return_value = "Google"
    settings.get_default_year.return_value = 2026
    settings.get_log_path.return_value = "C:/logs/gosling.log"
    return settings

def test_settings_dialog_load_save(qtbot, mock_settings):
    """Test that settings load into UI and save back correctly."""
    dialog = SettingsDialog(mock_settings)
    qtbot.addWidget(dialog)
    
    # 1. Verify Load
    assert dialog.txt_root_dir.text() == "C:/Music"
    assert dialog.cmb_bitrate.currentText() == "320k"
    
    # 2. Change values
    dialog.txt_root_dir.setText("D:/NewMusic")
    dialog.cmb_bitrate.setCurrentText("VBR (V0)")
    
    # 3. Trigger Save
    dialog._on_save_clicked()
    
    import os
    # 4. Verify mock calls
    mock_settings.set_root_directory.assert_called_with(os.path.normpath("D:/NewMusic"))
    mock_settings.set_conversion_bitrate.assert_called_with("VBR (V0)")
    mock_settings.sync.assert_called_once()
