import os
import sys
import mutagen
from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeView, QTableView, QListWidget,
    QLineEdit, QPushButton, QLabel,
    QSlider, QSizePolicy, QFileDialog,
    QMessageBox, QMenu
)
from PyQt6.QtCore import Qt, QStandardPaths, QSortFilterProxyModel
from PyQt6.QtSql import QSqlDatabase
from db_manager import DBManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gosling2 - Music Library")
        window_width = 1200
        window_height = 800
        window_top = (QApplication.primaryScreen().size().height() - window_height) // 2
        window_left = (QApplication.primaryScreen().size().width() - window_width) // 2
        self.setGeometry(window_left, window_top, window_width, window_height)

        # 1. Main Container Widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        # Main vertical layout for the whole window (Top, Middle, Bottom)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(5, 3, 5, 3)

        # --- TOP SECTION: ADD SONGS BUTTON & SEARCH BAR ---
        self._setup_top_controls(main_layout)

        # --- MIDDLE SECTION: THREE MAIN PANELS ---
        self._setup_middle_panels(main_layout)

        # --- BOTTOM SECTION: PLAYBACK BAR AND CONTROLS ---
        self._setup_bottom_bar(main_layout)

        # --- CONNECTIONS ---
        self.add_files_button.clicked.connect(self._open_file_dialog)

        # --- DATABASE ---
        self.db_manager = DBManager()
        self.library_model = QStandardItemModel()
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.library_model)
        self.table_view.setModel(self.proxy_model)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_table_context_menu)
        self._current_sort_column_index = 0
        self._current_sort_order = Qt.SortOrder.DescendingOrder
        self._setup_table_view()

        QApplication.instance().aboutToQuit.connect(self._cleanup_on_exit)

    def _cleanup_on_exit(self):
        """Cleans up resources on application exit."""
        db = QSqlDatabase.database()
        if db.isValid():
            db.close()

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
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 1. Left Panel: Filtering/Browsing (QTreeWidget - using QTreeView placeholder)
        self.tree_view = QTreeView()
        self.tree_view.setHeaderHidden(True)
        song_library_panel = QWidget()
        song_library_panel.setLayout(QVBoxLayout())
        tree_label = QLabel("LIBRARY TREE BROWSER")
        tree_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        song_library_panel.layout().addWidget(tree_label)
        song_library_panel.layout().addWidget(self.tree_view)
        splitter.addWidget(song_library_panel)

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
        splitter.addWidget(database_viewer)

        # 3. Right Panel: Real-Time Queue (QListWidget)
        self.queue_list = QListWidget()
        playlist_panel = QWidget()
        playlist_panel.setLayout(QVBoxLayout())
        playlist_label = QLabel("PLAYLIST")
        playlist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        playlist_panel.layout().addWidget(playlist_label)
        playlist_panel.layout().addWidget(self.queue_list)
        splitter.addWidget(playlist_panel)

        # Set initial sizes for better visual balance
        splitter.setSizes([200, 600, 300])

        layout.addWidget(splitter, 1)

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

    def _setup_table_view(self):
        """Sets up the QTableView and connects signals."""
        header = self.table_view.horizontalHeader()
        self.table_view.setSortingEnabled(True)
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.sectionClicked.connect(self._sort_library_view)
        self.refresh_library_view()
        self.table_view.setColumnHidden(0, True)
        self.table_view.setColumnHidden(2, True)
        self.table_view.horizontalHeader().setStretchLastSection(True)
        self.table_view.resizeColumnsToContents()

    def _show_table_context_menu(self, position):
        """Shows a context menu for the table view."""
        index = self.table_view.indexAt(position)
        if not index.isValid():
            return
        menu = QMenu()
        show_id3_action = menu.addAction("🔍 Show ID3 Data")
        show_id3_action.triggered.connect(self._show_id3_tags)
        delete_action = menu.addAction("❌ Delete Selected File(s)")
        delete_action.triggered.connect(self._delete_selected_files)
        menu.exec(self.table_view.viewport().mapToGlobal(position))

    def _show_id3_tags(self):
        """Shows the ID3 tags for the selected file."""
        selected_cells = self.table_view.selectionModel().selectedIndexes()
        if not selected_cells:
            QMessageBox.information(self, "Show ID3 Tags", "No file selected.")
            return

        selected_rows = sorted(set(index.row() for index in selected_cells))

        for row in selected_rows:
            file_id_qindex = self.library_model.index(row, 0)
            file_id = str(self.library_model.data(file_id_qindex))
            file_path_index = self.library_model.index(row, 2)
            file_path = self.library_model.data(file_path_index)
            file_name = os.path.basename(file_path)
            if not file_path:
                QMessageBox.warning(self, "Metadata Error", f"File path not found or invalid:\n{file_path}")
                return
            try:
                audio = mutagen.File(file_path)
                if not audio:
                    QMessageBox.warning(self, "Metadata Error", "Mutagen could not read audio file.")
                    return

                # --- Format Basic Info ---
                tags_to_update = audio.tags if audio.tags else {}
                title_tag = audio.get("TIT2", file_name)[0].strip()
                artist_tag = audio.get("TPE1", ["Unknown artist"])[0].strip()
                duration = audio.info.length if hasattr(audio.info, 'length') else 0
                duration = float(duration)
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                bpm = audio.get("TBPM", audio.get("bpm"))
                try:
                    bpm = int(str(bpm).strip()) if bpm else 0
                except (ValueError, TypeError, IndexError):
                    bpm = 0

                question_text = (
                    f"**File ID3:** {file_id}\n"
                    f"**File:** {file_name}\n\n"
                    f"Do you want to update the database record with the following ID3 tags?\n\n"
                    f"**Artist:** {artist_tag}\n"
                    f"**Title:** {title_tag}\n"
                    f"**Duration:** {minutes:02d}:{seconds:02d} ({duration:.2f}s)\n"
                    f"**BPM:** {bpm}"
                )

                # --- Display Result ---
                reply = QMessageBox.question(
                    self, "Update Metadata",
                    question_text,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    if self.db_manager.update_file_metadata(file_id, title_tag, duration, bpm, tags_to_update):
                        self.refresh_library_view()
                        QMessageBox.information(self, "Update Metadata", "Metadata updated successfully.")
                    else:
                        QMessageBox.warning(self, "Update Metadata", "Failed to update metadata.")
            except Exception as e:
                QMessageBox.critical(self, "Mutagen Error", f"An error occurred while reading the file metadata:\n{e}")

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
            # row is an int; build QModelIndex from row, column 0
            model_index = self.library_model.index(row, 0)
            if not model_index.isValid():
                continue

            file_id_variant = self.library_model.data(model_index)
            try:
                file_id = int(file_id_variant)
            except (TypeError, ValueError):
                # Couldn't parse file id; skip and continue
                continue

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
                    title = db_manager.insert_file_basic(path)
                    if title:
                        inserted_count += 1
                        file_summary += f"[ADDED] {title}\n"
                    else:
                        file_summary += f"[SKIPPED] {os.path.basename(path)}\n"

                if inserted_count > 0:
                    self.refresh_library_view()

                msg = QMessageBox()
                msg.setWindowTitle("File Import Summary")
                msg.setText(f"Inserted {inserted_count} new file(s) into the database.\n\n{file_summary}")
                msg.exec()


    def refresh_library_view(self):
        self.library_model.clear()
        headers, data = self.db_manager.fetch_all_library_data()
        if not headers:
            self.library_model.setHorizontalHeaderLabels(['FileID', 'Artist(s)', 'Path', 'Title', 'Duration', 'BPM'])
            return
        self.library_model.setHorizontalHeaderLabels(headers)
        for row_data in data:
            items = []
            for col_index, value in enumerate(row_data):
                item = QStandardItem(str(value) if value is not None else "")
                if col_index in [0, 4, 5]:  # FileID, Duration, TempoBPM
                    try:
                        numeric_value = float(value) if value is not None else 0.0
                    except (ValueError, TypeError):
                        numeric_value = 0.0
                    item.setData(numeric_value, 3)

                items.append(item)

            self.library_model.appendRow(items)
        self.proxy_model.sort(
            self.table_view.horizontalHeader().sortIndicatorSection(),
            self.table_view.horizontalHeader().sortIndicatorOrder()
        )

        self.table_view.resizeColumnToContents(0)


    def _sort_library_view(self, index):
        """Handles column header clicks by applying the sort to the proxy model."""



# --- Application Execution Entry Point ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())