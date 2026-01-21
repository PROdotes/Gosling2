"""
T-Tools: Library Tools Window

An independent QMainWindow for global entity management.
Provides tabs for managing Tags, Artists, Albums, Publishers, and viewing Library Health.
"""
from typing import Optional, TYPE_CHECKING
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QSplitter, QFrame, QLabel, QPushButton, QLineEdit, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QIcon, QAction

from ..widgets.glow_factory import GlowButton, GlowLineEdit

if TYPE_CHECKING:
    from ...business.services.tag_service import TagService
    from ...business.services.contributor_service import ContributorService
    from ...business.services.publisher_service import PublisherService
    from ...business.services.album_service import AlbumService
    from ...business.services.settings_manager import SettingsManager


class ToolsWindow(QMainWindow):
    """
    Global Library Tools Window.

    Provides entity management for:
    - Tags (Phase 1)
    - Artists (Phase 2)
    - Albums (Phase 3)
    - Publishers (Phase 2)
    - Health Dashboard (Phase 1)
    """

    # Emitted when data changes that might affect main window
    data_changed = pyqtSignal()

    # Window geometry settings keys
    GEOMETRY_KEY = "tools_window_geometry"
    ACTIVE_TAB_KEY = "tools_window_active_tab"

    def __init__(
        self,
        tag_service: "TagService",
        settings_manager: "SettingsManager",
        contributor_service: Optional["ContributorService"] = None,
        publisher_service: Optional["PublisherService"] = None,
        album_service: Optional["AlbumService"] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.tag_service = tag_service
        self.settings_manager = settings_manager
        self.contributor_service = contributor_service
        self.publisher_service = publisher_service
        self.album_service = album_service

        self.setWindowTitle("🔧 Library Tools")
        self.setObjectName("ToolsWindow")
        self.setMinimumSize(800, 500)

        # Allow this window to be independent (not always on top of parent)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowMinMaxButtonsHint
        )

        self._init_ui()
        self._restore_geometry()
        self._restore_active_tab()

    def _init_ui(self):
        """Build the main UI structure."""
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setObjectName("ToolsTabs")
        self.tabs.setDocumentMode(True)  # Cleaner look

        # Create tabs (Phase 1: Tags + Health)
        self.tags_tab = self._create_tags_tab()
        self.health_tab = self._create_health_tab()

        # Add tabs with icons - Health is last (final pill)
        self.tabs.addTab(self.tags_tab, "🏷️ Tags")

        # Artists tab (Phase 2)
        if self.contributor_service:
            self.artists_tab = self._create_artists_tab()
            self.tabs.addTab(self.artists_tab, "🎭 Artists")
        else:
            self._add_placeholder_tab("🎭 Artists", "Service not available")

        # Albums tab (Phase 3)
        if self.album_service:
            self.albums_tab = self._create_albums_tab()
            self.tabs.addTab(self.albums_tab, "💿 Albums")
        else:
            self._add_placeholder_tab("💿 Albums", "Service not available")

        # Publishers tab (Phase 2)
        if self.publisher_service:
            self.publishers_tab = self._create_publishers_tab()
            self.tabs.addTab(self.publishers_tab, "🏢 Publishers")
        else:
            self._add_placeholder_tab("🏢 Publishers", "Service not available")

        # Health tab is always last
        self.tabs.addTab(self.health_tab, "⚠️ Health")

        layout.addWidget(self.tabs)

    def _add_placeholder_tab(self, title: str, message: str):
        """Add a placeholder tab for features not yet implemented."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl = QLabel(message)
        lbl.setObjectName("PlaceholderLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

        self.tabs.addTab(widget, title)

    # ─────────────────────────────────────────────────────────────────
    # TAGS TAB
    # ─────────────────────────────────────────────────────────────────

    def _create_tags_tab(self) -> QWidget:
        """Create the Tags management tab."""
        widget = QWidget()
        widget.setObjectName("TagsTab")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        # Search
        self.tags_search = GlowLineEdit()
        self.tags_search.setPlaceholderText("Filter tags...")
        self.tags_search.setFixedWidth(200)
        self.tags_search.textChanged.connect(self._on_tags_filter_changed)
        toolbar.addWidget(self.tags_search)

        # Category filter (TODO: populate from DB)
        toolbar.addWidget(QLabel("Category:"))
        self.tags_category_filter = GlowLineEdit()
        self.tags_category_filter.setPlaceholderText("All")
        self.tags_category_filter.setFixedWidth(100)
        self.tags_category_filter.textChanged.connect(self._refresh_tags_list)
        toolbar.addWidget(self.tags_category_filter)

        # Orphans only
        self.tags_orphans_only = QCheckBox("Orphans Only")
        self.tags_orphans_only.setObjectName("OrphansOnlyCheckbox")
        self.tags_orphans_only.toggled.connect(self._refresh_tags_list)
        toolbar.addWidget(self.tags_orphans_only)

        toolbar.addStretch()

        # Nuke Orphans Button
        self.btn_nuke_orphan_tags = GlowButton("🗑️ Nuke All Orphans")
        self.btn_nuke_orphan_tags.setObjectName("NukeButton")
        self.btn_nuke_orphan_tags.clicked.connect(self._nuke_orphan_tags)
        toolbar.addWidget(self.btn_nuke_orphan_tags)

        layout.addLayout(toolbar)

        # Splitter: List | Inspector
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("TagsSplitter")

        # Left: Table
        self.tags_table = QTableWidget()
        self.tags_table.setObjectName("TagsTable")
        self.tags_table.setColumnCount(3)
        self.tags_table.setHorizontalHeaderLabels(["Name", "Category", "Usage"])
        self.tags_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tags_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tags_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tags_table.verticalHeader().setVisible(False)
        self.tags_table.horizontalHeader().setStretchLastSection(True)
        self.tags_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tags_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tags_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.tags_table.itemSelectionChanged.connect(self._on_tag_selected)
        splitter.addWidget(self.tags_table)

        # Right: Inspector
        inspector = QFrame()
        inspector.setObjectName("TagInspector")
        inspector.setMinimumWidth(250)
        inspector_layout = QVBoxLayout(inspector)
        inspector_layout.setContentsMargins(15, 15, 15, 15)
        inspector_layout.setSpacing(12)

        # Inspector Header
        lbl_inspector = QLabel("INSPECTOR")
        lbl_inspector.setObjectName("InspectorHeader")
        inspector_layout.addWidget(lbl_inspector)

        # Name field
        lbl_name = QLabel("TAG NAME")
        lbl_name.setObjectName("FieldLabel")
        inspector_layout.addWidget(lbl_name)

        self.tag_name_input = GlowLineEdit()
        self.tag_name_input.setPlaceholderText("Select a tag...")
        self.tag_name_input.setEnabled(False)
        inspector_layout.addWidget(self.tag_name_input)

        # Category field
        lbl_cat = QLabel("CATEGORY")
        lbl_cat.setObjectName("FieldLabel")
        inspector_layout.addWidget(lbl_cat)

        self.tag_category_input = GlowLineEdit()
        self.tag_category_input.setPlaceholderText("e.g., Genre, Mood")
        self.tag_category_input.setEnabled(False)
        inspector_layout.addWidget(self.tag_category_input)

        # Usage display
        self.tag_usage_label = QLabel("Usage: -")
        self.tag_usage_label.setObjectName("UsageLabel")
        inspector_layout.addWidget(self.tag_usage_label)

        inspector_layout.addStretch()

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_tag_save = GlowButton("Save")
        self.btn_tag_save.setObjectName("SaveButton")
        self.btn_tag_save.setEnabled(False)
        self.btn_tag_save.clicked.connect(self._save_tag)
        btn_row.addWidget(self.btn_tag_save)

        self.btn_tag_merge = GlowButton("Merge...")
        self.btn_tag_merge.setEnabled(False)
        self.btn_tag_merge.clicked.connect(self._merge_tag)
        btn_row.addWidget(self.btn_tag_merge)

        self.btn_tag_delete = GlowButton("Delete")
        self.btn_tag_delete.setObjectName("DeleteButton")
        self.btn_tag_delete.setEnabled(False)
        self.btn_tag_delete.clicked.connect(self._delete_tag)
        btn_row.addWidget(self.btn_tag_delete)

        inspector_layout.addLayout(btn_row)

        splitter.addWidget(inspector)
        splitter.setSizes([500, 300])

        layout.addWidget(splitter)

        # Store current selection
        self._current_tag_id = None
        self._current_tag_usage = 0

        return widget

    def _refresh_tags_list(self):
        """Reload the tags table from the database."""
        # Get filter values
        category = self.tags_category_filter.text().strip() or None
        orphans_only = self.tags_orphans_only.isChecked()
        search_text = self.tags_search.text().strip().lower()

        # Fetch data
        tags_with_usage = self.tag_service.get_all_with_usage(
            category=category,
            orphans_only=orphans_only
        )

        # Apply text filter
        if search_text:
            tags_with_usage = [
                (t, u) for t, u in tags_with_usage
                if search_text in t.tag_name.lower()
            ]

        # Populate table
        self.tags_table.setRowCount(len(tags_with_usage))

        for row, (tag, usage) in enumerate(tags_with_usage):
            # Name
            name_item = QTableWidgetItem(tag.tag_name)
            name_item.setData(Qt.ItemDataRole.UserRole, tag.tag_id)
            self.tags_table.setItem(row, 0, name_item)

            # Category
            cat_item = QTableWidgetItem(tag.category or "—")
            self.tags_table.setItem(row, 1, cat_item)

            # Usage
            usage_item = QTableWidgetItem(str(usage))
            usage_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            # Highlight orphans
            if usage == 0:
                usage_item.setForeground(Qt.GlobalColor.red)
            self.tags_table.setItem(row, 2, usage_item)

        # Update orphan count in nuke button
        orphan_count = self.tag_service.get_orphan_count(category=category)
        self.btn_nuke_orphan_tags.setText(f"🗑️ Nuke All Orphans ({orphan_count})")
        self.btn_nuke_orphan_tags.setEnabled(orphan_count > 0)

    def _on_tags_filter_changed(self, text: str):
        """Handle search text change."""
        self._refresh_tags_list()

    def _on_tag_selected(self):
        """Handle tag selection in the table."""
        rows = self.tags_table.selectedItems()
        if not rows:
            self._clear_tag_inspector()
            return

        # Get tag ID from first column
        row = self.tags_table.currentRow()
        name_item = self.tags_table.item(row, 0)
        if not name_item:
            return

        tag_id = name_item.data(Qt.ItemDataRole.UserRole)
        tag = self.tag_service.get_by_id(tag_id)
        if not tag:
            return

        # Get usage
        usage = int(self.tags_table.item(row, 2).text())

        # Populate inspector
        self._current_tag_id = tag_id
        self._current_tag_usage = usage

        self.tag_name_input.setText(tag.tag_name)
        self.tag_name_input.setEnabled(True)

        self.tag_category_input.setText(tag.category or "")
        self.tag_category_input.setEnabled(True)

        self.tag_usage_label.setText(f"Usage: {usage} songs")

        # Enable buttons
        self.btn_tag_save.setEnabled(True)
        self.btn_tag_merge.setEnabled(True)
        self.btn_tag_delete.setEnabled(True)

    def _clear_tag_inspector(self):
        """Clear the tag inspector fields."""
        self._current_tag_id = None
        self._current_tag_usage = 0

        self.tag_name_input.clear()
        self.tag_name_input.setEnabled(False)

        self.tag_category_input.clear()
        self.tag_category_input.setEnabled(False)

        self.tag_usage_label.setText("Usage: -")

        self.btn_tag_save.setEnabled(False)
        self.btn_tag_merge.setEnabled(False)
        self.btn_tag_delete.setEnabled(False)

    def _save_tag(self):
        """Save changes to the selected tag."""
        if not self._current_tag_id:
            return

        new_name = self.tag_name_input.text().strip()
        new_category = self.tag_category_input.text().strip() or None

        if not new_name:
            QMessageBox.warning(self, "Invalid Name", "Tag name cannot be empty.")
            return

        # Get current tag
        tag = self.tag_service.get_by_id(self._current_tag_id)
        if not tag:
            return

        # Check for name collision (merge scenario)
        existing = self.tag_service.find_by_name(new_name, new_category)
        if existing and existing.tag_id != tag.tag_id:
            # Merge into existing
            result = QMessageBox.question(
                self, "Merge Tags?",
                f"A tag named '{new_name}' already exists in category '{new_category or 'None'}'.\n\n"
                f"Do you want to merge into the existing tag?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if result == QMessageBox.StandardButton.Yes:
                if self.tag_service.merge_tags(tag.tag_id, existing.tag_id):
                    self._refresh_tags_list()
                    self._clear_tag_inspector()
                    self.data_changed.emit()
            return

        # Update tag
        tag.tag_name = new_name
        tag.category = new_category
        if self.tag_service.update(tag):
            self._refresh_tags_list()
            self.data_changed.emit()
        else:
            QMessageBox.warning(self, "Save Failed", "Could not update the tag.")

    def _merge_tag(self):
        """Open merge dialog for the selected tag."""
        if not self._current_tag_id:
            return

        # TODO: Implement a proper merge target picker dialog
        # For now, show a simple input dialog
        from PyQt6.QtWidgets import QInputDialog

        tag = self.tag_service.get_by_id(self._current_tag_id)
        if not tag:
            return

        target_name, ok = QInputDialog.getText(
            self, "Merge Tag",
            f"Merge '{tag.tag_name}' into which tag?\n(Enter the target tag name):"
        )

        if not ok or not target_name.strip():
            return

        target = self.tag_service.find_by_name(target_name.strip(), tag.category)
        if not target:
            QMessageBox.warning(
                self, "Not Found",
                f"No tag named '{target_name}' found in category '{tag.category or 'None'}'."
            )
            return

        if target.tag_id == tag.tag_id:
            QMessageBox.warning(self, "Invalid", "Cannot merge a tag into itself.")
            return

        if self.tag_service.merge_tags(tag.tag_id, target.tag_id):
            self._refresh_tags_list()
            self._clear_tag_inspector()
            self.data_changed.emit()
        else:
            QMessageBox.warning(self, "Merge Failed", "Could not merge the tags.")

    def _delete_tag(self):
        """Delete the selected tag."""
        if not self._current_tag_id:
            return

        tag = self.tag_service.get_by_id(self._current_tag_id)
        if not tag:
            return

        # No confirmation for orphans (0 usage)
        if self._current_tag_usage > 0:
            result = QMessageBox.question(
                self, "Delete Tag?",
                f"'{tag.tag_name}' is used by {self._current_tag_usage} song(s).\n\n"
                f"Deleting will unlink it from all songs. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if result != QMessageBox.StandardButton.Yes:
                return

        if self.tag_service.delete_tag(self._current_tag_id):
            self._refresh_tags_list()
            self._clear_tag_inspector()
            self.data_changed.emit()
        else:
            QMessageBox.warning(self, "Delete Failed", "Could not delete the tag.")

    def _nuke_orphan_tags(self):
        """Delete all orphan tags."""
        category = self.tags_category_filter.text().strip() or None
        count = self.tag_service.get_orphan_count(category=category)

        if count == 0:
            return

        # Per design: no confirmation for orphan nuking
        deleted = self.tag_service.delete_all_orphans(category=category)
        self._refresh_tags_list()
        self.data_changed.emit()

        # Show feedback
        QMessageBox.information(
            self, "Orphans Deleted",
            f"Successfully deleted {deleted} orphan tag(s)."
        )

    # ─────────────────────────────────────────────────────────────────
    # ARTISTS TAB
    # ─────────────────────────────────────────────────────────────────

    def _create_artists_tab(self) -> QWidget:
        """Create the Artists management tab."""
        widget = QWidget()
        widget.setObjectName("ArtistsTab")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        # Search
        self.artists_search = GlowLineEdit()
        self.artists_search.setPlaceholderText("Filter artists...")
        self.artists_search.setFixedWidth(200)
        self.artists_search.textChanged.connect(self._refresh_artists_list)
        toolbar.addWidget(self.artists_search)

        # Orphans only
        self.artists_orphans_only = QCheckBox("Orphans Only")
        self.artists_orphans_only.setObjectName("OrphansOnlyCheckbox")
        self.artists_orphans_only.toggled.connect(self._refresh_artists_list)
        toolbar.addWidget(self.artists_orphans_only)

        toolbar.addStretch()

        # Nuke Orphans Button
        self.btn_nuke_orphan_artists = GlowButton("🗑️ Nuke All Orphans")
        self.btn_nuke_orphan_artists.setObjectName("NukeButton")
        self.btn_nuke_orphan_artists.clicked.connect(self._nuke_orphan_artists)
        toolbar.addWidget(self.btn_nuke_orphan_artists)

        layout.addLayout(toolbar)

        # Splitter: List | Inspector
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("ArtistsSplitter")

        # Left: Table
        self.artists_table = QTableWidget()
        self.artists_table.setObjectName("ArtistsTable")
        self.artists_table.setColumnCount(3)
        self.artists_table.setHorizontalHeaderLabels(["Name", "Type", "Usage"])
        self.artists_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.artists_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.artists_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.artists_table.verticalHeader().setVisible(False)
        self.artists_table.horizontalHeader().setStretchLastSection(True)
        self.artists_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.artists_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.artists_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.artists_table.itemSelectionChanged.connect(self._on_artist_selected)
        splitter.addWidget(self.artists_table)

        # Right: Inspector
        inspector = QFrame()
        inspector.setObjectName("ArtistInspector")
        inspector.setMinimumWidth(250)
        inspector_layout = QVBoxLayout(inspector)
        inspector_layout.setContentsMargins(15, 15, 15, 15)
        inspector_layout.setSpacing(12)

        # Inspector Header
        lbl_inspector = QLabel("INSPECTOR")
        lbl_inspector.setObjectName("InspectorHeader")
        inspector_layout.addWidget(lbl_inspector)

        # Name field
        lbl_name = QLabel("ARTIST NAME")
        lbl_name.setObjectName("FieldLabel")
        inspector_layout.addWidget(lbl_name)

        self.artist_name_input = GlowLineEdit()
        self.artist_name_input.setPlaceholderText("Select an artist...")
        self.artist_name_input.setEnabled(False)
        inspector_layout.addWidget(self.artist_name_input)

        # Usage display
        self.artist_usage_label = QLabel("Usage: -")
        self.artist_usage_label.setObjectName("UsageLabel")
        inspector_layout.addWidget(self.artist_usage_label)

        inspector_layout.addStretch()

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_artist_delete = GlowButton("Delete")
        self.btn_artist_delete.setObjectName("DeleteButton")
        self.btn_artist_delete.setEnabled(False)
        self.btn_artist_delete.clicked.connect(self._delete_artist)
        btn_row.addWidget(self.btn_artist_delete)

        inspector_layout.addLayout(btn_row)

        splitter.addWidget(inspector)
        splitter.setSizes([500, 300])

        layout.addWidget(splitter)

        # Store current selection
        self._current_artist_id = None
        self._current_artist_usage = 0

        return widget

    def _refresh_artists_list(self):
        """Reload the artists table from the database."""
        if not self.contributor_service:
            return

        orphans_only = self.artists_orphans_only.isChecked()
        search_text = self.artists_search.text().strip().lower()

        # Fetch data
        artists_with_usage = self.contributor_service.get_all_with_usage(orphans_only=orphans_only)

        # Apply text filter
        if search_text:
            artists_with_usage = [
                (a, u) for a, u in artists_with_usage
                if search_text in a.name.lower()
            ]

        # Populate table
        self.artists_table.setRowCount(len(artists_with_usage))

        for row, (artist, usage) in enumerate(artists_with_usage):
            # Name
            name_item = QTableWidgetItem(artist.name)
            name_item.setData(Qt.ItemDataRole.UserRole, artist.contributor_id)
            self.artists_table.setItem(row, 0, name_item)

            # Type
            type_item = QTableWidgetItem(artist.type or "person")
            self.artists_table.setItem(row, 1, type_item)

            # Usage
            usage_item = QTableWidgetItem(str(usage))
            usage_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if usage == 0:
                usage_item.setForeground(Qt.GlobalColor.red)
            self.artists_table.setItem(row, 2, usage_item)

        # Update orphan count in nuke button
        orphan_count = self.contributor_service.get_orphan_count()
        self.btn_nuke_orphan_artists.setText(f"🗑️ Nuke All Orphans ({orphan_count})")
        self.btn_nuke_orphan_artists.setEnabled(orphan_count > 0)

    def _on_artist_selected(self):
        """Handle artist selection in the table."""
        rows = self.artists_table.selectedItems()
        if not rows:
            self._clear_artist_inspector()
            return

        row = self.artists_table.currentRow()
        name_item = self.artists_table.item(row, 0)
        if not name_item:
            return

        artist_id = name_item.data(Qt.ItemDataRole.UserRole)
        usage = int(self.artists_table.item(row, 2).text())

        self._current_artist_id = artist_id
        self._current_artist_usage = usage

        self.artist_name_input.setText(name_item.text())
        self.artist_name_input.setEnabled(False)  # Read-only for now
        self.artist_usage_label.setText(f"Usage: {usage} credits")
        self.btn_artist_delete.setEnabled(True)

    def _clear_artist_inspector(self):
        """Clear the artist inspector fields."""
        self._current_artist_id = None
        self._current_artist_usage = 0
        self.artist_name_input.clear()
        self.artist_name_input.setEnabled(False)
        self.artist_usage_label.setText("Usage: -")
        self.btn_artist_delete.setEnabled(False)

    def _delete_artist(self):
        """Delete the selected artist."""
        if not self._current_artist_id or not self.contributor_service:
            return

        if self._current_artist_usage > 0:
            result = QMessageBox.question(
                self, "Delete Artist?",
                f"This artist has {self._current_artist_usage} credit(s).\n\n"
                f"Deleting will remove all credits. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if result != QMessageBox.StandardButton.Yes:
                return

        if self.contributor_service.delete_contributor(self._current_artist_id):
            self._refresh_artists_list()
            self._clear_artist_inspector()
            self.data_changed.emit()
        else:
            QMessageBox.warning(self, "Delete Failed", "Could not delete the artist.")

    def _nuke_orphan_artists(self):
        """Delete all orphan artists."""
        if not self.contributor_service:
            return

        count = self.contributor_service.get_orphan_count()
        if count == 0:
            return

        deleted = self.contributor_service.delete_all_orphans()
        self._refresh_artists_list()
        self.data_changed.emit()

        QMessageBox.information(
            self, "Orphans Deleted",
            f"Successfully deleted {deleted} orphan artist(s)."
        )

    # ─────────────────────────────────────────────────────────────────
    # PUBLISHERS TAB
    # ─────────────────────────────────────────────────────────────────

    def _create_publishers_tab(self) -> QWidget:
        """Create the Publishers management tab."""
        widget = QWidget()
        widget.setObjectName("PublishersTab")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        # Search
        self.publishers_search = GlowLineEdit()
        self.publishers_search.setPlaceholderText("Filter publishers...")
        self.publishers_search.setFixedWidth(200)
        self.publishers_search.textChanged.connect(self._refresh_publishers_list)
        toolbar.addWidget(self.publishers_search)

        # Orphans only
        self.publishers_orphans_only = QCheckBox("Orphans Only")
        self.publishers_orphans_only.setObjectName("OrphansOnlyCheckbox")
        self.publishers_orphans_only.toggled.connect(self._refresh_publishers_list)
        toolbar.addWidget(self.publishers_orphans_only)

        toolbar.addStretch()

        # Nuke Orphans Button
        self.btn_nuke_orphan_publishers = GlowButton("🗑️ Nuke All Orphans")
        self.btn_nuke_orphan_publishers.setObjectName("NukeButton")
        self.btn_nuke_orphan_publishers.clicked.connect(self._nuke_orphan_publishers)
        toolbar.addWidget(self.btn_nuke_orphan_publishers)

        layout.addLayout(toolbar)

        # Splitter: List | Inspector
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("PublishersSplitter")

        # Left: Table
        self.publishers_table = QTableWidget()
        self.publishers_table.setObjectName("PublishersTable")
        self.publishers_table.setColumnCount(2)
        self.publishers_table.setHorizontalHeaderLabels(["Name", "Usage"])
        self.publishers_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.publishers_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.publishers_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.publishers_table.verticalHeader().setVisible(False)
        self.publishers_table.horizontalHeader().setStretchLastSection(True)
        self.publishers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.publishers_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.publishers_table.itemSelectionChanged.connect(self._on_publisher_selected)
        splitter.addWidget(self.publishers_table)

        # Right: Inspector
        inspector = QFrame()
        inspector.setObjectName("PublisherInspector")
        inspector.setMinimumWidth(250)
        inspector_layout = QVBoxLayout(inspector)
        inspector_layout.setContentsMargins(15, 15, 15, 15)
        inspector_layout.setSpacing(12)

        # Inspector Header
        lbl_inspector = QLabel("INSPECTOR")
        lbl_inspector.setObjectName("InspectorHeader")
        inspector_layout.addWidget(lbl_inspector)

        # Name field
        lbl_name = QLabel("PUBLISHER NAME")
        lbl_name.setObjectName("FieldLabel")
        inspector_layout.addWidget(lbl_name)

        self.publisher_name_input = GlowLineEdit()
        self.publisher_name_input.setPlaceholderText("Select a publisher...")
        self.publisher_name_input.setEnabled(False)
        inspector_layout.addWidget(self.publisher_name_input)

        # Usage display
        self.publisher_usage_label = QLabel("Usage: -")
        self.publisher_usage_label.setObjectName("UsageLabel")
        inspector_layout.addWidget(self.publisher_usage_label)

        inspector_layout.addStretch()

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_publisher_delete = GlowButton("Delete")
        self.btn_publisher_delete.setObjectName("DeleteButton")
        self.btn_publisher_delete.setEnabled(False)
        self.btn_publisher_delete.clicked.connect(self._delete_publisher)
        btn_row.addWidget(self.btn_publisher_delete)

        inspector_layout.addLayout(btn_row)

        splitter.addWidget(inspector)
        splitter.setSizes([500, 300])

        layout.addWidget(splitter)

        # Store current selection
        self._current_publisher_id = None
        self._current_publisher_usage = 0

        return widget

    def _refresh_publishers_list(self):
        """Reload the publishers table from the database."""
        if not self.publisher_service:
            return

        orphans_only = self.publishers_orphans_only.isChecked()
        search_text = self.publishers_search.text().strip().lower()

        # Fetch data
        publishers_with_usage = self.publisher_service.get_all_with_usage(orphans_only=orphans_only)

        # Apply text filter
        if search_text:
            publishers_with_usage = [
                (p, u) for p, u in publishers_with_usage
                if search_text in p.publisher_name.lower()
            ]

        # Populate table
        self.publishers_table.setRowCount(len(publishers_with_usage))

        for row, (pub, usage) in enumerate(publishers_with_usage):
            # Name
            name_item = QTableWidgetItem(pub.publisher_name)
            name_item.setData(Qt.ItemDataRole.UserRole, pub.publisher_id)
            self.publishers_table.setItem(row, 0, name_item)

            # Usage
            usage_item = QTableWidgetItem(str(usage))
            usage_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if usage == 0:
                usage_item.setForeground(Qt.GlobalColor.red)
            self.publishers_table.setItem(row, 1, usage_item)

        # Update orphan count in nuke button
        orphan_count = self.publisher_service.get_orphan_count()
        self.btn_nuke_orphan_publishers.setText(f"🗑️ Nuke All Orphans ({orphan_count})")
        self.btn_nuke_orphan_publishers.setEnabled(orphan_count > 0)

    def _on_publisher_selected(self):
        """Handle publisher selection in the table."""
        rows = self.publishers_table.selectedItems()
        if not rows:
            self._clear_publisher_inspector()
            return

        row = self.publishers_table.currentRow()
        name_item = self.publishers_table.item(row, 0)
        if not name_item:
            return

        publisher_id = name_item.data(Qt.ItemDataRole.UserRole)
        usage = int(self.publishers_table.item(row, 1).text())

        self._current_publisher_id = publisher_id
        self._current_publisher_usage = usage

        self.publisher_name_input.setText(name_item.text())
        self.publisher_name_input.setEnabled(False)  # Read-only for now
        self.publisher_usage_label.setText(f"Usage: {usage} albums/songs")
        self.btn_publisher_delete.setEnabled(True)

    def _clear_publisher_inspector(self):
        """Clear the publisher inspector fields."""
        self._current_publisher_id = None
        self._current_publisher_usage = 0
        self.publisher_name_input.clear()
        self.publisher_name_input.setEnabled(False)
        self.publisher_usage_label.setText("Usage: -")
        self.btn_publisher_delete.setEnabled(False)

    def _delete_publisher(self):
        """Delete the selected publisher."""
        if not self._current_publisher_id or not self.publisher_service:
            return

        if self._current_publisher_usage > 0:
            result = QMessageBox.question(
                self, "Delete Publisher?",
                f"This publisher is used by {self._current_publisher_usage} album(s)/song(s).\n\n"
                f"Deleting will unlink it from all items. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if result != QMessageBox.StandardButton.Yes:
                return

        if self.publisher_service.delete(self._current_publisher_id):
            self._refresh_publishers_list()
            self._clear_publisher_inspector()
            self.data_changed.emit()
        else:
            QMessageBox.warning(self, "Delete Failed", "Could not delete the publisher.")

    def _nuke_orphan_publishers(self):
        """Delete all orphan publishers."""
        if not self.publisher_service:
            return

        count = self.publisher_service.get_orphan_count()
        if count == 0:
            return

        deleted = self.publisher_service.delete_all_orphans()
        self._refresh_publishers_list()
        self.data_changed.emit()

        QMessageBox.information(
            self, "Orphans Deleted",
            f"Successfully deleted {deleted} orphan publisher(s)."
        )

    # ─────────────────────────────────────────────────────────────────
    # ALBUMS TAB (Phase 3)
    # ─────────────────────────────────────────────────────────────────

    def _create_albums_tab(self) -> QWidget:
        """Create the Albums management tab."""
        widget = QWidget()
        widget.setObjectName("AlbumsTab")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        # Search
        self.albums_search = GlowLineEdit()
        self.albums_search.setPlaceholderText("Filter albums...")
        self.albums_search.setFixedWidth(200)
        self.albums_search.textChanged.connect(self._refresh_albums_list)
        toolbar.addWidget(self.albums_search)

        # Orphans only
        self.albums_orphans_only = QCheckBox("Empty Only")
        self.albums_orphans_only.setObjectName("OrphansOnlyCheckbox")
        self.albums_orphans_only.toggled.connect(self._refresh_albums_list)
        toolbar.addWidget(self.albums_orphans_only)

        toolbar.addStretch()

        # Nuke Orphans Button
        self.btn_nuke_orphan_albums = GlowButton("🗑️ Nuke All Empty")
        self.btn_nuke_orphan_albums.setObjectName("NukeButton")
        self.btn_nuke_orphan_albums.clicked.connect(self._nuke_orphan_albums)
        toolbar.addWidget(self.btn_nuke_orphan_albums)

        layout.addLayout(toolbar)

        # Splitter: List | Inspector
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("AlbumsSplitter")

        # Left: Table
        self.albums_table = QTableWidget()
        self.albums_table.setObjectName("AlbumsTable")
        self.albums_table.setColumnCount(4)
        self.albums_table.setHorizontalHeaderLabels(["Title", "Artist", "Year", "Songs"])
        self.albums_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.albums_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.albums_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.albums_table.verticalHeader().setVisible(False)
        self.albums_table.horizontalHeader().setStretchLastSection(True)
        self.albums_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.albums_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.albums_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.albums_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.albums_table.itemSelectionChanged.connect(self._on_album_selected)
        splitter.addWidget(self.albums_table)

        # Right: Inspector
        inspector = QFrame()
        inspector.setObjectName("AlbumInspector")
        inspector.setMinimumWidth(250)
        inspector_layout = QVBoxLayout(inspector)
        inspector_layout.setContentsMargins(15, 15, 15, 15)
        inspector_layout.setSpacing(12)

        # Inspector Header
        lbl_inspector = QLabel("INSPECTOR")
        lbl_inspector.setObjectName("InspectorHeader")
        inspector_layout.addWidget(lbl_inspector)

        # Title field
        lbl_title = QLabel("ALBUM TITLE")
        lbl_title.setObjectName("FieldLabel")
        inspector_layout.addWidget(lbl_title)

        self.album_title_input = GlowLineEdit()
        self.album_title_input.setPlaceholderText("Select an album...")
        self.album_title_input.setEnabled(False)
        inspector_layout.addWidget(self.album_title_input)

        # Artist field
        lbl_artist = QLabel("ARTIST")
        lbl_artist.setObjectName("FieldLabel")
        inspector_layout.addWidget(lbl_artist)

        self.album_artist_input = GlowLineEdit()
        self.album_artist_input.setPlaceholderText("—")
        self.album_artist_input.setEnabled(False)
        inspector_layout.addWidget(self.album_artist_input)

        # Year field
        lbl_year = QLabel("YEAR")
        lbl_year.setObjectName("FieldLabel")
        inspector_layout.addWidget(lbl_year)

        self.album_year_input = GlowLineEdit()
        self.album_year_input.setPlaceholderText("—")
        self.album_year_input.setEnabled(False)
        inspector_layout.addWidget(self.album_year_input)

        # Usage display
        self.album_usage_label = QLabel("Songs: —")
        self.album_usage_label.setObjectName("UsageLabel")
        inspector_layout.addWidget(self.album_usage_label)

        inspector_layout.addStretch()

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_album_delete = GlowButton("Delete")
        self.btn_album_delete.setObjectName("DeleteButton")
        self.btn_album_delete.setEnabled(False)
        self.btn_album_delete.clicked.connect(self._delete_album)
        btn_row.addWidget(self.btn_album_delete)

        inspector_layout.addLayout(btn_row)

        splitter.addWidget(inspector)
        splitter.setSizes([500, 300])

        layout.addWidget(splitter)

        # Store current selection
        self._current_album_id = None
        self._current_album_usage = 0

        return widget

    def _refresh_albums_list(self):
        """Reload the albums table from the database."""
        if not self.album_service:
            return

        orphans_only = self.albums_orphans_only.isChecked()
        search_text = self.albums_search.text().strip().lower()

        # Fetch data
        albums_with_usage = self.album_service.get_all_with_usage(orphans_only=orphans_only)

        # Apply text filter
        if search_text:
            albums_with_usage = [
                (a, u) for a, u in albums_with_usage
                if search_text in a.title.lower() or 
                   (a.album_artist and search_text in a.album_artist.lower())
            ]

        # Populate table
        self.albums_table.setRowCount(len(albums_with_usage))

        for row, (album, usage) in enumerate(albums_with_usage):
            # Title
            title_item = QTableWidgetItem(album.title or "—")
            title_item.setData(Qt.ItemDataRole.UserRole, album.album_id)
            self.albums_table.setItem(row, 0, title_item)

            # Artist
            artist_item = QTableWidgetItem(album.album_artist or "—")
            self.albums_table.setItem(row, 1, artist_item)

            # Year
            year_text = str(album.release_year) if album.release_year else "—"
            year_item = QTableWidgetItem(year_text)
            self.albums_table.setItem(row, 2, year_item)

            # Songs (Usage)
            usage_item = QTableWidgetItem(str(usage))
            usage_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if usage == 0:
                usage_item.setForeground(Qt.GlobalColor.red)
            self.albums_table.setItem(row, 3, usage_item)

        # Update orphan count in nuke button
        orphan_count = self.album_service.get_orphan_count()
        self.btn_nuke_orphan_albums.setText(f"🗑️ Nuke All Empty ({orphan_count})")
        self.btn_nuke_orphan_albums.setEnabled(orphan_count > 0)

    def _on_album_selected(self):
        """Handle album selection in the table."""
        rows = self.albums_table.selectedItems()
        if not rows:
            self._clear_album_inspector()
            return

        row = self.albums_table.currentRow()
        title_item = self.albums_table.item(row, 0)
        if not title_item:
            return

        album_id = title_item.data(Qt.ItemDataRole.UserRole)
        usage = int(self.albums_table.item(row, 3).text())

        self._current_album_id = album_id
        self._current_album_usage = usage

        self.album_title_input.setText(title_item.text())
        self.album_title_input.setEnabled(False)  # Read-only for now

        artist_item = self.albums_table.item(row, 1)
        self.album_artist_input.setText(artist_item.text() if artist_item else "—")
        self.album_artist_input.setEnabled(False)

        year_item = self.albums_table.item(row, 2)
        self.album_year_input.setText(year_item.text() if year_item else "—")
        self.album_year_input.setEnabled(False)

        self.album_usage_label.setText(f"Songs: {usage}")
        self.btn_album_delete.setEnabled(True)

    def _clear_album_inspector(self):
        """Clear the album inspector fields."""
        self._current_album_id = None
        self._current_album_usage = 0
        self.album_title_input.clear()
        self.album_title_input.setEnabled(False)
        self.album_artist_input.clear()
        self.album_artist_input.setEnabled(False)
        self.album_year_input.clear()
        self.album_year_input.setEnabled(False)
        self.album_usage_label.setText("Songs: —")
        self.btn_album_delete.setEnabled(False)

    def _delete_album(self):
        """Delete the selected album."""
        if not self._current_album_id or not self.album_service:
            return

        if self._current_album_usage > 0:
            result = QMessageBox.question(
                self, "Delete Album?",
                f"This album has {self._current_album_usage} song(s) linked.\\n\\n"
                f"Deleting will unlink all songs. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if result != QMessageBox.StandardButton.Yes:
                return

        if self.album_service.delete(self._current_album_id):
            self._refresh_albums_list()
            self._clear_album_inspector()
            self.data_changed.emit()
        else:
            QMessageBox.warning(self, "Delete Failed", "Could not delete the album.")

    def _nuke_orphan_albums(self):
        """Delete all empty albums (no linked songs)."""
        if not self.album_service:
            return

        count = self.album_service.get_orphan_count()
        if count == 0:
            return

        deleted = self.album_service.delete_all_orphans()
        self._refresh_albums_list()
        self.data_changed.emit()

        QMessageBox.information(
            self, "Empty Albums Deleted",
            f"Successfully deleted {deleted} empty album(s)."
        )

    # ─────────────────────────────────────────────────────────────────
    # HEALTH TAB
    # ─────────────────────────────────────────────────────────────────

    def _create_health_tab(self) -> QWidget:
        """Create the Health dashboard tab."""
        widget = QWidget()
        widget.setObjectName("HealthTab")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header = QLabel("⚠️ LIBRARY HEALTH REPORT")
        header.setObjectName("HealthHeader")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        layout.addSpacing(20)

        # Health items container
        health_frame = QFrame()
        health_frame.setObjectName("HealthFrame")
        health_layout = QVBoxLayout(health_frame)
        health_layout.setSpacing(15)

        # Initialize labels dict BEFORE creating rows
        self._health_labels = {}

        # Tags row
        self.health_tags_row = self._create_health_row(
            "🏷️ Orphan Tags",
            self._on_health_show_tags,
            self._on_health_nuke_tags
        )
        health_layout.addWidget(self.health_tags_row)

        # Artists row
        self.health_artists_row = self._create_health_row(
            "🎭 Empty Artists",
            self._on_health_show_artists,
            self._on_health_nuke_artists,
            enabled=bool(self.contributor_service)
        )
        health_layout.addWidget(self.health_artists_row)

        # Albums row (Phase 3 - now functional)
        self.health_albums_row = self._create_health_row(
            "💿 Empty Albums",
            self._on_health_show_albums,
            self._on_health_nuke_albums,
            enabled=bool(self.album_service)
        )
        health_layout.addWidget(self.health_albums_row)

        # Publishers row
        self.health_publishers_row = self._create_health_row(
            "🏢 Orphan Publishers",
            self._on_health_show_publishers,
            self._on_health_nuke_publishers,
            enabled=bool(self.publisher_service)
        )
        health_layout.addWidget(self.health_publishers_row)

        layout.addWidget(health_frame)
        layout.addStretch()

        # Refresh button
        btn_refresh = GlowButton("🔄 Refresh Health Report")
        btn_refresh.clicked.connect(self._refresh_health)
        layout.addWidget(btn_refresh, alignment=Qt.AlignmentFlag.AlignCenter)

        return widget

    def _create_health_row(
        self,
        label: str,
        show_callback,
        nuke_callback,
        enabled: bool = True
    ) -> QFrame:
        """Create a health report row."""
        frame = QFrame()
        frame.setObjectName("HealthRow")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(15)

        # Label with count placeholder
        lbl = QLabel(f"{label}: —")
        lbl.setObjectName("HealthRowLabel")
        lbl.setMinimumWidth(200)
        layout.addWidget(lbl)

        # Store label reference
        self._health_labels = getattr(self, '_health_labels', {})
        self._health_labels[label] = lbl

        layout.addStretch()

        # Show button
        btn_show = GlowButton("SHOW")
        btn_show.setFixedWidth(80)
        btn_show.setEnabled(enabled)
        btn_show.clicked.connect(show_callback)
        layout.addWidget(btn_show)

        # Nuke button
        btn_nuke = GlowButton("NUKE ALL")
        btn_nuke.setObjectName("NukeButton")
        btn_nuke.setFixedWidth(100)
        btn_nuke.setEnabled(enabled)
        btn_nuke.clicked.connect(nuke_callback)
        layout.addWidget(btn_nuke)

        # Store buttons for enabling/disabling
        frame._btn_show = btn_show
        frame._btn_nuke = btn_nuke

        return frame

    def _refresh_health(self):
        """Refresh all health statistics."""
        # Tags
        tag_orphans = self.tag_service.get_orphan_count()
        tag_label = self._health_labels.get("🏷️ Orphan Tags")
        if tag_label:
            if tag_orphans == 0:
                tag_label.setText("🏷️ Orphan Tags: ✓ Clean")
                tag_label.setProperty("status", "clean")
            else:
                tag_label.setText(f"🏷️ Orphan Tags: {tag_orphans}")
                tag_label.setProperty("status", "alert")
            tag_label.style().polish(tag_label)

            self.health_tags_row._btn_show.setEnabled(tag_orphans > 0)
            self.health_tags_row._btn_nuke.setEnabled(tag_orphans > 0)

        # Artists
        if self.contributor_service:
            artist_orphans = self.contributor_service.get_orphan_count()
            artist_label = self._health_labels.get("🎭 Empty Artists")
            if artist_label:
                if artist_orphans == 0:
                    artist_label.setText("🎭 Empty Artists: ✓ Clean")
                    artist_label.setProperty("status", "clean")
                else:
                    artist_label.setText(f"🎭 Empty Artists: {artist_orphans}")
                    artist_label.setProperty("status", "alert")
                artist_label.style().polish(artist_label)

                self.health_artists_row._btn_show.setEnabled(artist_orphans > 0)
                self.health_artists_row._btn_nuke.setEnabled(artist_orphans > 0)

        # Publishers
        if self.publisher_service:
            pub_orphans = self.publisher_service.get_orphan_count()
            pub_label = self._health_labels.get("🏢 Orphan Publishers")
            if pub_label:
                if pub_orphans == 0:
                    pub_label.setText("🏢 Orphan Publishers: ✓ Clean")
                    pub_label.setProperty("status", "clean")
                else:
                    pub_label.setText(f"🏢 Orphan Publishers: {pub_orphans}")
                    pub_label.setProperty("status", "alert")
                pub_label.style().polish(pub_label)

                self.health_publishers_row._btn_show.setEnabled(pub_orphans > 0)
                self.health_publishers_row._btn_nuke.setEnabled(pub_orphans > 0)

        # Albums (Phase 3)
        if self.album_service:
            album_orphans = self.album_service.get_orphan_count()
            album_label = self._health_labels.get("💿 Empty Albums")
            if album_label:
                if album_orphans == 0:
                    album_label.setText("💿 Empty Albums: ✓ Clean")
                    album_label.setProperty("status", "clean")
                else:
                    album_label.setText(f"💿 Empty Albums: {album_orphans}")
                    album_label.setProperty("status", "alert")
                album_label.style().polish(album_label)

                self.health_albums_row._btn_show.setEnabled(album_orphans > 0)
                self.health_albums_row._btn_nuke.setEnabled(album_orphans > 0)

    def _on_health_show_tags(self):
        """Switch to Tags tab with orphans filter."""
        self.tabs.setCurrentWidget(self.tags_tab)
        self.tags_orphans_only.setChecked(True)

    def _on_health_nuke_tags(self):
        """Nuke all orphan tags from Health tab."""
        self._nuke_orphan_tags()
        self._refresh_health()

    def _on_health_show_artists(self):
        """Switch to Artists tab with orphans filter."""
        if hasattr(self, 'artists_tab'):
            self.tabs.setCurrentWidget(self.artists_tab)
            self.artists_orphans_only.setChecked(True)

    def _on_health_nuke_artists(self):
        """Nuke all orphan artists from Health tab."""
        self._nuke_orphan_artists()
        self._refresh_health()

    def _on_health_show_albums(self):
        """Switch to Albums tab with orphans filter."""
        if hasattr(self, 'albums_tab'):
            self.tabs.setCurrentWidget(self.albums_tab)
            self.albums_orphans_only.setChecked(True)

    def _on_health_nuke_albums(self):
        """Nuke all empty albums from Health tab."""
        self._nuke_orphan_albums()
        self._refresh_health()

    def _on_health_show_publishers(self):
        """Switch to Publishers tab with orphans filter."""
        if hasattr(self, 'publishers_tab'):
            self.tabs.setCurrentWidget(self.publishers_tab)
            self.publishers_orphans_only.setChecked(True)

    def _on_health_nuke_publishers(self):
        """Nuke all orphan publishers from Health tab."""
        self._nuke_orphan_publishers()
        self._refresh_health()

    def keyPressEvent(self, event):
        """Handle key presses (Escape to close)."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    # ─────────────────────────────────────────────────────────────────

    def showEvent(self, event):
        """Called when window is shown."""
        super().showEvent(event)
        # Refresh all lists when window is shown
        self._refresh_tags_list()
        if self.contributor_service and hasattr(self, 'artists_tab'):
            self._refresh_artists_list()
        if self.album_service and hasattr(self, 'albums_tab'):
            self._refresh_albums_list()
        if self.publisher_service and hasattr(self, 'publishers_tab'):
            self._refresh_publishers_list()
        self._refresh_health()

    def closeEvent(self, event):
        """Save geometry on close."""
        self._save_geometry()
        self._save_active_tab()
        event.accept()

    def _restore_geometry(self):
        """Restore window geometry from settings."""
        geometry = self.settings_manager.get_setting(self.GEOMETRY_KEY)
        if geometry:
            self.restoreGeometry(geometry)
        else:
            # Default size
            self.resize(900, 600)

    def _save_geometry(self):
        """Save window geometry to settings."""
        self.settings_manager.set_setting(self.GEOMETRY_KEY, self.saveGeometry())

    def _restore_active_tab(self):
        """Restore the last active tab."""
        tab_index = self.settings_manager.get_setting(self.ACTIVE_TAB_KEY, 0)
        if isinstance(tab_index, int) and 0 <= tab_index < self.tabs.count():
            self.tabs.setCurrentIndex(tab_index)

    def _save_active_tab(self):
        """Save the current active tab."""
        self.settings_manager.set_setting(self.ACTIVE_TAB_KEY, self.tabs.currentIndex())
