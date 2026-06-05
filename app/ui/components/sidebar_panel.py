"""Sidebar Panel — collapsible left rail with session history organized in folders, search, and actions.

Single Responsibility: owns all sidebar UI state and exposes clean signals + methods.
Coupling:             communicates outward only through signals; receives data via populate().
"""
from datetime import datetime
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTreeWidget, QTreeWidgetItem, QWidget, QMenu, QSizePolicy
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QCursor, QIcon


# ── Custom Tree Widget with internal Drag-and-Drop ────────────────────

class SessionTreeWidget(QTreeWidget):
    """Custom QTreeWidget specializing in drag-and-drop and custom items."""
    session_moved = Signal(int, object)  # (session_id, folder_id_or_none)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.InternalMove)
        self.setSelectionMode(QTreeWidget.SingleSelection)
        self.setHeaderHidden(True)
        self.setRootIsDecorated(False)  # Hide default expand/collapse icons
        self.setIndentation(15)

    def dragEnterEvent(self, event):
        # Only accept drag if we are dragging a session item
        item = self.currentItem()
        if item and item.data(0, Qt.UserRole) and item.data(0, Qt.UserRole).get("type") == "session":
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        dragged_item = self.currentItem()
        if not dragged_item or not dragged_item.data(0, Qt.UserRole) or dragged_item.data(0, Qt.UserRole).get("type") != "session":
            event.ignore()
            return

        session_id = dragged_item.data(0, Qt.UserRole)["id"]
        
        # Determine target item under drop position
        target_item = self.itemAt(event.position().toPoint())
        
        folder_id = None
        if target_item:
            target_data = target_item.data(0, Qt.UserRole)
            if target_data:
                if target_data.get("type") == "folder":
                    folder_id = target_data["id"]
                elif target_data.get("type") == "session":
                    # If dropped on a session, move to that session's folder (parent)
                    parent_item = target_item.parent()
                    if parent_item and parent_item.data(0, Qt.UserRole):
                        folder_id = parent_item.data(0, Qt.UserRole)["id"]
        
        self.session_moved.emit(session_id, folder_id)
        event.acceptProposedAction()


# ── Custom Row Widgets for Folders and Sessions ──────────────────────

class FolderRowWidget(QWidget):
    """Custom row widget for rendering folders in the QTreeWidget."""
    def __init__(self, item: QTreeWidgetItem, folder_name: str, folder_id: int, kebab_callback):
        super().__init__()
        self.item = item
        self.folder_id = folder_id
        self.setStyleSheet("background: transparent;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)
        
        self.toggle_btn = QPushButton("+")
        self.toggle_btn.setFixedSize(18, 18)
        self.toggle_btn.setFocusPolicy(Qt.NoFocus)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #E5E7EB; border-radius: 4px;
                background-color: #F9FAFB; color: #6B7280;
                font-size: 11px; font-weight: bold; padding: 0;
            }
            QPushButton:hover {
                border-color: #0F7A75; color: #0F7A75; background-color: #E6F4F2;
            }
        """)
        self.toggle_btn.clicked.connect(self._on_toggle_clicked)
        layout.addWidget(self.toggle_btn)
        
        icon_label = QLabel("📁")
        icon_label.setStyleSheet("font-size: 13px;")
        layout.addWidget(icon_label)
        
        name_label = QLabel(folder_name)
        name_label.setStyleSheet("font-weight: 600; color: #111827; font-size: 12px;")
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        kebab_btn = QPushButton("⋮")
        kebab_btn.setFixedSize(20, 20)
        kebab_btn.setFocusPolicy(Qt.NoFocus)
        kebab_btn.setToolTip("Folder Options")
        kebab_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent; border: none;
                color: #9CA3AF; font-size: 14px; font-weight: bold; padding: 0;
            }
            QPushButton:hover {
                color: #111827; background-color: #F3F4F6; border-radius: 4px;
            }
        """)
        kebab_btn.clicked.connect(lambda: kebab_callback(kebab_btn, self.folder_id, folder_name))
        layout.addWidget(kebab_btn)
        
    def update_toggle_icon(self):
        if self.item.isExpanded():
            self.toggle_btn.setText("−")  # Unicode minus
        else:
            self.toggle_btn.setText("+")
            
    def _on_toggle_clicked(self):
        self.item.setExpanded(not self.item.isExpanded())
        self.update_toggle_icon()


class SessionRowWidget(QWidget):
    """Custom row widget for rendering sessions in the QTreeWidget."""
    def __init__(self, item: QTreeWidgetItem, title: str, date_str: str, duration_sec: float, session_id: int, kebab_callback):
        super().__init__()
        self.item = item
        self.session_id = session_id
        self.setStyleSheet("background: transparent;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)
        
        icon_label = QLabel("📄")
        icon_label.setStyleSheet("font-size: 13px; color: #FF6FA3;")
        layout.addWidget(icon_label)
        
        text_container = QWidget()
        text_container.setStyleSheet("background: transparent;")
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 12px; font-weight: 500; color: #111827;")
        text_layout.addWidget(self.title_label)
        
        self.sub_label = QLabel(f"{date_str} • {duration_sec:.1f}s")
        self.sub_label.setStyleSheet("font-size: 10px; color: #6B7280;")
        text_layout.addWidget(self.sub_label)
        
        layout.addWidget(text_container)
        layout.addStretch()
        
        kebab_btn = QPushButton("⋮")
        kebab_btn.setFixedSize(20, 20)
        kebab_btn.setFocusPolicy(Qt.NoFocus)
        kebab_btn.setToolTip("Session Options")
        kebab_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent; border: none;
                color: #9CA3AF; font-size: 14px; font-weight: bold; padding: 0;
            }
            QPushButton:hover {
                color: #111827; background-color: #F3F4F6; border-radius: 4px;
            }
        """)
        kebab_btn.clicked.connect(lambda: kebab_callback(kebab_btn, self.session_id, title))
        layout.addWidget(kebab_btn)


# ── Sidebar Panel Main Widget ─────────────────────────────────────────

class SidebarPanel(QFrame):
    """Collapsible left sidebar showing past session history organized in folders."""

    # ── Public signals (the contract with the outside world) ──────────
    new_session_requested     = Signal()
    session_selected          = Signal(int)   # session_id
    delete_selected_requested = Signal()
    delete_all_requested      = Signal()
    create_folder_requested   = Signal()
    folder_deleted            = Signal(int)   # folder_id
    session_moved             = Signal(int, object)  # session_id, folder_id (int or None)
    rename_folder_requested   = Signal(int)   # folder_id
    rename_session_requested  = Signal(int)   # session_id

    # ── Layout constants ──────────────────────────────────────────────
    EXPANDED_WIDTH  = 280
    COLLAPSED_WIDTH = 80   # 56 px button + 12 px margin × 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidePanel")
        self.setFixedWidth(self.EXPANDED_WIDTH)
        self._collapsed = False
        self._last_folders = []
        self._last_sessions = []
        self._folder_widgets = {}
        self._build_layout()

    # ── Construction ──────────────────────────────────────────────────

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addLayout(self._build_header())
        layout.addWidget(self._build_search())
        layout.addWidget(self._build_session_tree())
        layout.addLayout(self._build_delete_row())

        # Add dynamic vertical spacer that is only visible when collapsed
        self.spacer_widget = QWidget()
        self.spacer_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.spacer_widget.setVisible(False)
        layout.addWidget(self.spacer_widget)

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)

        self.collapse_btn = QPushButton()
        self.collapse_btn.setFixedSize(56, 30)
        self.collapse_btn.setToolTip("Collapse")
        self.collapse_btn.setStyleSheet(
            "QPushButton { border-radius: 6px; }"
        )
        import os
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "collapse_icon.png")
        if os.path.exists(icon_path):
            self.collapse_btn.setIcon(QIcon(icon_path))
            self.collapse_btn.setIconSize(QSize(20, 20))
        self.collapse_btn.clicked.connect(self._on_toggle_clicked)
        row.addWidget(self.collapse_btn)

        self.title_label = QLabel("PAST SESSIONS")
        self.title_label.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #6B7280; letter-spacing: 1.5px;"
        )
        row.addWidget(self.title_label)

        # Create Folder button
        self.new_folder_btn = QPushButton()
        self.new_folder_btn.setToolTip("Create new folder")
        self.new_folder_btn.setFixedSize(32, 30)
        self.new_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF; border: 1px solid #E5E7EB;
                border-radius: 6px; padding: 0;
            }
            QPushButton:hover {
                border-color: #0F7A75; background-color: #E6F4F2;
            }
        """)
        import os
        components_dir = os.path.dirname(__file__)
        root_dir = os.path.abspath(os.path.join(components_dir, "..", "..", ".."))
        icon_path = os.path.join(root_dir, "Icons", "Adds Add folder.png")
        if os.path.exists(icon_path):
            self.new_folder_btn.setIcon(QIcon(icon_path))
            self.new_folder_btn.setIconSize(QSize(20, 20))
        
        self.new_folder_btn.clicked.connect(self.create_folder_requested.emit)
        row.addWidget(self.new_folder_btn)

        # Create Session button
        self.new_btn = QPushButton("📝")
        self.new_btn.setToolTip("New recording session")
        self.new_btn.setFixedSize(32, 30)
        self.new_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF; border: 1px solid #E5E7EB;
                border-radius: 6px; color: #FF6FA3; font-size: 15px; padding: 0;
            }
            QPushButton:hover {
                border-color: #FF6FA3; background-color: #FF6FA3; color: #FFFFFF;
            }
        """)
        self.new_btn.clicked.connect(self.new_session_requested.emit)
        row.addWidget(self.new_btn)

        return row

    def _build_search(self) -> QLineEdit:
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search past sessions...")
        return self.search_input

    def _build_session_tree(self) -> QTreeWidget:
        self.session_tree = SessionTreeWidget()
        self.session_tree.session_moved.connect(self.session_moved.emit)
        self.session_tree.itemClicked.connect(self._on_item_clicked)
        # Connect expand/collapse signals to keep custom folder plus/minus toggles in sync
        self.session_tree.itemExpanded.connect(self._update_all_folder_toggles)
        self.session_tree.itemCollapsed.connect(self._update_all_folder_toggles)
        return self.session_tree

    def _build_delete_row(self) -> QHBoxLayout:
        row = QHBoxLayout()

        self.delete_btn = QPushButton("DELETE SELECTED")
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF; border: 1px solid #E5E7EB;
                color: #E02424; font-size: 10px; font-weight: bold; padding: 6px;
            }
            QPushButton:hover {
                background-color: #E02424; color: #FFFFFF; border-color: #E02424;
            }
        """)
        self.delete_btn.clicked.connect(self.delete_selected_requested.emit)
        row.addWidget(self.delete_btn)

        self.delete_all_btn = QPushButton("🗑️")
        self.delete_all_btn.setToolTip("Delete all sessions")
        self.delete_all_btn.setFixedSize(30, 30)
        self.delete_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF; border: 1px solid #E5E7EB;
                color: #E02424; font-size: 13px; border-radius: 6px; padding: 0;
            }
            QPushButton:hover {
                background-color: #E02424; color: #FFFFFF; border-color: #E02424;
            }
        """)
        self.delete_all_btn.clicked.connect(self.delete_all_requested.emit)
        row.addWidget(self.delete_all_btn)

        return row

    # ── Public API ────────────────────────────────────────────────────

    @property
    def is_collapsed(self) -> bool:
        return self._collapsed

    @property
    def search_text(self) -> str:
        return self.search_input.text().strip().lower()

    def connect_search(self, slot) -> None:
        """Connect search-input changes to an external slot."""
        self.search_input.textChanged.connect(slot)

    def populate(self, folders: List[Dict[str, Any]], sessions: List[Dict[str, Any]]) -> None:
        """Rebuild the hierarchical session tree, applying the search filter."""
        self._last_folders = folders
        self._last_sessions = sessions

        # 1. Save expanded states of existing folders
        expanded_folders = set()
        for i in range(self.session_tree.topLevelItemCount()):
            item = self.session_tree.topLevelItem(i)
            data = item.data(0, Qt.UserRole)
            if data and data.get("type") == "folder" and item.isExpanded():
                expanded_folders.add(data["id"])

        self.session_tree.clear()
        self._folder_widgets = {}
        
        q = self.search_text

        # Create folder tree items
        folder_items = {}
        for f in folders:
            folder_item = QTreeWidgetItem(self.session_tree)
            folder_item.setData(0, Qt.UserRole, {"type": "folder", "id": f["id"]})
            # Folders can accept drops but cannot be dragged
            folder_item.setFlags(folder_item.flags() & ~Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
            folder_items[f["id"]] = folder_item

            # Build custom row widget
            row_widget = FolderRowWidget(
                item=folder_item,
                folder_name=f["name"],
                folder_id=f["id"],
                kebab_callback=self._show_folder_kebab_menu
            )
            self.session_tree.setItemWidget(folder_item, 0, row_widget)
            folder_item.setSizeHint(0, QSize(100, 40))
            self._folder_widgets[f["id"]] = row_widget

        # Track if folders contain visible items
        folder_has_visible_children = {fid: False for fid in folder_items}

        # Populate sessions
        for s in sessions:
            title = s["title"]
            if q and q not in title.lower():
                continue

            date_str = datetime.fromisoformat(s["created_at"]).strftime("%Y-%m-%d %H:%M")
            duration = s["duration_sec"]
            session_id = s["id"]
            fid = s["folder_id"]

            parent_item = self.session_tree
            if fid is not None and fid in folder_items:
                parent_item = folder_items[fid]
                folder_has_visible_children[fid] = True

            session_item = QTreeWidgetItem(parent_item)
            session_item.setData(0, Qt.UserRole, {"type": "session", "id": session_id})
            # Sessions can be dragged but cannot receive drops
            session_item.setFlags(session_item.flags() | Qt.ItemIsDragEnabled & ~Qt.ItemIsDropEnabled)

            row_widget = SessionRowWidget(
                item=session_item,
                title=title,
                date_str=date_str,
                duration_sec=duration,
                session_id=session_id,
                kebab_callback=self._show_session_kebab_menu
            )
            self.session_tree.setItemWidget(session_item, 0, row_widget)
            session_item.setSizeHint(0, QSize(100, 46))

        # Hide folders that have no visible children during search, unless folder name matches
        for fid, item in folder_items.items():
            folder_name = next((f["name"] for f in folders if f["id"] == fid), "").lower()
            name_matches = q and q in folder_name
            
            if q and not name_matches and not folder_has_visible_children[fid]:
                item.setHidden(True)
            else:
                item.setHidden(False)
                # Expand folder automatically if matching during search, or if it was previously expanded
                if q:
                    item.setExpanded(True)
                    if fid in self._folder_widgets:
                        self._folder_widgets[fid].update_toggle_icon()
                elif fid in expanded_folders:
                    item.setExpanded(True)
                    if fid in self._folder_widgets:
                        self._folder_widgets[fid].update_toggle_icon()

    def select_by_id(self, session_id: Optional[int]) -> None:
        """Highlight the tree entry matching the given session ID."""
        if session_id is None:
            self.session_tree.setCurrentItem(None)
            return
            
        root = self.session_tree.invisibleRootItem()
        item = self._find_session_item(root, session_id)
        if item:
            self.session_tree.setCurrentItem(item)

    def current_session_id(self) -> Optional[int]:
        """Return the session_id of the selected list item, or None."""
        item = self.session_tree.currentItem()
        if item:
            data = item.data(0, Qt.UserRole)
            if data and data.get("type") == "session":
                return data["id"]
        return None

    def expand(self) -> None:
        """Restore sidebar to its full expanded width."""
        self._collapsed = False
        self.setFixedWidth(self.EXPANDED_WIDTH)
        for w in (self.title_label, self.new_folder_btn, self.new_btn, self.search_input,
                  self.session_tree, self.delete_btn, self.delete_all_btn):
            w.setVisible(True)
        self.spacer_widget.setVisible(False)
        self.collapse_btn.setToolTip("Collapse")

    def collapse(self) -> None:
        """Shrink sidebar to an icon-only rail showing only the expand button."""
        self._collapsed = True
        self.setFixedWidth(self.COLLAPSED_WIDTH)
        for w in (self.title_label, self.new_folder_btn, self.new_btn, self.search_input,
                  self.session_tree, self.delete_btn, self.delete_all_btn):
            w.setVisible(False)
        self.spacer_widget.setVisible(True)
        self.collapse_btn.setToolTip("Expand")

    # ── Internal ──────────────────────────────────────────────────────

    def _on_toggle_clicked(self) -> None:
        if self._collapsed:
            self.expand()
        else:
            self.collapse()

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        data = item.data(0, Qt.UserRole)
        if data and data.get("type") == "session":
            self.session_selected.emit(data["id"])

    def _find_session_item(self, parent_item: QTreeWidgetItem, session_id: int) -> Optional[QTreeWidgetItem]:
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            data = child.data(0, Qt.UserRole)
            if data and data.get("type") == "session" and data.get("id") == session_id:
                return child
            res = self._find_session_item(child, session_id)
            if res:
                return res
        return None

    def _update_all_folder_toggles(self) -> None:
        """Helper to sync the text (+ / -) of custom folder row toggles on expansion events."""
        for fid, widget in self._folder_widgets.items():
            widget.update_toggle_icon()

    def _menu_stylesheet(self) -> str:
        return """
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #E5E7EB;
                border-radius: 8px;
                padding: 4px;
                font-size: 12px;
                color: #111827;
            }
            QMenu::item {
                padding: 7px 20px 7px 12px;
                border-radius: 5px;
                color: #111827;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #FFE4E6;
                color: #FF6FA3;
            }
            QMenu::separator {
                height: 1px;
                background: #E5E7EB;
                margin: 4px 8px;
            }
        """

    def _show_folder_kebab_menu(self, button: QPushButton, folder_id: int, folder_name: str) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(self._menu_stylesheet())
        
        rename_action = menu.addAction("📝  Rename Folder")
        delete_action = menu.addAction("❌  Delete Folder")
        
        action = menu.exec(button.mapToGlobal(button.rect().bottomLeft()))
        if action == rename_action:
            self.rename_folder_requested.emit(folder_id)
        elif action == delete_action:
            self.folder_deleted.emit(folder_id)

    def _show_session_kebab_menu(self, button: QPushButton, session_id: int, title: str) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(self._menu_stylesheet())
        
        rename_action = menu.addAction("📝  Rename Session")
        
        move_menu = menu.addMenu("📁  Move to Folder")
        move_menu.setStyleSheet(self._menu_stylesheet())
        
        ungroup_action = move_menu.addAction("📂  Ungrouped (Root)")
        
        folder_actions = {}
        for folder in self._last_folders:
            folder_action = move_menu.addAction(f"📁  {folder['name']}")
            folder_actions[folder_action] = folder["id"]
            
        menu.addSeparator()
        delete_action = menu.addAction("❌  Delete Session")
        
        action = menu.exec(button.mapToGlobal(button.rect().bottomLeft()))
        if action == rename_action:
            self.rename_session_requested.emit(session_id)
        elif action == delete_action:
            self.select_by_id(session_id)
            self.delete_selected_requested.emit()
        elif action == ungroup_action:
            self.session_moved.emit(session_id, None)
        elif action in folder_actions:
            target_folder_id = folder_actions[action]
            self.session_moved.emit(session_id, target_folder_id)
