from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QListWidget, QListWidgetItem, QStackedWidget,
    QFrame, QMessageBox, QComboBox, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction
from ..widgets.glow_factory import GlowLineEdit, GlowButton

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
        
        self.btn_mode_toggle = GlowButton("Create New (+)")
        self.btn_mode_toggle.clicked.connect(self._toggle_mode)
        header_layout.addWidget(self.btn_mode_toggle)
        
        layout.addLayout(header_layout)
        
        # 2. Stacked Content (Search vs Create)
        self.stack = QStackedWidget()
        
        # --- PAGE 1: SEARCH ---
        self.page_search = QWidget()
        search_layout = QVBoxLayout(self.page_search)
        search_layout.setContentsMargins(0,0,0,0)
        
        self.txt_search = GlowLineEdit()
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
        self.btn_cancel = GlowButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        self.btn_confirm = GlowButton("Select")
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
        inp = GlowLineEdit()
        layout.addWidget(lbl)
        layout.addWidget(inp)
        return inp

    def _toggle_mode(self, checked=False):
        if self.stack.currentIndex() == 0:
            # === SWITCH TO CREATE MODE ===
            search_text = self.txt_search.text().strip()
            
            self.stack.setCurrentIndex(1)
            self.lbl_title.setText("NEW ALBUM")
            self.btn_mode_toggle.setText("Back to Search")
            self.btn_confirm.setText("Create & Select")
            self.btn_confirm.setEnabled(True)
            
            # Smart Populate Logic:
            # Priority 1: User's typed search query (explicit intent)
            # Priority 2: Original Song Metadata (contextual intent)
            # Priority 3: Blank
            
            target_title = search_text or self.initial_data.get('title', '')
            target_artist = self.initial_data.get('artist', '')
            target_year = self.initial_data.get('year', '')
            target_publisher = self.initial_data.get('publisher', '')

            # Set fields (Force set to ensure consistent state)
            self.inp_title.setText(target_title)
            self.inp_artist.setText(target_artist)
            self.inp_year.setText(str(target_year) if target_year else "")
            self.inp_publisher.setText(target_publisher)

            # Clear search to avoid confusion upon return
            self.txt_search.clear()
            
            # Focus Logic
            if not target_title:
                self.inp_title.setFocus()
            elif not target_artist:
                self.inp_artist.setFocus()
            else:
                 self.inp_title.setFocus() # Default to title if all filled
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
        # Call Repo to Create
        try:
            if not self.album_repo:
                 raise ValueError("Album Repository connection is missing.")

            # Parse Year safely
            year_val = self.inp_year.text().strip()
            year_int = int(year_val) if year_val and year_val.isdigit() else None
            
            # Using get_or_create to prevent duplicates on name collision
            album_obj, created = self.album_repo.get_or_create(
                title=title,
                album_artist=self.inp_artist.text().strip(),
                release_year=year_int
            )
            
            if not album_obj:
                raise ValueError("Failed to retrieve or create album object.")

            # If newly created, we might need to update other fields (Publisher/Type)
            # because get_or_create might not set them if just matching basic key.
            # But here we are in "Create Mode", so we assume intention to set attributes.
            # Note: We only update if we have a valid object
            try:
                album_obj.album_type = self.cmb_type.currentText()
                # Update attributes
                self.album_repo.update(album_obj)
                
                # Link Publisher
                pub_name = self.inp_publisher.text().strip()
                if pub_name and album_obj.album_id is not None:
                    self.album_repo.set_publisher(album_obj.album_id, pub_name)
            except Exception as e:
                # Log minor update error but don't stop the selection
                print(f"Warning: Could not update album attributes: {e}")
            
            self.album_selected.emit(album_obj.album_id, album_obj.title)
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Could not create album: {e}")
