import pytest
from PyQt6.QtCore import Qt, QPoint, QRect, QPointF
from PyQt6.QtGui import QMouseEvent, QEnterEvent
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtWidgets import QToolTip, QWidget
from unittest.mock import MagicMock, patch
from src.presentation.widgets.seek_slider import SeekSlider

class TestSeekSlider:
    @pytest.fixture
    def slider(self, qtbot):
        slider = SeekSlider()
        qtbot.addWidget(slider)
        slider.resize(100, 30)
        return slider

    @pytest.fixture
    def mock_player(self):
        player = MagicMock(spec=QMediaPlayer)
        return player

    def test_initialization(self, slider):
        assert slider.hasMouseTracking() is True
        assert slider.total_duration_secs == 0



    def test_duration_changed(self, slider):
        # 120,000 ms = 120 seconds = 2 minutes
        slider.updateDuration(120000)
        assert slider.total_duration_secs == 120.0
        assert slider.maximum() == 120000

    def test_update_tooltip_logic(self, slider):
        slider.updateDuration(120000) # 2 mins total
        
        # Mock event at middle of slider (50%)
        event = MagicMock()
        event.position().x.return_value = 50 
        slider.width = MagicMock(return_value=100)
        
        # Test internal logic indirectly via side effects or just call private method for unit testing logic
        # Ideally we test public behavior, but verifying tooltip text is hard without mocking QToolTip
        
        with patch('PyQt6.QtWidgets.QToolTip.showText') as mock_show:
            event.position().toPoint.return_value = QPoint(50, 0)
            
            slider._update_tooltip(event)
            
            # 50% of 2:00 is 1:00. Remaining is 1:00
            expected_text = "01:00 / -01:00"
            mock_show.assert_called()
            args = mock_show.call_args[0]
            assert args[1] == expected_text

    def test_mouse_press_seek(self, slider, qtbot):
        slider.updateDuration(100000) # 100s
        slider.width = MagicMock(return_value=100)
        
        # Click at 25% mark
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(25, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        
        with patch.object(slider, 'width', return_value=100):
            with qtbot.waitSignal(slider.seekRequested, timeout=1000) as blocker:
                slider.mousePressEvent(event)
                
            # Allow tolerance
            assert blocker.signal_triggered
            args = blocker.args
            assert 24000 <= args[0] <= 26000

    def test_mouse_press_ignore_right_click(self, slider, qtbot):
        slider.updateDuration(100000)
        
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(25, 10),
            Qt.MouseButton.RightButton,
            Qt.MouseButton.RightButton,
            Qt.KeyboardModifier.NoModifier
        )
        
        # Should NOT emit signal
        with qtbot.assertNotEmitted(slider.seekRequested):
             slider.mousePressEvent(event)

    def test_size_hint(self, slider):
        hint = slider.sizeHint()
        assert hint.height() == 30

    def test_tooltip_events(self, slider):
        """Test enter and move events trigger tooltip update"""
        slider.updateDuration(100000)
        
        # Enter Event
        event_enter = MagicMock()
        event_enter.position().x.return_value = 50
        event_enter.position().toPoint.return_value = QPoint(50, 0)
        
        # We need to ensure the event type allows enter/move?
        # Actually we just call the methods directly
        
        with patch('src.presentation.widgets.seek_slider.SeekSlider._update_tooltip') as mock_update:
            with patch('PyQt6.QtWidgets.QSlider.enterEvent'):
                slider.enterEvent(event_enter)
                mock_update.assert_called_once()
            
            mock_update.reset_mock()
            
            with patch('PyQt6.QtWidgets.QSlider.mouseMoveEvent'):
                slider.mouseMoveEvent(event_enter)
                mock_update.assert_called_once()

    def test_tooltip_zero_duration(self, slider):
        """Test tooltip does not show if duration is 0"""
        slider.updateDuration(0)
        assert slider.total_duration_secs == 0
        
        event = MagicMock()
        
        with patch('PyQt6.QtWidgets.QToolTip.showText') as mock_show:
            slider._update_tooltip(event)
            mock_show.assert_not_called()
