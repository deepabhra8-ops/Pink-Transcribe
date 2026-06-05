"""Sidebar Panel — collapsible left rail with session history, search, and actions.

Single Responsibility: owns all sidebar UI state and exposes clean signals + methods.
Coupling:             communicates outward only through signals; receives data via populate().
"""
from datetime import datetime
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QLineEdit,
)
from PySide6.QtCore import Signal, Qt


class SidebarPanel(QFrame):
    """Collapsible left sidebar showing past session history."""

    # ── Public signals (the only contract with the outside world) ─────
    new_session_requested   = Signal()
    session_selected        = Signal(int)   # session_id
    delete_selected_requested = Signal()
    delete_all_requested    = Signal()

    # ── Layout constants ──────────────────────────────────────────────
    EXPANDED_WIDTH  = 280
    COLLAPSED_WIDTH = 80   # 56 px button + 12 px margin × 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidePanel")
        self.setFixedWidth(self.EXPANDED_WIDTH)
        self._collapsed = False
        self._build_layout()

    # ── Construction ──────────────────────────────────────────────────

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addLayout(self._build_header())
        layout.addWidget(self._build_search())
        layout.addWidget(self._build_session_list())
        layout.addLayout(self._build_delete_row())

    def _build_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)

        self.collapse_btn = QPushButton("☰ ◀")
        self.collapse_btn.setFixedSize(56, 30)
        self.collapse_btn.setToolTip("Collapse Sidebar (hide session list)")
        self.collapse_btn.setStyleSheet(
            "QPushButton { font-size: 13px; letter-spacing: 1px; border-radius: 6px; }"
        )
        self.collapse_btn.clicked.connect(self._on_toggle_clicked)
        row.addWidget(self.collapse_btn)

        self.title_label = QLabel("PAST SESSIONS")
        self.title_label.setStyleSheet(
            "font-size: 11px; font-weight: bold; color: #6B7280; letter-spacing: 1.5px;"
        )
        row.addWidget(self.title_label)

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

    def _build_session_list(self) -> QListWidget:
        self.session_list = QListWidget()
        self.session_list.itemClicked.connect(
            lambda item: self.session_selected.emit(item.data(Qt.UserRole))
        )
        return self.session_list

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

    def populate(self, sessions: List[Dict[str, Any]]) -> None:
        """Rebuild the list from the provided session dicts, applying the current search filter."""
        self.session_list.clear()
        q = self.search_text
        for s in sessions:
            if q and q not in s["title"].lower():
                continue
            date_str = datetime.fromisoformat(s["created_at"]).strftime("%Y-%m-%d %H:%M")
            item = QListWidgetItem(f"{s['title']}\n{date_str} • {s['duration_sec']:.1f}s")
            item.setData(Qt.UserRole, s["id"])
            self.session_list.addItem(item)

    def select_by_id(self, session_id: Optional[int]) -> None:
        """Highlight the list entry matching the given session ID."""
        for i in range(self.session_list.count()):
            item = self.session_list.item(i)
            if item.data(Qt.UserRole) == session_id:
                self.session_list.setCurrentItem(item)
                return

    def current_session_id(self) -> Optional[int]:
        """Return the session_id of the selected list item, or None."""
        item = self.session_list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def expand(self) -> None:
        """Restore sidebar to its full expanded width."""
        self._collapsed = False
        self.setFixedWidth(self.EXPANDED_WIDTH)
        for w in (self.title_label, self.new_btn, self.search_input,
                  self.session_list, self.delete_btn, self.delete_all_btn):
            w.setVisible(True)
        self.collapse_btn.setText("☰ ◀")
        self.collapse_btn.setToolTip("Collapse Sidebar (hide session list)")

    def collapse(self) -> None:
        """Shrink sidebar to an icon-only rail showing only the expand button."""
        self._collapsed = True
        self.setFixedWidth(self.COLLAPSED_WIDTH)
        for w in (self.title_label, self.new_btn, self.search_input,
                  self.session_list, self.delete_btn, self.delete_all_btn):
            w.setVisible(False)
        self.collapse_btn.setText("☰ ▶")
        self.collapse_btn.setToolTip("Expand Sidebar (show session list)")

    # ── Internal ──────────────────────────────────────────────────────

    def _on_toggle_clicked(self) -> None:
        if self._collapsed:
            self.expand()
        else:
            self.collapse()
