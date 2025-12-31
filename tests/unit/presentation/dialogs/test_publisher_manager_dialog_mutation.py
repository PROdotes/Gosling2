import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QMessageBox
from src.presentation.dialogs.publisher_manager_dialog import PublisherDetailsDialog
from src.data.models.publisher import Publisher

@pytest.fixture
def mock_repo():
    return MagicMock()

@pytest.fixture
def sample_pub():
    return Publisher(1, "Test", None)

def test_publisher_mutation_long_name(qtbot, mock_repo, sample_pub):
    dialog = PublisherDetailsDialog(sample_pub, mock_repo)
    qtbot.addWidget(dialog)
    
    # Chaos Monkey: 10,000 character name
    long_name = "A" * 10000
    dialog.txt_name.setText(long_name)
    
    mock_repo.update.return_value = True
    dialog._save()
    
    # Should handle it without crashing (sending to repo)
    assert sample_pub.publisher_name == long_name
    mock_repo.update.assert_called_once()

def test_publisher_mutation_sql_injection(qtbot, mock_repo, sample_pub):
    dialog = PublisherDetailsDialog(sample_pub, mock_repo)
    qtbot.addWidget(dialog)
    
    # Bobby Tables
    injection = "Publisher'); DROP TABLE Publishers; --"
    dialog.txt_name.setText(injection)
    
    mock_repo.update.return_value = True
    dialog._save()
    
    assert sample_pub.publisher_name == injection
    # Repository is responsible for parameterization, but dialog should pass it through safely.
    mock_repo.update.assert_called_once()

def test_publisher_mutation_empty_name(qtbot, mock_repo, sample_pub):
    dialog = PublisherDetailsDialog(sample_pub, mock_repo)
    qtbot.addWidget(dialog)
    
    dialog.txt_name.setText("   ") # Only whitespace
    
    dialog._save()
    
    # Should return early and NOT call update
    mock_repo.update.assert_not_called()

def test_publisher_mutation_special_chars(qtbot, mock_repo, sample_pub):
    dialog = PublisherDetailsDialog(sample_pub, mock_repo)
    qtbot.addWidget(dialog)
    
    # Emoji, null bytes (if QLineEdit allows), non-latin
    special = "🏢 Publisher \x00 日本語"
    dialog.txt_name.setText(special)
    
    mock_repo.update.return_value = True
    dialog._save()
    
    assert sample_pub.publisher_name == special
    mock_repo.update.assert_called_once()
