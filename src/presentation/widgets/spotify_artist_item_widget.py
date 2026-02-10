"""
SpotifyArtistItemWidget 🎵
Visual row for a single parsed artist in the Spotify import preview.
"""
from typing import List, Optional
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QMenu
from PyQt6.QtCore import Qt, pyqtSignal

from .glow_factory import GlowLineEdit, GlowButton
from .chip_tray_widget import ChipTrayWidget

class SpotifyArtistItemWidget(QWidget):
    """
    A row representing a single parsed artist.
    Horizontal layout: [Name Edit] | [Roles Tray] | [Delete Button]
    """
    
    delete_requested = pyqtSignal(object) # Emits self
    
    def __init__(self, name: str, roles: List[str], service_provider: any, parent=None):
        super().__init__(parent)
        self.service_provider = service_provider
        self.initial_roles = roles
        
        # UI Properties
        self.setObjectName("SpotifyArtistItem")
        self.setProperty("has_unknown_roles", False)
        
        self._init_ui(name, roles)
        self._connect_signals()

    def _init_ui(self, name: str, roles: List[str]):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)
        
        # 1. Name Editor
        self.name_edit = GlowLineEdit()
        self.name_edit.setText(name)
        self.name_edit.setPlaceholderText("Artist Name")
        self.name_edit.setFixedWidth(200)
        layout.addWidget(self.name_edit)
        
        # 2. Roles Tray
        self.role_tray = ChipTrayWidget(
            confirm_removal=False,
            add_tooltip="Add Role",
            parent=self
        )
        # Customizing tray for roles
        self.role_tray.setSizePolicy(self.role_tray.sizePolicy().Policy.Expanding, self.role_tray.sizePolicy().Policy.Preferred)
        
        layout.addWidget(self.role_tray, 1)
        
        # 3. Delete Button
        self.btn_delete = GlowButton("✕")
        self.btn_delete.setFixedSize(24, 24)
        self.btn_delete.setToolTip("Remove this artist")
        self.btn_delete.set_radius_style("border-radius: 12px;")
        layout.addWidget(self.btn_delete)
        
        # Set initial roles
        self.set_roles(roles)

    def _connect_signals(self):
        self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self))
        self.role_tray.chip_clicked.connect(self._on_role_clicked)
        # The add button of the tray
        self.role_tray.add_requested.connect(self._on_add_role_clicked)
        # Enable removal via Ctrl+Click on chips
        self.role_tray.chip_remove_requested.connect(lambda eid, label: self.role_tray.remove_chip(eid))

    def get_name(self) -> str:
        return self.name_edit.text().strip()

    def get_roles(self) -> List[str]:
        return self.role_tray.get_names()

    def set_roles(self, roles: List[str]):
        """Populate the tray with role chips."""
        self.role_tray.clear()
        
        # We use role name as both ID and Label for simplicity in preview
        for role in roles:
            # Check if role is unknown (heuristic for visual flagging)
            is_unknown = self._check_role_unknown(role)
            zone = "amber" if is_unknown else "default"
            
            # Add chip to tray
            # entity_id is used for identification; we use index or name hash
            self.role_tray.add_chip(
                entity_id=hash(role), 
                label=role, 
                zone=zone,
                tooltip="Unknown Role" if is_unknown else ""
            )
            
        self._refresh_unknown_status()

    def _check_role_unknown(self, role_name: str) -> bool:
        """
        Check if a role exists in the DB.
        This is a soft check for visual flagging in the preview.
        """
        if not self.service_provider or not hasattr(self.service_provider, 'library_service'):
            return False
            
        # Optimization: In a real app, we'd cache the roles list.
        # For the preview, we can just check against a common list or query service.
        # For now, let's assume unknown if not in our hardcoded synoynms list + common extras.
        from src.utils.spotify_credits_parser import ROLE_SYNONYMS
        canonical_roles = [r.lower() for r in ROLE_SYNONYMS.values()]
        
        # Add some standard ones
        canonical_roles.extend(['performer', 'artist', 'remixer', 'publisher', 'distributor'])
        
        return role_name.lower() not in canonical_roles

    def _refresh_unknown_status(self):
        """Update background glow if unknown roles exist."""
        has_unknown = any(self._check_role_unknown(r) for r in self.get_roles())
        self.setProperty("has_unknown_roles", has_unknown)
        
        # Re-apply styling
        self.style().unpolish(self)
        self.style().polish(self)

    def _on_role_clicked(self, role_id, role_name):
        """Open a menu to quickly swap the role to a canonical one."""
        menu = QMenu(self)
        
        from src.utils.spotify_credits_parser import ROLE_SYNONYMS
        canonical_list = sorted(list(set(ROLE_SYNONYMS.values())))
        
        for r in canonical_list:
            action = menu.addAction(r)
            action.triggered.connect(lambda checked, new_role=r: self._swap_role(role_name, new_role))
            
        menu.addSeparator()
        remove_action = menu.addAction("Remove Role")
        remove_action.triggered.connect(lambda: self.role_tray.remove_chip(role_id))
        
        menu.exec(self.cursor().pos())

    def _swap_role(self, old_role_name, new_role_name):
        """Replace a role in the tray."""
        current_roles = self.get_roles()
        new_roles = [new_role_name if r == old_role_name else r for r in current_roles]
        self.set_roles(new_roles)

    def _on_add_role_clicked(self):
        """Allow manual role entry if needed."""
        # This would typically open a small input or a specialized picker.
        # For MVP, we can just allow the user to type in the tray if supported, 
        # or just leave it for re-pasting.
        pass
