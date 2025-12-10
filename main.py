import os
import sys
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QAction, QCloseEvent, QDrag, QFont, QPen, QColor, QPainter
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeView, QTableView, QListWidget,
    QLineEdit, QPushButton, QLabel,
    QSlider, QSizePolicy, QFileDialog,
    QMessageBox, QMenu, QListWidgetItem,
    QStyledItemDelegate, QStyle
)
from PyQt6.QtCore import QStandardPaths, QSortFilterProxyModel, QSettings, QMimeData, Qt, QRect, QSize, QUrl
from PyQt6.QtSql import QSqlDatabase
from db_manager import DBManager
from Song import Song


class PlaylistItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.artist_font = QFont("Arial", 12, QFont.Weight.Bold)
        self.title_font = QFont("Arial", 10)

    def paint(self, painter, option, index):
        painter.save()

        # Draw background if selected
        if option.state & QStyle.StateFlag.State_Selected:
            custom_color = QColor("#1E5096")
            painter.fillRect(option.rect, custom_color)

        # Retrieve data
        display_text = index.data(Qt.ItemDataRole.DisplayRole)
        if not display_text or not isinstance(display_text, str):
            display_text = ""
        if "|" in display_text:
            artist, title = display_text.split("|", 1)
        else:
            artist, title = display_text, ""

        # Set left alignment with padding
        padding = 5
        artist_rect = QRect(option.rect.left() + padding,
                            option.rect.top() + padding,
                            option.rect.width() - 2 * padding,
                            option.rect.height() // 2)
        title_rect = QRect(option.rect.left() + padding,
                           option.rect.top() + option.rect.height() // 2,
                           option.rect.width() - 2 * padding,
                           option.rect.height() // 2 - padding)

        # Draw artist (top line)
        painter.setFont(self.artist_font)
        painter.setPen(QPen(option.palette.text(), 1))
        painter.drawText(artist_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, artist)

        # Draw title (bottom line)
        painter.setFont(self.title_font)
        painter.setPen(QPen(option.palette.text(), 1))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)

        painter.restore()

    def sizeHint(self, option, index):
        width = option.rect.width() if option.rect.width() > 0 else 200
        return QSize(width, 54)  # e.g. 54 px for two rows


class PlaylistWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDropMode.DropOnly)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

        self._preview_row = None      # row where preview line will display
        self._preview_after = False   # before or after row

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if not event.mimeData().hasUrls():
            event.ignore()
            return

        pos = event.position().toPoint()
        index = self.indexAt(pos)

        if index.isValid():
            rect = self.visualItemRect(self.item(index.row()))
            midpoint = rect.top() + rect.height() / 2

            self._preview_row = index.row()
            self._preview_after = pos.y() >= midpoint
        else:
            # dropped below all items
            self._preview_row = self.count() - 1
            self._preview_after = True

        self.viewport().update()
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._preview_row = None
        self.viewport().update()

    def dropEvent(self, event):
        mime_data = event.mimeData()
        if not mime_data.hasUrls():
            event.ignore()
            return

        urls = mime_data.urls()
        file_paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if not file_paths:
            event.ignore()
            return

        # Compute final position
        if self._preview_row is not None:
            insert_row = self._preview_row + (1 if self._preview_after else 0)
        else:
            insert_row = self.count()

        for path in file_paths:
            display_text = os.path.basename(path)

            try:
                song = Song.from_mp3(path, None)
                if song:
                    artist = song.performers or "Unknown Artist"
                    title  = song.title or os.path.basename(path)
                    display_text = f"{artist} | {title}"
            except Exception:
                pass

            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, {"path": path})
            self.insertItem(insert_row, item)
            insert_row += 1

        # Reset preview state
        self._preview_row = None
        self.viewport().update()

        event.acceptProposedAction()

    def paintEvent(self, event):
        super().paintEvent(event)

        if self._preview_row is None:
            return

        painter = QPainter(self.viewport())
        pen = QPen(Qt.GlobalColor.red, 2)
        painter.setPen(pen)

        # Determine line position
        if self._preview_row < self.count():
            item = self.item(self._preview_row)
            rect = self.visualItemRect(item)
            y = rect.bottom() if self._preview_after else rect.top()
        else:
            # dropping at end
            last_rect = self.visualItemRect(self.item(self.count() - 1))
            y = last_rect.bottom()

        painter.drawLine(0, y, self.viewport().width(), y)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Settings
        QApplication.setOrganizationName("Prodo")
        QApplication.setApplicationName("Gosling2")
        self.settings = QSettings()

        # Main Window Setup
        self._load_window_geometry()
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # Main vertical layout for the whole window (Top, Middle, Bottom)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(5, 3, 5, 3)

        # --- DATABASE & MODELS (MUST BE INITIALIZED FIRST) ---
        self.db_manager = DBManager()
        self.library_model = QStandardItemModel()
        self.filter_tree_model = QStandardItemModel()  # <-- FIXED: Initialized early
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.library_model)

        # --- SETUP SECTIONS (Now models are ready) ---
        self._setup_top_controls(main_layout)
        self._setup_middle_panels(main_layout)  # <-- This call will now succeed
        self._setup_bottom_bar(main_layout)

        # --- TABLE & SORT SETUP (Must run AFTER self.table_view is created in _setup_middle_panels) ---
        self.table_view.setModel(self.proxy_model)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_table_context_menu)
        self.table_view.setDragEnabled(True)
        self.table_view.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.table_view.setDragDropMode(QTableView.DragDropMode.DragOnly)
        self._set_up_drag_and_drop_on_table_view()

        # Initial sort state setup
        self._current_sort_column_index = 0
        self._current_sort_order = Qt.SortOrder.DescendingOrder

        self._setup_table_view()  # This method should handle header connections and refresh the data.

        # --- CONNECTIONS ---
        self.add_files_button.clicked.connect(self._open_file_dialog)
        self.tree_view.clicked.connect(self._filter_library_by_tree_selection)
        QApplication.instance().aboutToQuit.connect(self._cleanup_on_exit)
        header = self.table_view.horizontalHeader()
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self._show_column_context_menu)

    def _load_window_geometry(self):
        if self.settings.contains("geometry"):
            self.restoreGeometry(self.settings.value("geometry"))
        else:
            window_width = 1200
            window_height = 800
            window_top = (QApplication.primaryScreen().size().height() - window_height) // 2
            window_left = (QApplication.primaryScreen().size().width() - window_width) // 2
            self.setGeometry(window_left, window_top, window_width, window_height)

    def _save_settings(self):
        """Saves window geometry and other settings."""
        self.settings.setValue("geometry", self.saveGeometry())
        if hasattr(self, "splitter"):
            self.settings.setValue("splitter_state", self.splitter.saveState())
        self._save_column_visibility()

    def _save_column_visibility(self):
        """Saves the visibility state of each column in the table view."""
        header_model = self.library_model
        table_view = self.table_view
        for i in range(header_model.columnCount()):
            header_name = header_model.headerData(i, Qt.Orientation.Horizontal)
            is_hidden = table_view.isColumnHidden(i)
            key = f"column_hidden/{header_name}"
            self.settings.setValue(key, is_hidden)

    def _load_column_visibility(self):
        """Loads the visibility state for all columns."""
        headers = [self.library_model.headerData(i, Qt.Orientation.Horizontal)
                   for i in range(self.library_model.columnCount())]
        for i, header_name in enumerate(headers):
            # QSettings key for column visibility: "column_hidden/<Column Header Name>"
            key = f"column_hidden/{header_name}"
            # Default is False (not hidden).
            is_hidden = self.settings.value(key, False, type=bool)
            self.table_view.setColumnHidden(i, is_hidden)

    @staticmethod
    def _cleanup_on_exit():
        """Cleans up resources on application exit."""
        db = QSqlDatabase.database()
        if db.isValid():
            db.close()

    def closeEvent(self, event: QCloseEvent):
        """Saves window state before closing."""
        self._save_settings()
        super().closeEvent(event)

    def _show_column_context_menu(self, position):
        """Shows a context menu for the table header to toggle column visibility."""
        menu = QMenu(self)
        source_model = self.library_model
        table_view = self.table_view

        for col in range(source_model.columnCount()):
            header_text = source_model.headerData(col, Qt.Orientation.Horizontal)
            action = QAction(str(header_text), self)
            action.setCheckable(True)
            # Table view columns are shown/hidden per *view* index (source == proxy in your set-up),
            # but we assume 1:1 mapping. If you're reordering columns or using a proxy that changes columns,
            # use proxy_model.mapFromSource/mapToSource as needed.
            action.setChecked(not table_view.isColumnHidden(col))
            action.setData(col)
            action.toggled.connect(self.toggle_column_visibility)
            menu.addAction(action)

        global_pos = table_view.horizontalHeader().mapToGlobal(position)
        menu.exec(global_pos)

    def toggle_column_visibility(self, checked):
        """Toggles the visibility of a column in the table view."""
        action = self.sender()
        if action:
            column = action.data()
            self.table_view.setColumnHidden(column, not checked)

    def _setup_top_controls(self, layout: QVBoxLayout):
        """Sets up the Add button and Search bar at the top."""
        top_hbox = QHBoxLayout()
        top_hbox.setContentsMargins(5, 0, 5, 10)

        # Add Files/Directory Button (Top Left)
        self.add_files_button = QPushButton("➕ Add Files/Dir")
        self.add_files_button.setFixedWidth(150)
        self.add_files_button.setFixedHeight(35)
        top_hbox.addWidget(self.add_files_button)

        # Search Bar (Top Middle/Right)
        self.search_bar = QLineEdit()
        self.search_bar.setFixedHeight(34)
        self.search_bar.setPlaceholderText("🔎 Search Library (FTS: Artist, Title, Album, Tags...)")
        self.search_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top_hbox.addWidget(self.search_bar)

        layout.addLayout(top_hbox)

    def _setup_middle_panels(self, layout: QVBoxLayout):
        """Sets up the three main content panels (Filter, List, Queue)."""

        # Use QSplitter to allow panels to be resized by the user
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # 1. Left Panel: Filtering/Browsing (QTreeWidget - using QTreeView placeholder)
        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setModel(self.filter_tree_model)
        song_library_panel = QWidget()
        song_library_panel.setLayout(QVBoxLayout())
        tree_label = QLabel("LIBRARY TREE BROWSER")
        tree_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        song_library_panel.layout().addWidget(tree_label)
        song_library_panel.layout().addWidget(self.tree_view)
        self.splitter.addWidget(song_library_panel)

        # 2. Middle Panel: Main Song Library (QTableView)
        self.table_view = QTableView()
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_table_context_menu)
        database_viewer = QWidget()
        database_viewer.setLayout(QVBoxLayout())
        library_label = QLabel("SONG LIBRARY")
        library_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        database_viewer.layout().addWidget(library_label)
        database_viewer.layout().addWidget(self.table_view)
        self.splitter.addWidget(database_viewer)

        # 3. Right Panel: Real-Time Queue (PlaylistWidget)
        self.queue_list = PlaylistWidget()
        self.queue_list.setItemDelegate(PlaylistItemDelegate(self.queue_list))
        self.queue_list.setSpacing(2)  # Optional spacing between items
        playlist_panel = QWidget()
        playlist_panel.setLayout(QVBoxLayout())
        playlist_label = QLabel("PLAYLIST")
        playlist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        playlist_panel.layout().addWidget(playlist_label)
        playlist_panel.layout().addWidget(self.queue_list)
        self.splitter.addWidget(playlist_panel)

        # Set initial sizes for better visual balance
        splitter_state = self.settings.value("splitter_state")
        print(splitter_state)
        if splitter_state:
            self.splitter.restoreState(splitter_state)
        else:
            self.splitter.setSizes([200, 600, 300])

        layout.addWidget(self.splitter, 1)

    def _setup_bottom_bar(self, layout: QVBoxLayout):
        """Sets up the persistent bottom playback bar."""

        bottom_bar_hbox = QHBoxLayout()
        bottom_bar_hbox.setContentsMargins(10, 10, 0, 0)

        # 1. Current Song Info (Left Side)
        self.current_song_label = QLabel("Artist Name - Song Title")
        bottom_bar_hbox.addWidget(self.current_song_label)

        # 2. Playback Scroll Bar (Center)
        self.playback_slider = QSlider(Qt.Orientation.Horizontal)
        self.playback_slider.setRange(0, 1000)
        bottom_bar_hbox.addWidget(self.playback_slider)

        # 3. Time Labels (Flanking the slider)
        self.time_played_label = QLabel("00:00")
        self.time_separator_label = QLabel("/")
        self.total_time_label = QLabel("04:30")
        bottom_bar_hbox.addWidget(self.time_played_label)
        bottom_bar_hbox.addWidget(self.time_separator_label)
        bottom_bar_hbox.addWidget(self.total_time_label)

        # 4. Playback Controls Box (Right Side)
        controls_widget = QWidget()
        controls_layout = QHBoxLayout(controls_widget)
        controls_layout.setContentsMargins(5, 5, 5, 5)

        self.play_pause_button = QPushButton("⏯️ Play/Pause")
        self.play_pause_button.setFixedWidth(150)
        self.play_pause_button.setFixedHeight(70)
        self.skip_button = QPushButton("⏭️ Skip/Fade")
        self.skip_button.setFixedWidth(150)
        self.skip_button.setFixedHeight(70)

        controls_layout.addWidget(self.play_pause_button)
        controls_layout.addWidget(self.skip_button)
        bottom_bar_hbox.addWidget(controls_widget)

        layout.addLayout(bottom_bar_hbox)

    def _populate_filter_tree(self):
        """Clears and repopulates the filter tree view with data from the database."""
        self.filter_tree_model.clear()
        root_item = self.filter_tree_model.invisibleRootItem()

        artists_root = QStandardItem("Performers")
        artists_root.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        artists_data = self.db_manager.fetch_data_for_tree("Performer")
        for contributor_id, name in artists_data:
            artist_item = QStandardItem(name)
            # Store the contributor ID for later use (e.g., filtering the table)
            artist_item.setData(contributor_id, Qt.ItemDataRole.UserRole)
            artists_root.appendRow(artist_item)
        root_item.appendRow(artists_root)

        composers_root = QStandardItem("Composers")
        composers_root.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        composers_data = self.db_manager.fetch_data_for_tree("Composer")
        for contributor_id, name in composers_data:
            composer_item = QStandardItem(name)
            composer_item.setData(contributor_id, Qt.ItemDataRole.UserRole)
            composers_root.appendRow(composer_item)
        root_item.appendRow(composers_root)
        self.tree_view.expandAll()

    def _setup_table_view(self):
        """Sets up the QTableView and connects signals."""
        header = self.table_view.horizontalHeader()
        self.table_view.setSortingEnabled(True)
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        self.refresh_library_view()
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.resizeColumnsToContents()

    def _filter_library_by_tree_selection(self, index):
        """
        Filters the library table (proxy model) based on the selected item
        in the artist tree view.
        """
        role_to_column = {
            "Performers": self._get_column_index('Performers'),
            "Composers": self._get_column_index('Composers'),
        }
        item = self.filter_tree_model.itemFromIndex(index)
        if item.parent():
            role_name = item.parent().text()
            if role_name in role_to_column:
                self.proxy_model.setFilterKeyColumn(role_to_column[role_name])
                contributor_name = item.text()
                import re
                escaped_name = re.escape(contributor_name)
                filter_text = r"(^|,\s)" + escaped_name + r"($|,\s)"
                self.proxy_model.setFilterRegularExpression(filter_text)
            else:
                # top-level node like "Performers" or "Composers" shows all
                self.proxy_model.setFilterRegularExpression("")
        else:
            self.proxy_model.setFilterRegularExpression("")

        self.table_view.scrollToTop()

    def _show_table_context_menu(self, position):
        """Shows a context menu for the table view (using non-blocking popup)."""
        index = self.table_view.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu(self)
        show_id3_action = menu.addAction("🔍 Show ID3 Data")
        delete_action = menu.addAction("❌ Delete Selected File(s)")

        show_id3_action.triggered.connect(self._show_id3_tags)
        delete_action.triggered.connect(self._delete_selected_files)

        # Keep reference so it doesn't get garbage collected
        self._current_context_menu = menu
        menu.popup(self.table_view.viewport().mapToGlobal(position))

    def _show_id3_tags(self):
        """Shows the ID3 tags for the selected file(s)."""
        selected_cells = self.table_view.selectionModel().selectedIndexes()
        if not selected_cells:
            QMessageBox.information(self, "Show ID3 Tags", "No file selected.")
            return

        selected_rows = sorted(set(index.row() for index in selected_cells))
        path_col_index = self._get_column_index('Path')

        for row in selected_rows:
            file_path_index = self.proxy_model.index(row, path_col_index)
            file_path = self.proxy_model.data(file_path_index)
            file_name = os.path.basename(file_path)
            if not file_path:
                QMessageBox.warning(self, "Metadata Error", f"File path not found or invalid:\n{file_path}")
                continue

            try:
                # Load the song metadata from the MP3 file
                song = Song.from_mp3(file_path, file_path_index)
                if song is None:
                    QMessageBox.warning(self, "Metadata Error", f"Mutagen could not read audio file:\n{file_name}")
                    continue

                # Format basic info
                minutes = int(song.duration // 60)
                seconds = int(song.duration % 60)

                info_text = (
                    f"File: {file_name}\n"
                    f"Title: {song.title}\n"
                    f"Performers: {song.performers}\n"
                    f"Duration: {minutes:02d}:{seconds:02d} ({song.duration:.2f} s)\n"
                    f"BPM: {song.bpm}"
                )
                QMessageBox.information(self, "ID3 Tags", info_text)

            except Exception as e:
                QMessageBox.critical(self, "Mutagen Error",
                                     f"An error occurred while reading the file metadata for {file_name}:\n{e}")

    def _delete_selected_files(self):
        """Deletes the selected files from the database."""
        selected_indexes = self.table_view.selectionModel().selectedIndexes()
        if not selected_indexes:
            QMessageBox.information(self, "Delete Files", "No files selected for deletion.")
            return

        unique_selected_rows = sorted(set(index.row() for index in selected_indexes))

        reply = QMessageBox.question(
            self, "Delete Files",
            f"Are you sure you want to delete the selected {len(unique_selected_rows)} file(s) from the database?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        db_manager = self.db_manager
        deleted_count = 0

        for row in unique_selected_rows:
            file_id_index = self.proxy_model.index(row, 0)
            file_id = str(self.proxy_model.data(file_id_index))

            if db_manager.delete_file_by_id(file_id):
                deleted_count += 1

        if deleted_count > 0:
            self.refresh_library_view()

        msg = QMessageBox()
        msg.setWindowTitle("Delete Files")
        msg.setText(f"Deleted {deleted_count} file(s) from the database.")
        msg.exec()

    def _open_file_dialog(self):
        """
        Opens a file dialog to select one or more MP3 files,
        or a directory, and shows a message box with the selected path(s).
        """
        download_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        if download_path:
            start_path = download_path
        else:
            start_path = os.getcwd()
        dialog = QFileDialog(self, directory=start_path)
        dialog.setWindowTitle("Select MP3 Files or a Directory")
        dialog.setNameFilter("MP3 Files (*.mp3 *.m4a)")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setOptions(QFileDialog.Option.DontResolveSymlinks)

        if dialog.exec():
            selected_paths = dialog.selectedFiles()

            if selected_paths:
                db_manager = self.db_manager

                inserted_count = 0
                file_summary = "--- Selected Files ---\n"

                for path in selected_paths:
                    file_id = db_manager.insert_file_basic(path)
                    if file_id:
                        inserted_count += 1
                        song = Song.from_mp3(path, file_id)
                        db_manager.update_file_data(song)
                        file_summary += f"[ADDED] {song.title}\n"
                    else:
                        file_summary += f"[SKIPPED] {os.path.basename(path)}\n"

                if inserted_count > 0:
                    self.refresh_library_view()

                msg = QMessageBox()
                msg.setWindowTitle("File Import Summary")
                msg.setText(f"Inserted {inserted_count} new file(s) into the database.\n\n{file_summary}")
                msg.exec()

    def refresh_library_view(self):
        """
        Clears the model, fetches all library data, populates the model,
        and performs post-refresh setup (sorting, tree, column visibility).
        """
        self.library_model.clear()

        # 1. Fetch data from the database
        headers, data = self.db_manager.fetch_all_library_data()

        if not headers:
            self.library_model.setHorizontalHeaderLabels(['FileID', 'Artists', 'Path', 'Title', 'Duration', 'BPM'])
            return

        self.library_model.setHorizontalHeaderLabels(headers)

        # Identify columns that need numeric sorting (used by the ProxyModel)
        COL_ID = self._get_column_index('FileID')
        COL_DURATION = self._get_column_index('Duration')
        COL_BPM = self._get_column_index('BPM')

        NUMERIC_SORT_ROLE = Qt.ItemDataRole.UserRole  # Role 32 for numeric comparison

        # 2. Populate model rows
        for row_data in data:
            items = []
            for col_index, value in enumerate(row_data):
                item = QStandardItem(str(value) if value is not None else "")

                # Check if the column requires special numeric data for sorting
                if col_index in (COL_ID, COL_DURATION, COL_BPM):
                    try:
                        numeric_value = float(value) if value is not None else 0.0
                    except (ValueError, TypeError):
                        numeric_value = 0.0

                    # Set the numeric value using the designated UserRole
                    item.setData(numeric_value, NUMERIC_SORT_ROLE)

                items.append(item)

            self.library_model.appendRow(items)

        # 3. Post-refresh view setup

        # Re-apply the current sort order
        self.proxy_model.sort(
            self.table_view.horizontalHeader().sortIndicatorSection(),
            self.table_view.horizontalHeader().sortIndicatorOrder()
        )

        self.table_view.resizeColumnToContents(0)
        self._populate_filter_tree()
        self._load_column_visibility()

    def _get_column_index(self, header_name: str) -> int:
        """Returns the column index for a given header name."""
        for col in range(self.library_model.columnCount()):
            if self.library_model.headerData(col, Qt.Orientation.Horizontal) == header_name:
                return col
        return -1

    def _set_up_drag_and_drop_on_table_view(self):
        self.table_view.mouseMoveEvent = self._table_view_mouse_move_event_factory(self.table_view.mouseMoveEvent)

    def _table_view_mouse_move_event_factory(self, original_event):
        def custom_mouseMoveEvent(event):
            if event.buttons() == Qt.MouseButton.LeftButton:
                self._start_drag(event)
            original_event(event)

        return custom_mouseMoveEvent

    def _start_drag(self, event):
        selected_indexes = self.table_view.selectionModel().selectedIndexes()
        if not selected_indexes:
            return

        # Only unique rows
        unique_rows = sorted(set(index.row() for index in selected_indexes))
        path_col_index = self._get_column_index('Path')
        if path_col_index == -1:
            return

        # Collect valid file paths
        drag_paths = []
        for row in unique_rows:
            index = self.proxy_model.index(row, path_col_index)
            path = self.proxy_model.data(index, Qt.ItemDataRole.DisplayRole)
            if path and os.path.isfile(path):
                drag_paths.append(path)

        if not drag_paths:
            return

        # Keep the drag object alive until exec() finishes
        drag = QDrag(self.table_view)
        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(p) for p in drag_paths])
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)


# --- Application Execution Entry Point ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())