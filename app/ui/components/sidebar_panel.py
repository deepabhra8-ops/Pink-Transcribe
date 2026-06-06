"""Sidebar Panel — collapsible left rail with session history organized in folders, search, and actions.

Single Responsibility: owns all sidebar UI state and exposes clean signals + methods.
Coupling:             communicates outward only through signals; receives data via populate().
"""
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTreeWidget, QTreeWidgetItem, QWidget, QMenu, QSizePolicy
)
from PySide6.QtCore import Signal, Qt, QSize, Property, QPropertyAnimation, QEasingCurve, QVariantAnimation
from PySide6.QtGui import QCursor, QIcon, QPainter, QPainterPath, QColor, QPen, QRegion


# ── Custom Tree Widget ────────────────────────────────────────────────

class SessionTreeWidget(QTreeWidget):
    """Custom QTreeWidget specializing in custom items."""
    session_moved = Signal(int, object)  # (session_id, folder_id_or_none)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QTreeWidget.SingleSelection)
        self.setHeaderHidden(True)
        self.setRootIsDecorated(False)  # Hide default expand/collapse icons
        self.setIndentation(24)         # Increased indentation for hierarchy cues
        self.setExpandsOnDoubleClick(False) # Disable instant double-click expanding/collapsing


# ── Chevron Button for Folder Expand/Collapse ─────────────────────────

class ChevronButton(QPushButton):
    """Sleek borderless button drawing a rotating vector chevron."""
    _rotation = 0.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(26, 26)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet("background: transparent; border: none; margin: 0; padding: 0;")
        
        self.anim = QPropertyAnimation(self, b"rotation")
        self.anim.setDuration(500)
        self.anim.setEasingCurve(QEasingCurve.InOutCubic)  # Coordinated luxury InOut curve

    @Property(float)
    def rotation(self) -> float:
        return self._rotation

    @rotation.setter
    def rotation(self, val: float) -> None:
        self._rotation = val
        self.update()

    def set_expanded(self, expanded: bool, animate: bool = True) -> None:
        target = 90.0 if expanded else 0.0
        if animate:
            if self.anim.state() == QPropertyAnimation.Running and self.anim.endValue() == target:
                return
            self.anim.stop()
            self.anim.setStartValue(self._rotation)
            self.anim.setEndValue(target)
            self.anim.start()
        else:
            if self.anim.state() == QPropertyAnimation.Running and self.anim.endValue() == target:
                return
            self.anim.stop()
            self.rotation = target

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if not self.isEnabled():
            color = QColor("#D1D5DB")
        elif self.underMouse():
            color = QColor("#0F7A75")  # Brand teal on hover
        else:
            color = QColor("#6B7280")  # Neutral grey
            
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self._rotation)
        
        path = QPainterPath()
        path.moveTo(-2, -5)
        path.lineTo(3, 0)
        path.lineTo(-2, 5)
        
        pen = QPen(color, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(path)


class SessionContainerWidget(QFrame):
    """Container widget housing multiple SessionRowWidgets inside a folder."""
    session_selected = Signal(int)

    def __init__(self, parent_item: QTreeWidgetItem, parent=None):
        super().__init__(parent)
        self.parent_item = parent_item
        self.setObjectName("sessionContainer")
        self.setStyleSheet("""
            #sessionContainer {
                background-color: rgba(255, 255, 255, 0.40);
                border: 1px solid #EAD8DD;
                border-radius: 6px;
            }
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.session_widgets: Dict[int, SessionRowWidget] = {}
        
    def add_session(self, s: Dict[str, Any], kebab_callback, is_first_nested: bool = False) -> SessionRowWidget:
        date_str = datetime.fromisoformat(s["created_at"]).strftime("%Y-%m-%d %H:%M")
        row = SessionRowWidget(
            item=self.parent_item,
            title=s["title"],
            date_str=date_str,
            duration_sec=s["duration_sec"],
            session_id=s["id"],
            kebab_callback=kebab_callback,
            is_nested=True,
            is_first_nested=is_first_nested
        )
        row.clicked.connect(self._on_row_clicked)
        self.main_layout.addWidget(row)
        self.session_widgets[s["id"]] = row
        return row
        
    def _on_row_clicked(self, session_id: int):
        self.select_session(session_id)
        self.session_selected.emit(session_id)
        
    def select_session(self, session_id: Optional[int]):
        for sid, widget in self.session_widgets.items():
            widget.set_selected(sid == session_id)
            
    def clear_selection(self):
        self.select_session(None)
        
    def filter_sessions(self, query: str) -> int:
        """Show/hide child widgets based on search query. Returns count of visible sessions."""
        visible_count = 0
        for sid, widget in self.session_widgets.items():
            matches = not query or query in widget.title_label.text().lower()
            widget.setVisible(matches)
            if matches:
                visible_count += 1
        return visible_count

    def calculate_total_height(self) -> int:
        """Sum of heights of visible sessions plus margins."""
        h = 0
        visible_count = 0
        for widget in self.session_widgets.values():
            if widget.isVisible():
                h += 54
                visible_count += 1
        if visible_count > 0:
            h += 2 # Accounting for 1px top + 1px bottom borders
        return h


class FolderRowWidget(QFrame):
    """Custom row widget for rendering folders in the QTreeWidget."""
    def __init__(self, item: QTreeWidgetItem, folder_name: str, folder_id: int, kebab_callback):
        super().__init__()
        self.item = item
        self.folder_id = folder_id
        self.setObjectName("folderRow")
        self.setStyleSheet("""
            #folderRow {
                background-color: transparent;
                border-radius: 6px;
            }
            #folderRow:hover {
                background-color: rgba(255, 111, 163, 0.08);
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(8)
        
        self.toggle_btn = ChevronButton(self)
        self.toggle_btn.clicked.connect(self._on_toggle_clicked)
        layout.addWidget(self.toggle_btn)
        
        icon_label = QLabel("📁")
        icon_label.setStyleSheet("font-size: 17px;")
        layout.addWidget(icon_label)
        
        name_label = QLabel(folder_name)
        name_label.setStyleSheet("font-weight: 600; color: #111827; font-size: 14px;")
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        kebab_btn = QPushButton("⋮")
        kebab_btn.setFixedSize(26, 26)
        kebab_btn.setFocusPolicy(Qt.NoFocus)
        kebab_btn.setToolTip("Folder Options")
        kebab_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent; border: none;
                color: #9CA3AF; font-size: 18px; font-weight: bold; padding: 0;
            }
            QPushButton:hover {
                color: #FF6FA3; background-color: #FFF5F7; border-radius: 6px;
            }
            QPushButton:pressed {
                background-color: #FFE4E6;
            }
        """)
        kebab_btn.clicked.connect(lambda: kebab_callback(kebab_btn, self.folder_id, folder_name))
        layout.addWidget(kebab_btn)
        
    def update_toggle_icon(self, animate: bool = True):
        is_expanded = self.item.isExpanded()
        self.toggle_btn.set_expanded(is_expanded, animate)
            
    def _on_toggle_clicked(self):
        self.toggle_expand()

    def toggle_expand(self, animate: bool = True) -> None:
        is_expanded = self.item.isExpanded()
        if is_expanded:
            self.collapse(animate)
        else:
            self.expand(animate)

    def expand(self, animate: bool = True) -> None:
        self.toggle_btn.set_expanded(True, animate)
        
        if self.item.childCount() == 0:
            self.item.setExpanded(True)
            return
            
        container_item = self.item.child(0)
        if container_item.isHidden():
            self.item.setExpanded(True)
            return
            
        tree = self.item.treeWidget()
        container_widget = tree.itemWidget(container_item, 0) if tree else None
        if not isinstance(container_widget, SessionContainerWidget):
            self.item.setExpanded(True)
            return
            
        target_height = container_widget.calculate_total_height()

        if animate:
            # Determine starting height from any in-progress animation
            if hasattr(self, "_height_anim") and self._height_anim is not None and \
               self._height_anim.state() == QVariantAnimation.Running:
                sh = container_item.sizeHint(0)
                start_val = sh.height() if (sh.isValid() and sh.height() >= 0) else 0
                self._height_anim.stop()
            else:
                start_val = 0
            
            container_item.setSizeHint(0, QSize(100, start_val))
            self.item.setExpanded(True)
            if tree:
                tree.scheduleDelayedItemsLayout()
                
            self._height_anim = QVariantAnimation(self)
            self._height_anim.setDuration(400)
            self._height_anim.setEasingCurve(QEasingCurve.OutCubic)
            self._height_anim.setStartValue(start_val)
            self._height_anim.setEndValue(target_height)
            
            def update_height(val):
                container_item.setSizeHint(0, QSize(100, int(val)))
                if tree:
                    tree.scheduleDelayedItemsLayout()
                    
            def on_expand_finished():
                container_item.setSizeHint(0, QSize(100, target_height))
                if tree:
                    tree.updateGeometries()
                    
            self._height_anim.valueChanged.connect(update_height)
            self._height_anim.finished.connect(on_expand_finished)
            self._height_anim.start()
        else:
            self.item.setExpanded(True)
            container_item.setSizeHint(0, QSize(100, target_height))
            if tree:
                tree.updateGeometries()

    def collapse(self, animate: bool = True) -> None:
        self.toggle_btn.set_expanded(False, animate)
        
        if self.item.childCount() == 0:
            self.item.setExpanded(False)
            return
            
        container_item = self.item.child(0)
        if container_item.isHidden():
            self.item.setExpanded(False)
            return
            
        tree = self.item.treeWidget()
        container_widget = tree.itemWidget(container_item, 0) if tree else None
        if not isinstance(container_widget, SessionContainerWidget):
            self.item.setExpanded(False)
            return
            
        if animate:
            # Determine starting height from current visible state
            if hasattr(self, "_height_anim") and self._height_anim is not None and \
               self._height_anim.state() == QVariantAnimation.Running:
                sh = container_item.sizeHint(0)
                start_val = sh.height() if (sh.isValid() and sh.height() >= 0) else container_widget.calculate_total_height()
                self._height_anim.stop()
            else:
                start_val = container_widget.calculate_total_height()
                
            self._height_anim = QVariantAnimation(self)
            self._height_anim.setDuration(400)
            self._height_anim.setEasingCurve(QEasingCurve.InOutCubic)
            self._height_anim.setStartValue(start_val)
            self._height_anim.setEndValue(0)
            
            def update_height(val):
                container_item.setSizeHint(0, QSize(100, int(val)))
                if tree:
                    tree.scheduleDelayedItemsLayout()
                    
            def on_collapse_finished():
                self.item.setExpanded(False)
                container_item.setSizeHint(0, QSize(100, container_widget.calculate_total_height()))
                if tree:
                    tree.updateGeometries()
                    
            self._height_anim.valueChanged.connect(update_height)
            self._height_anim.finished.connect(on_collapse_finished)
            self._height_anim.start()
        else:
            self.item.setExpanded(False)
            container_item.setSizeHint(0, QSize(100, container_widget.calculate_total_height()))
            if tree:
                tree.updateGeometries()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.toggle_expand()
            event.accept()
            return
        super().mousePressEvent(event)



class SessionRowWidget(QFrame):
    """Custom row widget for rendering sessions in the QTreeWidget."""
    clicked = Signal(int)

    def __init__(self, item: QTreeWidgetItem, title: str, date_str: str, duration_sec: float, session_id: int, kebab_callback, is_nested: bool = False, is_first_nested: bool = False):
        super().__init__()
        self.item = item
        self.session_id = session_id
        
        layout = QHBoxLayout(self)
        if is_nested:
            layout.setContentsMargins(8, 4, 8, 4)
            self.setObjectName("nestedSession")
            divider_style = "border-top: 1px solid #EAD8DD;" if not is_first_nested else ""
            self.setStyleSheet(f"""
                #nestedSession {{
                    background-color: transparent;
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 4px;
                    {divider_style}
                }}
                #nestedSession:hover {{
                    background-color: rgba(255, 111, 163, 0.08);
                }}
                #nestedSession[selected="true"] {{
                    background-color: rgba(255, 255, 255, 0.75);
                    border-left: 3px solid #FF6FA3;
                }}
            """)
        else:
            layout.setContentsMargins(6, 4, 6, 4)
            self.setObjectName("sessionRow")
            self.setStyleSheet("""
                #sessionRow {
                    background-color: transparent;
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 6px;
                }
                #sessionRow:hover {
                    background-color: rgba(255, 111, 163, 0.08);
                }
                #sessionRow[selected="true"] {
                    background-color: #FFE4E6;
                    border-left: 3px solid #FF6FA3;
                }
            """)
            
        layout.setSpacing(8)
        self.setFixedHeight(54)
        
        icon_label = QLabel("📄")
        icon_label.setStyleSheet("font-size: 17px; color: #FF6FA3; background: transparent;")
        layout.addWidget(icon_label)
        
        text_container = QWidget()
        text_container.setStyleSheet("background: transparent;")
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 500; color: #111827; background: transparent;")
        text_layout.addWidget(self.title_label)
        
        self.sub_label = QLabel(f"{date_str} • {duration_sec:.1f}s")
        self.sub_label.setStyleSheet("font-size: 11px; color: #6B7280; background: transparent;")
        text_layout.addWidget(self.sub_label)
        
        layout.addWidget(text_container)
        layout.addStretch()
        
        kebab_btn = QPushButton("⋮")
        kebab_btn.setFixedSize(26, 26)
        kebab_btn.setFocusPolicy(Qt.NoFocus)
        kebab_btn.setToolTip("Session Options")
        kebab_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent; border: none;
                color: #9CA3AF; font-size: 18px; font-weight: bold; padding: 0;
            }
            QPushButton:hover {
                color: #FF6FA3; background-color: #FFF5F7; border-radius: 6px;
            }
            QPushButton:pressed {
                background-color: #FFE4E6;
            }
        """)
        kebab_btn.clicked.connect(lambda: kebab_callback(kebab_btn, self.session_id, title))
        layout.addWidget(kebab_btn)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.session_id)
        super().mousePressEvent(event)


# ── Sidebar Panel Main Widget ─────────────────────────────────────────

class SidebarPanel(QFrame):
    """Collapsible left sidebar showing past session history organized in folders."""

    # ── Public signals (the contract with the outside world) ──────────
    new_session_requested           = Signal()
    new_session_in_folder_requested = Signal(int)   # folder_id
    session_selected                = Signal(int)   # session_id
    delete_selected_requested       = Signal()
    create_folder_requested         = Signal()
    folder_deleted                  = Signal(int)   # folder_id
    session_moved                   = Signal(int, object)  # session_id, folder_id (int or None)
    rename_folder_requested         = Signal(int)   # folder_id
    rename_session_requested        = Signal(int)   # session_id

    # ── Layout constants ──────────────────────────────────────────────
    EXPANDED_WIDTH  = 320
    COLLAPSED_WIDTH = 56

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidePanel")
        self.setFixedWidth(self.EXPANDED_WIDTH)
        self._collapsed = False
        self._last_folders = []
        self._last_sessions = []
        self._folder_widgets = {}
        self._folder_containers = {}
        self._build_layout()

    # ── Construction ──────────────────────────────────────────────────

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header widget
        self.header_widget = self._build_header()
        layout.addWidget(self.header_widget)

        # Content widget
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(12, 10, 12, 12)
        content_layout.setSpacing(10)

        self.search_container = self._build_search()
        content_layout.addWidget(self.search_container)

        self.session_tree = self._build_session_tree()
        content_layout.addWidget(self.session_tree)

        # Add dynamic vertical spacer that is only visible when collapsed
        self.spacer_widget = QWidget()
        self.spacer_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.spacer_widget.setVisible(False)
        content_layout.addWidget(self.spacer_widget)

        layout.addWidget(self.content_widget)

    def _build_header(self) -> QFrame:
        header = QFrame()
        header.setObjectName("sidebarHeader")
        header.setStyleSheet("""
            QFrame#sidebarHeader {
                background: transparent;
                border-bottom: 1px solid #EAD8DD;
            }
        """)
        
        row = QHBoxLayout(header)
        row.setContentsMargins(10, 12, 10, 12)
        row.setSpacing(6)

        self.collapse_btn = QPushButton()
        self.collapse_btn.setFixedSize(36, 30)
        self.collapse_btn.setToolTip("Collapse")
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0;
            }
            QPushButton:hover {
                background-color: rgba(255, 111, 163, 0.08);
                border-radius: 6px;
            }
            QPushButton:pressed {
                background-color: rgba(255, 111, 163, 0.15);
                border-radius: 6px;
            }
        """)
        import os
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "collapse_icon.png")
        if os.path.exists(icon_path):
            self.collapse_btn.setIcon(QIcon(icon_path))
            self.collapse_btn.setIconSize(QSize(20, 20))
        self.collapse_btn.clicked.connect(self._on_toggle_clicked)
        row.addWidget(self.collapse_btn)

        self.title_label = QLabel("PAST SESSIONS")
        self.title_label.setStyleSheet("""
            font-size: 13px;
            font-weight: 700;
            color: #0F7A75;
            letter-spacing: 1.2px;
            background: transparent;
        """)
        row.addWidget(self.title_label)

        # Create Folder button
        self.new_folder_btn = QPushButton()
        self.new_folder_btn.setToolTip("Create new folder")
        self.new_folder_btn.setFixedSize(32, 30)
        self.new_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #EAD8DD;
                border-radius: 6px;
                padding: 0;
            }
            QPushButton:hover {
                border-color: #0F7A75;
                background-color: #E6F4F2;
            }
            QPushButton:pressed {
                background-color: #CCFBF1;
            }
        """)
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "Icons", "Adds Add folder.png")
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
                background-color: #FFFFFF;
                border: 1px solid #EAD8DD;
                border-radius: 6px;
                color: #FF6FA3;
                font-size: 14px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                border-color: #FF6FA3;
                background-color: #FF6FA3;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #E63C78;
                border-color: #E63C78;
            }
        """)
        self.new_btn.clicked.connect(self.new_session_requested.emit)
        row.addWidget(self.new_btn)

        return header

    def _build_search(self) -> QWidget:
        # Search input wrapped in relative container with magnifier overlay icon
        search_container = QWidget()
        search_container.setStyleSheet("background: transparent;")
        search_container_layout = QHBoxLayout(search_container)
        search_container_layout.setContentsMargins(0, 0, 0, 0)
        search_container_layout.setSpacing(0)

        # Overlay magnifier label — absolutely positioned
        self._search_icon_label = QLabel("🔍", search_container)
        self._search_icon_label.setStyleSheet(
            "font-size: 15px; color: #9CA3AF; background: transparent;"
        )
        self._search_icon_label.setFixedSize(28, 32)
        self._search_icon_label.setAlignment(Qt.AlignCenter)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search past sessions...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #FAFAFA;
                border: 1.5px solid #EAD8DD;
                border-radius: 16px;
                padding: 6px 10px 6px 28px;
                font-size: 13px;
                color: #111827;
            }
            QLineEdit:focus {
                border-color: #FF6FA3;
                background-color: #FFFFFF;
            }
        """)
        self.search_input.setFixedHeight(32)
        search_container_layout.addWidget(self.search_input)
        
        # Install event filter to position icon
        self.search_input.installEventFilter(self)
        
        return search_container

    def eventFilter(self, obj, event) -> bool:
        from PySide6.QtCore import QEvent
        if hasattr(self, "search_input") and obj is self.search_input and event.type() in (QEvent.Resize, QEvent.Show):
            h = self.search_input.height()
            icon_h = self._search_icon_label.height()
            self._search_icon_label.move(0, max(0, (h - icon_h) // 2))
            self._search_icon_label.raise_()
        return super().eventFilter(obj, event)

    def _build_session_tree(self) -> QTreeWidget:
        self.session_tree = SessionTreeWidget()
        self.session_tree.setStyleSheet("""
            QTreeWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QTreeWidget::item {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                margin-bottom: 2px;
                padding: 0px 4px;
            }
            QTreeWidget::item:selected {
                background-color: transparent;
            }
        """)
        self.session_tree.session_moved.connect(self.session_moved.emit)
        self.session_tree.itemClicked.connect(self._on_item_clicked)
        self.session_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.session_tree.currentItemChanged.connect(self._on_current_item_changed)
        # Connect expand/collapse signals to keep custom folder plus/minus toggles in sync
        self.session_tree.itemExpanded.connect(self._update_all_folder_toggles)
        self.session_tree.itemCollapsed.connect(self._update_all_folder_toggles)
        return self.session_tree

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
        self._folder_containers = {}
        
        q = self.search_text

        # Create folder tree items
        folder_items = {}
        for f in folders:
            folder_item = QTreeWidgetItem(self.session_tree)
            folder_item.setData(0, Qt.UserRole, {"type": "folder", "id": f["id"]})
            # Folders cannot be dragged, accept drops, or be selected
            folder_item.setFlags(folder_item.flags() & ~Qt.ItemIsDragEnabled & ~Qt.ItemIsDropEnabled & ~Qt.ItemIsSelectable)
            folder_items[f["id"]] = folder_item

            # Build custom row widget
            row_widget = FolderRowWidget(
                item=folder_item,
                folder_name=f["name"],
                folder_id=f["id"],
                kebab_callback=self._show_folder_kebab_menu
            )
            self.session_tree.setItemWidget(folder_item, 0, row_widget)
            folder_item.setSizeHint(0, QSize(100, 48))
            self._folder_widgets[f["id"]] = row_widget
            
            # Create a single container item for this folder's sessions
            container_item = QTreeWidgetItem(folder_item)
            container_item.setData(0, Qt.UserRole, {"type": "session_container", "folder_id": f["id"]})
            container_item.setFlags(container_item.flags() & ~Qt.ItemIsDragEnabled & ~Qt.ItemIsDropEnabled & ~Qt.ItemIsSelectable)
            
            container_widget = SessionContainerWidget(parent_item=container_item)
            container_widget.session_selected.connect(self._on_container_session_selected)
            self.session_tree.setItemWidget(container_item, 0, container_widget)
            self._folder_containers[f["id"]] = container_widget

        # Track if folders contain visible items
        folder_has_visible_children = {fid: False for fid in folder_items}
        
        # We need to track the first nested item per folder to handle border-top divider styling
        folder_nested_sessions_added = {fid: 0 for fid in folder_items}

        # Populate sessions
        for s in sessions:
            title = s["title"]
            fid = s["folder_id"]
            
            if fid is not None and fid in folder_items:
                container_widget = self._folder_containers[fid]
                is_first = (folder_nested_sessions_added[fid] == 0)
                container_widget.add_session(s, self._show_session_kebab_menu, is_first)
                folder_nested_sessions_added[fid] += 1
                
                if not q or q in title.lower():
                    folder_has_visible_children[fid] = True
            else:
                # Ungrouped session
                if q and q not in title.lower():
                    continue
                    
                date_str = datetime.fromisoformat(s["created_at"]).strftime("%Y-%m-%d %H:%M")
                duration = s["duration_sec"]
                session_id = s["id"]
                
                session_item = QTreeWidgetItem(self.session_tree)
                session_item.setData(0, Qt.UserRole, {"type": "session", "id": session_id})
                session_item.setFlags(session_item.flags() & ~Qt.ItemIsDragEnabled & ~Qt.ItemIsDropEnabled)
                
                row_widget = SessionRowWidget(
                    item=session_item,
                    title=title,
                    date_str=date_str,
                    duration_sec=duration,
                    session_id=session_id,
                    kebab_callback=self._show_session_kebab_menu,
                    is_nested=False
                )
                self.session_tree.setItemWidget(session_item, 0, row_widget)
                session_item.setSizeHint(0, QSize(100, 54))

        # Hide folders that have no visible children during search, unless folder name matches
        for fid, item in folder_items.items():
            folder_name = next((f["name"] for f in folders if f["id"] == fid), "").lower()
            name_matches = q and q in folder_name
            container_widget = self._folder_containers[fid]
            
            visible_count = container_widget.filter_sessions(q)
            container_item = item.child(0)
            
            if q and not name_matches and not folder_has_visible_children[fid]:
                item.setHidden(True)
            else:
                item.setHidden(False)
                if len(container_widget.session_widgets) == 0:
                    container_item.setHidden(True)
                    container_item.setSizeHint(0, QSize(100, 0))
                else:
                    container_item.setHidden(False)
                    h = container_widget.calculate_total_height()
                    container_item.setSizeHint(0, QSize(100, h))
                
                if q:
                    item.setExpanded(True)
                    if fid in self._folder_widgets:
                        self._folder_widgets[fid].update_toggle_icon(animate=False)
                elif fid in expanded_folders:
                    item.setExpanded(True)
                    if fid in self._folder_widgets:
                        self._folder_widgets[fid].update_toggle_icon(animate=False)
                else:
                    item.setExpanded(False)
                    if fid in self._folder_widgets:
                        self._folder_widgets[fid].update_toggle_icon(animate=False)

    def select_by_id(self, session_id: Optional[int]) -> None:
        """Highlight the tree entry matching the given session ID."""
        if session_id is None:
            self.session_tree.setCurrentItem(None)
            for container in self._folder_containers.values():
                container.clear_selection()
            return
            
        # Find if it is in a folder container first
        for container in self._folder_containers.values():
            if session_id in container.session_widgets:
                self.session_tree.setCurrentItem(None)
                for c in self._folder_containers.values():
                    if c is not container:
                        c.clear_selection()
                container.select_session(session_id)
                return
                
        # Otherwise, search in ungrouped tree items
        root = self.session_tree.invisibleRootItem()
        item = self._find_session_item(root, session_id)
        if item:
            for container in self._folder_containers.values():
                container.clear_selection()
            self.session_tree.setCurrentItem(item)

    def current_session_id(self) -> Optional[int]:
        """Return the session_id of the selected list item, or None."""
        for container in self._folder_containers.values():
            for sid, widget in container.session_widgets.items():
                if widget.property("selected") == True:
                    return sid
                    
        item = self.session_tree.currentItem()
        if item:
            data = item.data(0, Qt.UserRole)
            if data and data.get("type") == "session":
                return data["id"]
        return None

    def expand(self) -> None:
        """Restore sidebar to its full expanded width."""
        self._collapsed = False
        self.spacer_widget.setVisible(False)
        self.collapse_btn.setToolTip("Collapse")
        
        # Immediately show widgets
        for w in (self.title_label, self.new_folder_btn, self.new_btn, self.search_container, self.session_tree):
            w.setVisible(True)
            
        # Fix inner widths during animation
        self.header_widget.setMinimumWidth(self.EXPANDED_WIDTH)
        self.content_widget.setMinimumWidth(self.EXPANDED_WIDTH)
        
        if hasattr(self, "_width_anim") and self._width_anim.state() == QVariantAnimation.Running:
            self._width_anim.stop()
            
        self._width_anim = QVariantAnimation(self)
        self._width_anim.setDuration(200)
        self._width_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._width_anim.setStartValue(self.width())
        self._width_anim.setEndValue(self.EXPANDED_WIDTH)
        
        def update_width(val):
            self.setFixedWidth(val)
            
        def on_finished():
            self.header_widget.setMinimumWidth(0)
            self.content_widget.setMinimumWidth(0)
            self.setFixedWidth(self.EXPANDED_WIDTH)
            
        self._width_anim.valueChanged.connect(update_width)
        self._width_anim.finished.connect(on_finished)
        self._width_anim.start()

    def collapse(self) -> None:
        """Shrink sidebar to an icon-only rail showing only the expand button."""
        self._collapsed = True
        self.collapse_btn.setToolTip("Expand")
        
        # Fix inner widths during animation
        self.header_widget.setMinimumWidth(self.EXPANDED_WIDTH)
        self.content_widget.setMinimumWidth(self.EXPANDED_WIDTH)
        
        if hasattr(self, "_width_anim") and self._width_anim.state() == QVariantAnimation.Running:
            self._width_anim.stop()
            
        self._width_anim = QVariantAnimation(self)
        self._width_anim.setDuration(200)
        self._width_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._width_anim.setStartValue(self.width())
        self._width_anim.setEndValue(self.COLLAPSED_WIDTH)
        
        def update_width(val):
            self.setFixedWidth(val)
            
        def on_finished():
            # Hide widgets at the end
            for w in (self.title_label, self.new_folder_btn, self.new_btn, self.search_container, self.session_tree):
                w.setVisible(False)
            self.header_widget.setMinimumWidth(0)
            self.content_widget.setMinimumWidth(0)
            self.spacer_widget.setVisible(True)
            self.setFixedWidth(self.COLLAPSED_WIDTH)
            
        self._width_anim.valueChanged.connect(update_width)
        self._width_anim.finished.connect(on_finished)
        self._width_anim.start()

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

    def _update_all_folder_toggles(self, item: Optional[QTreeWidgetItem] = None) -> None:
        """Helper to sync the chevron of custom folder row toggles on expansion events."""
        if item is not None:
            data = item.data(0, Qt.UserRole)
            if data and data.get("type") == "folder":
                fid = data["id"]
                if fid in self._folder_widgets:
                    self._folder_widgets[fid].update_toggle_icon(animate=False)
        else:
            for fid, widget in self._folder_widgets.items():
                widget.update_toggle_icon(animate=False)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Slot connected to itemDoubleClicked to handle smooth folder expand/collapse animations."""
        data = item.data(0, Qt.UserRole)
        if data and data.get("type") == "folder":
            widget = self.session_tree.itemWidget(item, 0)
            if isinstance(widget, FolderRowWidget):
                widget.toggle_expand()

    def _on_container_session_selected(self, session_id: int) -> None:
        """Coordinate container-level selection to clear other selections."""
        for container in self._folder_containers.values():
            if session_id not in container.session_widgets:
                container.clear_selection()
        self.session_tree.setCurrentItem(None)
        self.session_selected.emit(session_id)

    def _on_current_item_changed(self, current: Optional[QTreeWidgetItem], previous: Optional[QTreeWidgetItem]) -> None:
        """Clear container selections and update highlights on current item change."""
        if current:
            data = current.data(0, Qt.UserRole)
            if data and data.get("type") == "session":
                for container in self._folder_containers.values():
                    container.clear_selection()
            
        if previous:
            widget = self.session_tree.itemWidget(previous, 0)
            if isinstance(widget, SessionRowWidget):
                widget.set_selected(False)
        if current:
            widget = self.session_tree.itemWidget(current, 0)
            if isinstance(widget, SessionRowWidget):
                widget.set_selected(True)

    def _menu_stylesheet(self) -> str:
        return """
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #EAD8DD;
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
                background: #EAD8DD;
                margin: 4px 8px;
            }
        """

    def _show_folder_kebab_menu(self, button: QPushButton, folder_id: int, folder_name: str) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(self._menu_stylesheet())
        
        new_session_action = menu.addAction("➕  New Session")
        rename_action = menu.addAction("📝  Rename Folder")
        delete_action = menu.addAction("❌  Delete Folder")
        
        action = menu.exec(button.mapToGlobal(button.rect().bottomLeft()))
        if action == new_session_action:
            self.new_session_in_folder_requested.emit(folder_id)
        elif action == rename_action:
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
