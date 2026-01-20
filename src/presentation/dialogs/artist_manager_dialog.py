from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QFrame, QMessageBox, QWidget, QMenu, 
    QComboBox, QRadioButton, QButtonGroup, QSizePolicy, QCompleter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from ..widgets.glow_factory import GlowLineEdit, GlowButton, GlowComboBox
from ..widgets.entity_list_widget import EntityListWidget, LayoutMode
from src.core.entity_registry import EntityType
from src.core.context_adapters import ArtistMemberAdapter, ArtistAliasAdapter

class IdentityCollisionDialog(QDialog):
    """
    Human-friendly resolver for name conflicts. 
    No technical jargon, no scary boxes.
    """
    def __init__(
        self, target_name, song_count=0, has_context_song=False,
        title="Check Name", header="ALREADY EXISTS", 
        primary_label="Combine", secondary_label=None, description=None,
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setObjectName("CollisionDialog")
        
        layout = QVBoxLayout(self)
        layout.setObjectName("CollisionLayout")
        
        layout.addStretch(1)
        
        self.lbl_header = QLabel(header)
        self.lbl_header.setObjectName("CollisionHeader")
        self.lbl_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_header)

        self.lbl_msg = QLabel(f"'{target_name}' already exists.")
        self.lbl_msg.setObjectName("CollisionMessage")
        self.lbl_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_msg)
        
        if description:
            desc = description
        elif has_context_song:
            desc = f"Combine all {song_count} songs or link this one only?" if song_count > 1 else "Combine them?"
        else:
            desc = f"Combine all {song_count} songs?" if song_count > 1 else "Combine them?"

        self.lbl_desc = QLabel(desc)
        self.lbl_desc.setObjectName("CollisionDescription")
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_desc)

        layout.addStretch(1)
        
        btns = QVBoxLayout()
        btns.setObjectName("CollisionButtonLayout")
        
        # Primary Action
        self.btn_primary = GlowButton(primary_label)
        self.btn_primary.setObjectName("ActionPill")
        self.btn_primary.setProperty("action_role", "primary")
        self.btn_primary.clicked.connect(lambda: self.done(3))
        self.btn_primary.setDefault(True) 
        btns.addWidget(self.btn_primary)
            
        # Secondary Action (Optional)
        if secondary_label:
            self.btn_secondary = GlowButton(secondary_label)
            self.btn_secondary.setObjectName("ActionPill")
            self.btn_secondary.setProperty("action_role", "secondary")
            self.btn_secondary.clicked.connect(lambda: self.done(1))
            btns.addWidget(self.btn_secondary)

        # Cancel
        self.btn_cancel = GlowButton("Cancel")
        self.btn_cancel.setObjectName("ActionPill")
        self.btn_cancel.setProperty("action_role", "ghost")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)
        
        layout.addLayout(btns)
        layout.addStretch(1)
        
        self.btn_primary.setFocus()









class ArtistDetailsDialog(QDialog):
    """
    Full Artist Editor with Memberships, Aliases, etc.
    """
    def __init__(self, artist, service, context_song=None, allow_remove_from_context=False, parent=None):
        super().__init__(parent)
        
        # 0. RESOLVE IDENTITY: Always edit the Master Record
        # If user clicked "Gabry Ponte" (Alias), we switch to "Gabriele Ponte" (Primary)
        # This prevents the confusing "Alias Rename Mode" and ensures we manage the full Identity.
        primary = service.get_primary_contributor(artist.contributor_id)
        self.artist = primary if primary else artist
        
        self.context_song = context_song
        self.original_type = artist.type
        self.service = service
        self.allow_remove = allow_remove_from_context
        self.setWindowTitle(f"Manager: {artist.name}")
        self.setObjectName("ArtistDetailsDialog")
        
        layout = QVBoxLayout(self)
        layout.setObjectName("ArtistDetailsLayout")
        
        self._init_ui(layout)
        self._refresh_data()

    def _init_ui(self, layout):
        # 1. Identity
        lbl_name = QLabel("ARTIST NAME")
        lbl_name.setObjectName("DialogFieldLabel")
        self.txt_name = GlowLineEdit()
        self.txt_name.edit.setPlaceholderText("Artist Name...")
        self.txt_name.edit.returnPressed.connect(self._save) # Snappy: Enter to Update
        
        layout.addWidget(lbl_name)
        layout.addWidget(self.txt_name)
        
        lbl_sort = QLabel("SORT NAME")
        lbl_sort.setObjectName("DialogFieldLabel")
        self.txt_sort = GlowLineEdit()
        self.txt_sort.edit.returnPressed.connect(self._save) # Snappy: Enter to Update
        layout.addWidget(lbl_sort)
        layout.addWidget(self.txt_sort)
        
        # Type (Buttons)
        t_row = QHBoxLayout()
        t_row.setSpacing(20)  # Extra space for glow margins
        t_row.setContentsMargins(0, 8, 10, 0)  # Removed bottom margin - let the glow breathe
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        
        self.radio_person = GlowButton("PERSON")
        self.radio_person.setObjectName("IdentityTypeButton")
        self.radio_person.setCheckable(True)
        self.radio_person.setMinimumHeight(48)  # Extra height for glow
        self.btn_group.addButton(self.radio_person.btn, 0)
        
        self.radio_group = GlowButton("GROUP")
        self.radio_group.setObjectName("IdentityTypeButton")
        self.radio_group.setCheckable(True)
        self.radio_group.setMinimumHeight(48)  # Extra height for glow
        self.btn_group.addButton(self.radio_group.btn, 1)
        
        # UI Refresh logic (Safe-Toggle)
        self.radio_person.toggled.connect(lambda checked: self._on_type_toggled("person") if checked else None)
        self.radio_group.toggled.connect(lambda checked: self._on_type_toggled("group") if checked else None)

        t_row.addWidget(self.radio_person)
        t_row.addWidget(self.radio_group)
        t_row.addStretch()
        layout.addLayout(t_row)
        
        # Spacer for glow to render without clipping
        layout.addSpacing(8)
        
        line = QFrame()
        line.setObjectName("FieldGroupLine")
        line.setFixedHeight(2)
        layout.addWidget(line)
        
        # Aliases - NOW USES EntityListWidget with chips!
        h_alias = QHBoxLayout()
        lbl_alias = QLabel("ALIASES")
        lbl_alias.setObjectName("DialogFieldLabel")
        h_alias.addWidget(lbl_alias)
        h_alias.addStretch()
        layout.addLayout(h_alias)
        
        # Create a mock service provider for EntityListWidgets
        # This is a temporary adapter until we have a real ServiceProvider
        class _ServiceAdapter:
            def __init__(self, service):
                self.contributor_service = service
        
        self._service_adapter = _ServiceAdapter(self.service)
        
        # Create alias adapter
        self._alias_adapter = ArtistAliasAdapter(
            self.artist,
            self.service,
            refresh_fn=self._refresh_data
        )
        
        self.list_aliases = EntityListWidget(
            service_provider=self._service_adapter,
            entity_type=EntityType.ALIAS,
            layout_mode=LayoutMode.CLOUD,  # Chips!
            context_adapter=self._alias_adapter,
            allow_add=True,  # Show the (+) button
            allow_remove=True,
            allow_edit=False,  # Context menu + Custom click handler instead
            add_tooltip="Add Alias",
            confirm_removal=False,  # Simplified removal
            parent=self
        )
        # Override the add handler to use our custom merge-based alias add
        if self.list_aliases.tray:
            # Disconnect default and connect our custom handler
            self.list_aliases.tray.add_requested.disconnect()
            self.list_aliases.tray.add_requested.connect(self._add_alias)
            # Normal click on alias -> Rename
            self.list_aliases.tray.chip_clicked.connect(self._on_alias_chip_clicked)

        # Connect to custom context menu for Promote/Rename actions
        self.list_aliases.chip_context_menu_requested.connect(self._show_alias_chip_menu)
        layout.addWidget(self.list_aliases)
        
        # Membership - NOW USES EntityListWidget!
        h_member = QHBoxLayout()
        self.lbl_member = QLabel("MEMBERS")
        self.lbl_member.setObjectName("DialogFieldLabel")
        h_member.addWidget(self.lbl_member)
        h_member.addStretch()
        layout.addLayout(h_member)
        
        # Create the member adapter (will be recreated on type toggle)
        self._member_adapter = ArtistMemberAdapter(
            self.artist, 
            self.service, 
            refresh_fn=self._refresh_data,
            parent=self
        )
        
        self.list_members = EntityListWidget(
            service_provider=self._service_adapter,
            entity_type=EntityType.GROUP_MEMBER,
            layout_mode=LayoutMode.CLOUD,  # Chips instead of list
            context_adapter=self._member_adapter,
            allow_add=True,
            allow_remove=True,
            allow_edit=True,
            add_tooltip="Add Member/Group",
            parent=self
        )
        self.list_members.setObjectName("ArtistSubList")
        
        # Set the picker filter based on artist type
        self.list_members.set_picker_filter(
            lambda: "person" if self.artist.type == "group" else "group"
        )
        # Override the add behavior for Person-to-Person merging
        if self.list_members.tray:
            self.list_members.tray.add_requested.disconnect()
            self.list_members.tray.add_requested.connect(self._add_member)
            
        layout.addWidget(self.list_members)
        
        btns = QHBoxLayout()
        btns.addStretch()
        
        # 1. Destructive (Left) - ONLY if in a context where unlinking makes sense
        if self.allow_remove:
            self.btn_delete = GlowButton("Remove")
            self.btn_delete.setObjectName("ActionPill")
            self.btn_delete.setProperty("action_role", "destructive")
            self.btn_delete.setToolTip("Unlink this artist from the current song(s)")
            self.btn_delete.clicked.connect(lambda: self.done(2)) # Code 2 = Remove Request
            btns.addWidget(self.btn_delete)
        
        # 2. Neutral (Middle)
        btn_cancel = GlowButton("Cancel")
        btn_cancel.setObjectName("ActionPill")
        btn_cancel.setProperty("action_role", "secondary")
        btn_cancel.clicked.connect(self.reject)
        btns.addWidget(btn_cancel)
        
        # 3. Primary (Right)
        btn_save = GlowButton("UPDATE")
        btn_save.setObjectName("ActionPill")
        btn_save.setProperty("action_role", "primary")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self._save)
        btns.addWidget(btn_save)

        btns.addStretch()
        layout.addLayout(btns)

    def _refresh_data(self):
        # Block signals to prevent recursion during programmatic check
        self.radio_person.blockSignals(True)
        self.radio_group.blockSignals(True)
        
        self.txt_name.setText(self.artist.name)
        self.txt_sort.setText(self.artist.sort_name)
        if self.artist.type == "group":
            self.radio_group.setChecked(True)
            self.radio_person.setChecked(False)
            self.lbl_member.setText("GROUP MEMBERS")
        else:
            self.radio_person.setChecked(True)
            self.radio_group.setChecked(False)
            self.lbl_member.setText("BELONGS TO GROUPS")
            
        self.radio_person.blockSignals(False)
        self.radio_group.blockSignals(False)
            
        # Aliases - now uses EntityListWidget!
        # Update the adapter with current artist
        self._alias_adapter = ArtistAliasAdapter(
            self.artist,
            self.service,
            refresh_fn=self._refresh_data
        )
        self.list_aliases.context_adapter = self._alias_adapter
        self.list_aliases.refresh_from_adapter()
            
        # Memberships - now uses EntityListWidget!
        # Update the adapter with current artist (type may have changed)
        self._member_adapter = ArtistMemberAdapter(
            self.artist,
            self.service,
            refresh_fn=self._refresh_data
        )
        self.list_members.context_adapter = self._member_adapter
        self.list_members.refresh_from_adapter()

    def _on_type_toggled(self, new_type):
        """Update local model and refresh context labels."""
        if self.artist.type == new_type:
            return
        self.artist.type = new_type
        self._refresh_data()

    def _add_alias(self):
        # UNIFY: Use the modern EntityPickerDialog (matching "add person" flow)
        # BUT filter to only show same-type artists (person for person, group for group)
        from .entity_picker_dialog import EntityPickerDialog
        from src.core.picker_config import get_artist_picker_config
        
        # Get service provider (need to wrap service for EntityPickerDialog)
        class _ServiceProvider:
            def __init__(self, service):
                self.contributor_service = service
        
        # Get base config and customize for alias-adding
        # User Request: "pick group alias should only show group" (Strict filtering)
        artist_type = self.artist.type.title()  # "person" -> "Person"
        
        config = get_artist_picker_config(allowed_types=[artist_type])
        config.title_add = f"Add Alias for {self.artist.name}"
        
        diag = EntityPickerDialog(
            service_provider=_ServiceProvider(self.service),
            config=config,
            exclude_ids={self.artist.contributor_id},
            parent=self
        )
        
        if diag.exec():
            target = diag.get_selected()
            
            if not target:
                return
                
            # Check for Self (should be excluded by Picker but safe check)
            if target.contributor_id == self.artist.contributor_id:
                return
            
            # It's an independent artist entity.
            # Since an alias in our schema IS a contributor link, 
            # we are effectively saying "This independent entity IS actually me."
            # This requires a MERGE operation (Absorb).
            
            # Double Check Type Safety
            if target.type != self.artist.type:
                 QMessageBox.warning(self, "Type Mismatch", 
                                   f"Cannot use '{target.name}' ({target.type}) as alias for '{self.artist.name}' ({self.artist.type}).\n\n"
                                   "Aliases must be of the same type.")
                 return
            
            # SCENARIO CHECK: Alias Match vs Primary Identity Match
            # The EntityPickerDialog returns an object where .name is set to the *Matched Name*.
            # We fetch the FRESH database record to get the *Primary Name*.
            real_target = self.service.get_by_id(target.contributor_id)
            if not real_target: return
            
            # CASE 1: ALIAS RE-LINKING (Scenario 2)
            if target.name != real_target.name:
                alias_name = target.name
                parent_name = real_target.name
                
                resolver = IdentityCollisionDialog(
                    description=f"'{alias_name}' is linked to '{parent_name}'.\n\nLink it to '{self.artist.name}' instead?",
                    parent=self
                )
                
                if resolver.exec() == 3: 
                    if self.service.move_alias(alias_name, real_target.contributor_id, self.artist.contributor_id):
                        self._refresh_data()
                return

            # CASE 2: IDENTITY MERGE (Scenario 3/4)
            aliases = self.service.get_aliases(target.contributor_id) # The "Baggage"
            
            # SCENARIO 3: IDENTITY MERGE - SILENT
            if not aliases:
                if self.service.merge(target.contributor_id, self.artist.contributor_id):
                    self._refresh_data()
                return

            # SCENARIO 4: BAGGAGE MERGE (Existing Aliases) - Prompt once
            resolver = IdentityCollisionDialog(
                description="Combine them?",
                parent=self
            )
            
            if resolver.exec() == 3:
                if self.service.merge(target.contributor_id, self.artist.contributor_id):
                    self._refresh_data()
                else:
                    QMessageBox.warning(self, "Error", "Could not combine artists.")
            


    def _on_alias_chip_clicked(self, alias_id, name):
        """Handle mouse click on alias chip - trigger rename."""
        self._edit_alias(alias_id, name)


    def _add_member(self):
        """Handle adding a member/group, with Person->Person merge bypass."""
        from .entity_picker_dialog import EntityPickerDialog
        from src.core.picker_config import get_artist_picker_config
        
        # Determine allowed types based on current artist
        # Person: Can join 'Group' OR merge with 'Person'
        # Group: Can have 'Person' members
        allowed = ["Group", "Person"] if self.artist.type == "person" else ["Person"]
        
        diag = EntityPickerDialog(
            service_provider=self._service_adapter,
            config=get_artist_picker_config(allowed_types=allowed),
            parent=self
        )
        
        if diag.exec():
            target = diag.get_selected()
            if not target: return
            
            # 1. Check types for Person->Person merge (The Gabriel/Gustavo Rule)
            # Fetch fresh model to be sure of type
            real_target = self.service.get_by_id(target.contributor_id)
            if not real_target: return
            
            if self.artist.type == "person" and real_target.type == "person":
                # They are the same artist? Merge identities.
                # Apply Baggage Rule
                aliases = self.service.get_aliases(target.contributor_id)
                
                if not aliases:
                    # SILENT
                    if self.service.merge(target.contributor_id, self.artist.contributor_id):
                        self._refresh_data()
                    return

                # PROMPT
                resolver = IdentityCollisionDialog(
                    target_name=real_target.name,
                    description="Combine them?",
                    parent=self
                )
                if resolver.exec() == 3:
                     if self.service.merge(target.contributor_id, self.artist.contributor_id):
                        self._refresh_data()
                return

            # 2. Normal Membership link (Group involved)
            # Use the adapter to handle the link correctly (handles alias names too)
            self._member_adapter.link(target.contributor_id, matched_alias=getattr(target, 'matched_alias', None))
            self._refresh_data()

    def _show_alias_chip_menu(self, alias_id, alias_name, global_pos):
        """Show context menu for alias chips."""
        menu = QMenu(self)
        
        promote_act = QAction("Set as Primary ★", self)
        promote_act.triggered.connect(lambda: self._promote_alias(alias_id, alias_name))
        menu.addAction(promote_act)
        
        menu.addSeparator()

        edit_act = QAction("Rename", self)
        edit_act.triggered.connect(lambda: self._edit_alias(alias_id, alias_name))
        menu.addAction(edit_act)
        
        del_act = QAction("Unlink Name", self)
        del_act.triggered.connect(lambda: self._confirm_delete_alias(alias_id, alias_name))
        menu.addAction(del_act)
        menu.exec(global_pos)

    def _confirm_delete_alias(self, alias_id, name):
        # Simplified: Just do it. Audit log handles the safety.
        if self.service.delete_alias(alias_id):
            self._refresh_data()

    def _promote_alias(self, alias_id, name):
        msg = f"This will make '{name}' the main artist name.\n\n"
        msg += f"'{self.artist.name}' will be kept as an alternative name.\n\n"
        msg += "Continue?"
        
        if QMessageBox.question(self, "Change Main Name", msg,
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if self.service.promote_alias(self.artist.contributor_id, alias_id):
                # We need to reload the whole artist object because the name changed
                self.artist = self.service.get_by_id(self.artist.contributor_id)
                self.setWindowTitle(f"Manager: {self.artist.name}")
                self._refresh_data()

    def _edit_alias(self, alias_id, old_name):
        from .entity_picker_dialog import EntityPickerDialog
        from src.core.picker_config import get_alias_picker_config
        from types import SimpleNamespace
        
        # Create mock entity for Rename mode
        target = SimpleNamespace(contributor_id=alias_id, name=old_name)
        
        diag = EntityPickerDialog(
            service_provider=self._service_adapter,
            config=get_alias_picker_config(),
            target_entity=target,
            parent=self
        )
        
        if diag.exec() == 1:
            if diag.is_rename_requested():
                new_name, _ = diag.get_rename_info()
                new_name = new_name.strip() if new_name else ""
                
                if new_name and new_name != old_name:
                    if self.service.update_alias(alias_id, new_name):
                        self._refresh_data()

    def _delete_alias(self, alias_id):
        # Unused now, replaced by confirm version
        pass

    # NOTE: _add_member, _show_member_menu, _remove_member are now handled by EntityListWidget
    # The old manual implementations have been removed.

    def _save(self):
        new_name = self.txt_name.text().strip()
        if not new_name: return
        
        new_type = "group" if self.radio_group.isChecked() else "person"
        
        # 1. COLLISION DETECTION & MERGE PROMPT
        # Check if name CHANGED (Case-sensitive check effectively, but we handle casing logic below)
        if new_name != self.artist.name:
            # Check if target exists (excluding self)
            target_collision = self.service.get_collision(new_name, self.artist.contributor_id)
            if target_collision:
                # IT EXISTS! Prompt the user.
                
                # Scenario 3: Identity Merge (Silent)
                target_aliases = self.service.get_aliases(target_collision.contributor_id)
                
                if not target_aliases:
                    if self.service.merge(self.artist.contributor_id, target_collision.contributor_id):
                        self.done(3)
                    return

                # Scenario 4: Baggage Merge (Prompt once)
                resolver = IdentityCollisionDialog(
                    description="Combine them?",
                    parent=self
                )
                if resolver.exec() == 3:
                    if self.service.merge(self.artist.contributor_id, target_collision.contributor_id):
                        self.done(3)
                        return
                    else:
                        QMessageBox.warning(self, "Error", "Could not combine artists.")
                        return
                return

        # Safety check for type change (Data integrity)
        if self.original_type != new_type:
            if self.original_type == "group":
                # Losing 'Children'
                count = len(self.service.get_members(self.artist.contributor_id))
                relation = "member"
            else:
                # Losing 'Parents'
                count = len(self.service.get_groups(self.artist.contributor_id))
                relation = "group membership"

            if count > 0:
                msg = f"Changing this {self.original_type.capitalize()} to a {new_type.capitalize()} will remove {count} existing {relation}(s). Are you sure?"
                if QMessageBox.warning(self, "Confirm Type Change", msg, 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
                    return
        
        self.artist.name = new_name
        self.artist.sort_name = self.txt_sort.text().strip()
        self.artist.type = new_type
        
        if self.service.update(self.artist):
            self.done(3) # Signal 3: Data Changed (Sync Required)
        else:
            QMessageBox.warning(self, "Error", "Failed to save artist changes.")

