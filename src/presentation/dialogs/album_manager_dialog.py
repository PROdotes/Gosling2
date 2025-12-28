from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QListWidget, QListWidgetItem, QPushButton, QStackedWidget,
    QFrame, QMessageBox, QComboBox, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction

class AlbumManagerDialog(QDialog):
    """
    T-46: Proper Album Editor (The Inspector)
    Allows searching existing albums or creating new ones with proper hierarchy.
    """
    
    # Returns the selected/created Album ID and Name
    album_selected = pyqtSignal(int, str) 

    def __init__(self, album_repository, initial_data=None, parent=None):
        super().__init__(parent)
        self.album_repo = album_repository
        self.initial_data = initial_data or {}
        self.selected_album = None
        
        self.setWindowTitle("Album Manager")
        self.setFixedSize(600, 500)
        self.setModal(True)
        
        # Styling moved to theme.qss
        self.setObjectName("AlbumManagerDialog")
        
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # 1. Header (Mode Switcher)
        header_layout = QHBoxLayout()
        self.lbl_title = QLabel("SELECT ALBUM")
        self.lbl_title.setObjectName("DialogHeaderTitle")
        
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        
        self.btn_mode_toggle = QPushButton("Create New (+)")
        self.btn_mode_toggle.clicked.connect(self._toggle_mode)
        header_layout.addWidget(self.btn_mode_toggle)
        
        layout.addLayout(header_layout)
        
        # 2. Stacked Content (Search vs Create)
        self.stack = QStackedWidget()
        
        # --- PAGE 1: SEARCH ---
        self.page_search = QWidget()
        search_layout = QVBoxLayout(self.page_search)
        search_layout.setContentsMargins(0,0,0,0)
        
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search Albums...")
        self.txt_search.textChanged.connect(self._on_search_text_changed)
        search_layout.addWidget(self.txt_search)
        
        self.list_albums = QListWidget()
        self.list_albums.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_albums.itemSelectionChanged.connect(self._on_selection_changed)
        search_layout.addWidget(self.list_albums)
        
        self.stack.addWidget(self.page_search)
        
        # --- PAGE 2: CREATE ---
        self.page_create = QWidget()
        create_layout = QVBoxLayout(self.page_create)
        create_layout.setContentsMargins(0,0,0,0)
        create_layout.setSpacing(15)
        
        # Form
        form_frame = QFrame()
        form_frame.setObjectName("DialogFormContainer")
        form_layout = QVBoxLayout(form_frame)
        
        self.inp_title = self._add_field(form_layout, "Album Title *")
        self.inp_artist = self._add_field(form_layout, "Album Artist")
        self.inp_year = self._add_field(form_layout, "Release Year")
        self.inp_publisher = self._add_field(form_layout, "Publisher")
        
        # Type Dropdown
        lbl_type = QLabel("Release Type")
        lbl_type.setObjectName("DialogFieldLabel")
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Album", "EP", "Single", "Compilation", "Anthology"])
        
        form_layout.addWidget(lbl_type)
        form_layout.addWidget(self.cmb_type)
        
        create_layout.addWidget(form_frame)
        create_layout.addStretch()
        
        self.stack.addWidget(self.page_create)
        
        layout.addWidget(self.stack)
        
        # 3. Footer actions
        footer = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_confirm = QPushButton("Select")
        self.btn_confirm.setObjectName("Primary")
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.clicked.connect(self._on_confirm_clicked)
        
        footer.addWidget(self.btn_cancel)
        footer.addStretch()
        footer.addWidget(self.btn_confirm)
        
        layout.addLayout(footer)
        
        # Initial Population & Autoselect
        title_to_find = self.initial_data.get('title', '')
        if title_to_find:
             self.txt_search.setText(title_to_find)
        else:
             self._refresh_list()

    def _add_field(self, layout, label_text):
        lbl = QLabel(label_text.upper())
        lbl.setObjectName("DialogFieldLabel")
        inp = QLineEdit()
        layout.addWidget(lbl)
        layout.addWidget(inp)
        return inp

    def _toggle_mode(self, checked=False):
        if self.stack.currentIndex() == 0:
            # Switch to Create
            search_text = self.txt_search.text().strip()
            
            self.stack.setCurrentIndex(1)
            self.lbl_title.setText("NEW ALBUM")
            self.btn_mode_toggle.setText("Back to Search")
            self.btn_confirm.setText("Create & Select")
            self.btn_confirm.setEnabled(True)
            
            # Auto-Populate Logic
            # 1. Title: Use search text if present, else fallback to song's album tag
            if search_text:
                self.inp_title.setText(search_text)
            elif not self.inp_title.text():
                self.inp_title.setText(self.initial_data.get('title', ''))
            
            # 2. Other fields: Fill if empty
            if not self.inp_artist.text():
                self.inp_artist.setText(self.initial_data.get('artist', ''))
            if not self.inp_year.text():
                year_val = self.initial_data.get('year', '')
                self.inp_year.setText(str(year_val) if year_val else "")
            if not self.inp_publisher.text():
                self.inp_publisher.setText(self.initial_data.get('publisher', ''))

            self.txt_search.clear()
            # Auto-focus the next likely empty field
            if not self.inp_title.text():
                self.inp_title.setFocus()
            else:
                self.inp_artist.setFocus()
        else:
             # Switch back to Search
            self.stack.setCurrentIndex(0)
            self.lbl_title.setText("SELECT ALBUM")
            self.btn_mode_toggle.setText("Create New (+)")
            self.btn_confirm.setText("Select")
            self._on_selection_changed() # Re-validate button

    def _refresh_list(self, query=""):
        self.list_albums.clear()
        # TODO: Hook up to AlbumRepository
        # Assuming repo.search(query) -> list of album objects or tuples
        # For now, mock it
        
        if self.album_repo:
             results = self.album_repo.search(query)
        else:
             results = [] 
        
        if not results and not query:
             # Show 'recent' or 'all'?
             pass
             
        target_title = self.initial_data.get('title', '').strip().lower()

        for alb in results:
            # Replaced alb.id with alb.album_id, alb.year with alb.release_year, alb.artist with alb.album_artist
            year_str = f" ({alb.release_year})" if alb.release_year else ""
            artist_str = f" - {alb.album_artist}" if alb.album_artist else ""
            
            item = QListWidgetItem(f"{alb.title}{year_str}{artist_str}")
            item.setData(Qt.ItemDataRole.UserRole, alb.album_id)
            # Store raw title to avoid parsing the formatted string later
            item.setData(Qt.ItemDataRole.UserRole + 1, alb.title) 
            self.list_albums.addItem(item)
            
            # Autoselect if exact title match
            if target_title and alb.title.strip().lower() == target_title:
                item.setSelected(True)
                self.list_albums.setCurrentItem(item)
                self.list_albums.scrollToItem(item)
            
    def _on_search_text_changed(self, text):
        self._refresh_list(text)
        
    def _on_selection_changed(self):
        has_sel = len(self.list_albums.selectedItems()) > 0
        self.btn_confirm.setEnabled(has_sel)
        
    def _on_item_double_clicked(self, item):
        self._confirm_selection()
        
    def _on_confirm_clicked(self, checked=False):
        if self.stack.currentIndex() == 0:
            self._confirm_selection()
        else:
            self._create_and_select()
            
    def _confirm_selection(self):
        items = self.list_albums.selectedItems()
        if not items: return
        
        alb_id = items[0].data(Qt.ItemDataRole.UserRole)
        alb_name = items[0].data(Qt.ItemDataRole.UserRole + 1)
        
        self.album_selected.emit(alb_id, alb_name)
        self.accept()
        
    def _create_and_select(self):
        # Validate
        title = self.inp_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Validation", "Album Title is required.")
            return
            
        # Call Repo to Create
        try:
            # Parse Year safely
            year_val = self.inp_year.text().strip()
            year_int = int(year_val) if year_val.isdigit() else None
            
            # Using get_or_create to prevent duplicates on name collision
            album_obj, created = self.album_repo.get_or_create(
                title=title,
                album_artist=self.inp_artist.text().strip(),
                release_year=year_int
            )
            
            # If newly created, we might need to update other fields (Publisher/Type)
            # because get_or_create might not set them if just matching basic key.
            # But here we are in "Create Mode", so we assume intention to set attributes.
            if created or album_obj:
                album_obj.album_type = self.cmb_type.currentText()
                # Update attributes
                self.album_repo.update(album_obj)
                # Link Publisher
                if self.inp_publisher.text().strip():
                    self.album_repo.set_publisher(album_obj.album_id, self.inp_publisher.text().strip())
            
            self.album_selected.emit(album_obj.album_id, album_obj.title)
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not create album: {e}")
