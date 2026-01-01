"""
Level 1 Logic Tests for ChipTrayWidget.
Per TESTING.md: Tests the happy path and polite failures.
"""
import pytest
from unittest.mock import MagicMock, patch
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

from src.presentation.widgets.chip_tray_widget import Chip, ChipTrayWidget


class TestChip:
    """Tests for the Chip component."""

    def test_chip_initialization(self, qtbot):
        """Test chip is created with correct properties."""
        chip = Chip(entity_id=1, label="Test Artist", icon_char="🎤")
        qtbot.addWidget(chip)
        
        assert chip.entity_id == 1
        assert chip.label_text == "Test Artist"  # Fixed: label_text not label

    def test_chip_mixed_state(self, qtbot):
        """Test chip with mixed state has correct property."""
        chip = Chip(entity_id=-1, label="3 Mixed", icon_char="🔀", is_mixed=True)
        qtbot.addWidget(chip)
        
        assert chip.property("state") == "mixed"
        assert chip.is_mixed is True

    def test_chip_click_signal(self, qtbot):
        """Test clicking chip emits clicked signal."""
        chip = Chip(entity_id=42, label="Clickable", icon_char="🎵")
        qtbot.addWidget(chip)
        
        with qtbot.waitSignal(chip.clicked, timeout=1000) as blocker:
            qtbot.mouseClick(chip, Qt.MouseButton.LeftButton)
        
        assert blocker.args == [42, "Clickable"]


class TestChipTrayWidget:
    """Tests for the ChipTrayWidget container."""

    def test_initialization(self, qtbot):
        """Test tray initializes with add button only."""
        tray = ChipTrayWidget()
        qtbot.addWidget(tray)
        
        assert tray.btn_add is not None  # Fixed: btn_add not add_btn
        assert tray.flow_layout is not None

    def test_add_chip(self, qtbot):
        """Test adding a chip to the tray."""
        tray = ChipTrayWidget()
        qtbot.addWidget(tray)
        
        tray.add_chip(1, "Artist 1", "🎤")
        
        # Check via get_names instead of private _chips
        assert tray.get_names() == ["Artist 1"]

    def test_add_multiple_chips(self, qtbot):
        """Test adding multiple chips."""
        tray = ChipTrayWidget()
        qtbot.addWidget(tray)
        
        tray.add_chip(1, "Artist 1", "🎤")
        tray.add_chip(2, "Artist 2", "🎸")
        tray.add_chip(3, "Artist 3", "🥁")
        
        assert tray.get_names() == ["Artist 1", "Artist 2", "Artist 3"]

    def test_remove_chip(self, qtbot):
        """Test removing a chip by ID."""
        tray = ChipTrayWidget()
        qtbot.addWidget(tray)
        
        tray.add_chip(1, "Artist 1", "🎤")
        tray.add_chip(2, "Artist 2", "🎸")
        tray.remove_chip(1)
        
        assert tray.get_names() == ["Artist 2"]

    def test_clear_chips(self, qtbot):
        """Test clearing all chips."""
        tray = ChipTrayWidget()
        qtbot.addWidget(tray)
        
        tray.add_chip(1, "Artist 1", "🎤")
        tray.add_chip(2, "Artist 2", "🎸")
        tray.clear()
        
        assert tray.get_names() == []
        # Add button should still exist
        assert tray.btn_add is not None

    def test_set_chips_bulk(self, qtbot):
        """Test bulk setting chips replaces existing."""
        tray = ChipTrayWidget()
        qtbot.addWidget(tray)
        
        # Add initial chip
        tray.add_chip(99, "Old Artist", "🎹")
        
        # Bulk set new chips
        new_chips = [
            (1, "New Artist 1", "🎤", False),
            (2, "New Artist 2", "🎸", False),
        ]
        tray.set_chips(new_chips)
        
        assert tray.get_names() == ["New Artist 1", "New Artist 2"]

    def test_add_button_signal(self, qtbot):
        """Test add button emits add_requested signal."""
        tray = ChipTrayWidget()
        qtbot.addWidget(tray)
        
        # GlowButton is a complex wrapper; directly emit clicked signal
        with qtbot.waitSignal(tray.add_requested, timeout=1000):
            tray.btn_add.clicked.emit()

    def test_remove_with_confirmation(self, qtbot):
        """Test chip removal with confirmation dialog."""
        tray = ChipTrayWidget(confirm_removal=True)
        qtbot.addWidget(tray)
        
        tray.add_chip(1, "Artist To Remove", "🎤")
        
        # Mock the confirmation dialog to return Yes
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            with qtbot.waitSignal(tray.chip_remove_requested, timeout=1000) as blocker:
                tray._on_remove_requested(1, "Artist To Remove")
        
        assert blocker.args == [1, "Artist To Remove"]

    def test_remove_cancelled(self, qtbot):
        """Test chip removal cancelled by user."""
        tray = ChipTrayWidget(confirm_removal=True)
        qtbot.addWidget(tray)
        
        tray.add_chip(1, "Artist To Keep", "🎤")
        
        # Mock the confirmation dialog to return No
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
            # Signal should NOT be emitted
            signal_emitted = False
            def on_remove(entity_id, label):
                nonlocal signal_emitted
                signal_emitted = True
            tray.chip_remove_requested.connect(on_remove)
            
            tray._on_remove_requested(1, "Artist To Keep")
            
            assert not signal_emitted

    def test_get_names_empty(self, qtbot):
        """Test get_names returns empty list when no chips."""
        tray = ChipTrayWidget()
        qtbot.addWidget(tray)
        
        assert tray.get_names() == []
