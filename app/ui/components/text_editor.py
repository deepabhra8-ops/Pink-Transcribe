import os
import re
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QToolButton, QComboBox, QColorDialog, QFrame, QMessageBox,
    QGraphicsDropShadowEffect, QLineEdit, QLabel, QPushButton, QMenu, QScrollArea, QSizePolicy
)
from PySide6.QtGui import (
    QTextCursor, QFont, QColor, QTextListFormat, QTextCharFormat, QTextDocument, QIcon
)
from PySide6.QtCore import Qt, Signal, Slot, QUrl

class TranscriptionTextEdit(QTextEdit):
    """Customized QTextEdit for rendering and editing timestamped transcription text."""
    
    # Custom signals for interaction
    seek_requested = Signal(float)
    speaker_clicked = Signal(str)
    split_segment_requested = Signal(int, int)  # block_idx, char_idx
    timestamp_shortcut_pressed = Signal()
    speaker_shortcut_pressed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Transcribed text will appear here once recording starts...")
        
        # Style sheet for editor
        self.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: none;
                padding: 20px;
                color: #111827; /* strong text */
                font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
                font-size: 15px;
                line-height: 1.6;
            }
        """)
        
        self.show_timestamps = True
        self.segments: List[Dict[str, Any]] = []
        self.partial_text = ""
        self._is_programmatic = False
        
        # Filter variables
        self.search_query = ""
        self.filter_speaker = "All Speakers"
        self.filter_tag = "All Tags"
        self.review_mode = False
        
        # Connect vertical scroll bar for smart auto-scrolling
        self.textChanged.connect(self._smart_scroll)

    def set_filters(self, query: str, speaker: str, tag: str, review_mode: bool) -> None:
        """Applies query, speaker, tag, and review filters and re-renders."""
        self.search_query = query
        self.filter_speaker = speaker
        self.filter_tag = tag
        self.review_mode = review_mode
        self.render_transcript()

    def set_show_timestamps(self, enabled: bool) -> None:
        """Toggles timestamp visibility and re-renders the text."""
        self.show_timestamps = enabled
        self.render_transcript()

    def update_segments(self, segments: List[Dict[str, Any]]) -> None:
        """Updates the internal list of finalized segments and re-renders."""
        self.segments = segments
        self.render_transcript()

    def update_partial(self, text: str) -> None:
        """Updates the active rolling unfinalized text segment and re-renders."""
        self.partial_text = text
        self.render_transcript()

    def clear_editor(self) -> None:
        """Clears all text and segments."""
        self.segments = []
        self.partial_text = ""
        self._is_programmatic = True
        try:
            self.clear()
        finally:
            self._is_programmatic = False

    @staticmethod
    def format_time(seconds: float) -> str:
        """Helper to format float seconds to MM:SS or HH:MM:SS."""
        if seconds < 0:
            seconds = 0.0
        secs = int(seconds)
        hours = secs // 3600
        mins = (secs % 3600) // 60
        rem_secs = secs % 60
        if hours > 0:
            return f"{hours:02d}:{mins:02d}:{rem_secs:02d}"
        return f"{mins:02d}:{rem_secs:02d}"

    def render_transcript(self) -> None:
        """Re-draws all finalized segments and the current active partial transcript as HTML."""
        # Save scrollbar position
        scrollbar = self.verticalScrollBar()
        was_at_bottom = scrollbar.value() >= scrollbar.maximum() - 30
        
        html_parts = []
        
        # Render finalized segments
        for seg in self.segments:
            text = seg["text"].strip()
            if not text:
                continue
                
            raw_spk = seg.get("speaker", "Speaker 1")
            
            # 1. Apply Speaker Filter
            if self.filter_speaker != "All Speakers" and raw_spk != self.filter_speaker:
                continue
                
            # 2. Apply Tag Filter / Review Mode
            seg_tag = seg.get("tag", None)
            if self.review_mode:
                if not seg_tag:
                    continue
            elif self.filter_tag != "All Tags" and seg_tag != self.filter_tag:
                continue
                
            # 3. Apply Regex/Search Query
            if self.search_query:
                try:
                    if not re.search(self.search_query, text, re.IGNORECASE):
                        continue
                except re.error:
                    # Fallback to standard literal containment check
                    if self.search_query.lower() not in text.lower():
                        continue
            
            # Map speaker to colors matching visual brief
            if raw_spk == "Speaker 1":
                spk_color = "#FF6FA3"
                spk_bg = "#FFE4E6"
            elif raw_spk == "Speaker 2":
                spk_color = "#0F7A75"
                spk_bg = "#CCFBF1"
            elif raw_spk == "Speaker 3":
                spk_color = "#0284C7"
                spk_bg = "#E0F2FE"
            else:
                spk_color = "#7C3AED"
                spk_bg = "#F3E8FF"

            start_time = seg.get("start_time", 0.0)
            t_str = self.format_time(start_time)
            
            # Optional timestamp display
            ts_html = ""
            if self.show_timestamps:
                ts_html = (
                    f'<span style="font-family: monospace; font-size: 13px; font-weight: bold; margin-right: 12px;">'
                    f'  <a href="seek://{start_time}" style="color: #6B7280; text-decoration: none;">{t_str}</a>'
                    f'</span>'
                )

            # Optional tag badge display
            tag_badge = ""
            if seg_tag:
                tag_badge = f' <span style="background-color: #FEF3C7; color: #D97706; font-size: 11px; padding: 1px 4px; border-radius: 4px; font-weight: bold;">{seg_tag}</span>'

            line = (
                f'<div style="margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #E5E7EB;">'
                f'  {ts_html}'
                f'  <span style="background-color: {spk_bg}; color: {spk_color}; font-size: 11px; font-weight: 600; '
                f'    padding: 2px 8px; border-radius: 12px; margin-right: 8px;">'
                f'    <a href="speaker://{raw_spk}" style="color: {spk_color}; text-decoration: none;">{raw_spk}</a>'
                f'  </span>'
                f'  {tag_badge}'
                f'  <div style="margin-top: 6px; color: #111827; font-size: 15px;">{text}</div>'
                f'</div>'
            )
            html_parts.append(line)

        # Render active partial text
        if self.partial_text.strip():
            p_text = self.partial_text.strip()
            offset = self.segments[-1]["end_time"] if self.segments else 0.0
            t_str = self.format_time(offset)
            
            ts_html = ""
            if self.show_timestamps:
                ts_html = (
                    f'<span style="font-family: monospace; font-size: 13px; font-style: italic; color: #9CA3AF; margin-right: 12px;">'
                    f'  {t_str}'
                    f'</span>'
                )

            partial_line = (
                f'<div style="margin-bottom: 16px; padding-bottom: 12px;">'
                f'  {ts_html}'
                f'  <span style="background-color: #F3F4F6; color: #9CA3AF; font-size: 11px; font-weight: 600; '
                f'    padding: 2px 8px; border-radius: 12px; margin-right: 8px;">'
                f'    Speaker ?'
                f'  </span>'
                f'  <div style="margin-top: 6px; color: #9CA3AF; font-style: italic; font-size: 15px;">{p_text}...</div>'
                f'</div>'
            )
            html_parts.append(partial_line)

        # Assemble and set HTML
        joined_html = "\n".join(html_parts)
        
        self._is_programmatic = True
        try:
            self.setHtml(joined_html)
        finally:
            self._is_programmatic = False
        
        # Restore scrollbar position if user was at the bottom
        if was_at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def _smart_scroll(self) -> None:
        pass

    def mouseReleaseEvent(self, event) -> None:
        """Override to intercept clicked links inside the QTextEdit layout."""
        anchor = self.anchorAt(event.pos())
        if anchor:
            self._on_anchor_clicked(QUrl(anchor))
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _on_anchor_clicked(self, url: QUrl) -> None:
        """Catches anchor clicks to support seeking and speaker renames."""
        scheme = url.scheme()
        path = url.path() if url.path() else url.host()
        if scheme == "seek":
            try:
                seconds = float(path)
                self.seek_requested.emit(seconds)
            except ValueError:
                pass
        elif scheme == "speaker":
            self.speaker_clicked.emit(path)

    def keyPressEvent(self, event) -> None:
        """Captures core keystrokes: Enter (split), Ctrl+K (timestamp), Ctrl+M (speaker)."""
        # Ctrl+K -> Insert timestamp
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_K:
            self.timestamp_shortcut_pressed.emit()
            event.accept()
            return
            
        # Ctrl+M -> Mark speaker
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_M:
            self.speaker_shortcut_pressed.emit()
            event.accept()
            return
            
        # Enter -> Split segment
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not event.modifiers() == Qt.ShiftModifier:
            cursor = self.textCursor()
            block_idx = cursor.blockNumber()
            char_idx = cursor.positionInBlock()
            
            # Only trigger segment split if we have valid segments and block number matches
            if 0 <= block_idx < len(self.segments):
                self.split_segment_requested.emit(block_idx, char_idx)
                event.accept()
                return
                
        super().keyPressEvent(event)


class TranscriptionEditor(QWidget):
    """Outer wrapper class presenting a rich text editor toolbar, search/filters, and workspace."""
    
    # Custom signals
    text_changed = Signal()
    tag_applied = Signal(str, str)  # tag category, text
    seek_requested = Signal(float)
    speaker_clicked = Signal(str)
    split_segment_requested = Signal(int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Build core layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        container = QFrame()
        container.setObjectName("editorContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 1. Build Formatter Toolbar
        self.toolbar_widget = QWidget()
        self.toolbar_widget.setStyleSheet("""
            QWidget {
                background-color: #F9FAFB;
                border-bottom: 1px solid #E5E7EB;
                padding: 4px 8px;
            }
            QToolButton {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                color: #111827;
                padding: 4px 8px;
                font-weight: 500;
                font-size: 12px;
                margin: 2px;
            }
            QToolButton:hover {
                background-color: #F3F4F6;
                border-color: #9CA3AF;
            }
            QToolButton:checked {
                background-color: #FFE4E6;
                border-color: #FF6FA3;
                color: #FF6FA3;
            }
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                color: #111827;
                padding: 2px 6px;
                font-size: 12px;
                min-height: 24px;
                min-width: 85px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                selection-background-color: #FFE4E6;
                selection-color: #FF6FA3;
                color: #111827;
                outline: none;
            }
        """)
        
        toolbar_layout = QHBoxLayout(self.toolbar_widget)
        toolbar_layout.setContentsMargins(4, 2, 4, 2)
        toolbar_layout.setSpacing(4)
        
        # Undo/Redo
        self.undo_btn = QToolButton()
        self.undo_btn.setText("↶")
        self.undo_btn.setToolTip("Undo (Ctrl+Z)")
        self.undo_btn.clicked.connect(self._undo)
        
        self.redo_btn = QToolButton()
        self.redo_btn.setText("↷")
        self.redo_btn.setToolTip("Redo (Ctrl+Y)")
        self.redo_btn.clicked.connect(self._redo)
        
        toolbar_layout.addWidget(self.undo_btn)
        toolbar_layout.addWidget(self.redo_btn)
        toolbar_layout.addWidget(self._create_separator())
        
        # Formatting Style
        self.bold_btn = QToolButton()
        self.bold_btn.setText("B")
        self.bold_btn.setCheckable(True)
        self.bold_btn.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.bold_btn.setToolTip("Bold (Ctrl+B)")
        self.bold_btn.clicked.connect(self._toggle_bold)
        
        self.italic_btn = QToolButton()
        self.italic_btn.setText("I")
        self.italic_btn.setCheckable(True)
        self.italic_btn.setFont(QFont("Segoe UI", 9, QFont.Normal, True))
        self.italic_btn.setToolTip("Italic (Ctrl+I)")
        self.italic_btn.clicked.connect(self._toggle_italic)
        
        self.underline_btn = QToolButton()
        self.underline_btn.setText("U")
        self.underline_btn.setCheckable(True)
        u_font = QFont("Segoe UI", 9)
        u_font.setUnderline(True)
        self.underline_btn.setFont(u_font)
        self.underline_btn.setToolTip("Underline (Ctrl+U)")
        self.underline_btn.clicked.connect(self._toggle_underline)
        
        toolbar_layout.addWidget(self.bold_btn)
        toolbar_layout.addWidget(self.italic_btn)
        toolbar_layout.addWidget(self.underline_btn)
        toolbar_layout.addWidget(self._create_separator())
        
        # Formatting Tags Dropdown
        self.tag_btn = QToolButton()
        self.tag_btn.setText("🏷️ Tag Selection")
        self.tag_btn.setToolTip("Apply Tag Highlight to selected text")
        self.tag_btn.setMinimumWidth(150)

        tag_menu = QMenu(self)
        # QMenu popups do NOT inherit the parent widget stylesheet on Windows;
        # they must be styled explicitly to avoid falling back to the system dark theme.
        tag_menu.setStyleSheet("""
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
        """)

        act_item = tag_menu.addAction("✅  Action Item")
        act_item.triggered.connect(lambda: self._apply_tag("Action Item", "#D1FAE5", "#0F7A75"))
        act_quote = tag_menu.addAction("💬  Quote")
        act_quote.triggered.connect(lambda: self._apply_tag("Quote", "#F3E8FF", "#7C3AED"))
        act_sensitive = tag_menu.addAction("🔴  Sensitive")
        act_sensitive.triggered.connect(lambda: self._apply_tag("Sensitive", "#FEE2E2", "#E02424"))

        self.tag_btn.setMenu(tag_menu)
        self.tag_btn.setPopupMode(QToolButton.InstantPopup)
        toolbar_layout.addWidget(self.tag_btn)
        toolbar_layout.addWidget(self._create_separator())
        
        # Alignments
        self.align_left = QToolButton()
        self.align_left.setText("▤")
        self.align_left.setCheckable(True)
        self.align_left.clicked.connect(lambda: self._set_alignment(Qt.AlignLeft))
        self.align_center = QToolButton()
        self.align_center.setText("☲")
        self.align_center.setCheckable(True)
        self.align_center.clicked.connect(lambda: self._set_alignment(Qt.AlignHCenter))
        self.align_right = QToolButton()
        self.align_right.setText("▥")
        self.align_right.setCheckable(True)
        self.align_right.clicked.connect(lambda: self._set_alignment(Qt.AlignRight))
        self.align_justify = QToolButton()
        self.align_justify.setText("≣")
        self.align_justify.setCheckable(True)
        self.align_justify.clicked.connect(lambda: self._set_alignment(Qt.AlignJustify))
        
        toolbar_layout.addWidget(self.align_left)
        toolbar_layout.addWidget(self.align_center)
        toolbar_layout.addWidget(self.align_right)
        toolbar_layout.addWidget(self.align_justify)
        toolbar_layout.addWidget(self._create_separator())
        
        # Font Options
        self.font_combo = QComboBox()
        self.font_combo.addItems(["Segoe UI", "Inter", "Arial", "Consolas", "Georgia", "Impact"])
        self.font_combo.setMinimumWidth(130)
        self.font_combo.setToolTip("Font Family")
        self.font_combo.currentTextChanged.connect(self._change_font_family)
        
        self.size_combo = QComboBox()
        self.size_combo.addItems(["8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "28", "36", "48"])
        self.size_combo.setCurrentText("14")
        self.size_combo.setMinimumWidth(85)
        self.size_combo.setToolTip("Font Size")
        self.size_combo.currentTextChanged.connect(self._change_font_size)
        
        toolbar_layout.addWidget(self.font_combo)
        toolbar_layout.addWidget(self.size_combo)
        toolbar_layout.addWidget(self._create_separator())
        
        # Colors
        self.color_btn = QToolButton()
        self.color_btn.setText("🎨")
        self.color_btn.setToolTip("Color Picker")
        self.color_btn.clicked.connect(self._choose_color)
        toolbar_layout.addWidget(self.color_btn)
        
        toolbar_layout.addStretch()

        # Wrap the toolbar in a horizontal QScrollArea so narrow windows can scroll
        # rather than forcing a rigid minimum width that breaks resize.
        toolbar_scroll = QScrollArea()
        toolbar_scroll.setWidget(self.toolbar_widget)
        toolbar_scroll.setWidgetResizable(True)
        toolbar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        toolbar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        toolbar_scroll.setFixedHeight(48)
        toolbar_scroll.setFrameShape(QFrame.NoFrame)
        toolbar_scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:horizontal {
                height: 4px;
                background: #F9FAFB;
            }
            QScrollBar::handle:horizontal {
                background: #FFB3CA;
                border-radius: 2px;
                min-width: 20px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
        """)
        container_layout.addWidget(toolbar_scroll)
        
        # 2. Build Sticky Search and Filters Bar
        self.search_widget = QWidget()
        self.search_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E5E7EB;
                padding: 4px 12px;
            }
            QLineEdit {
                background-color: #F3F4F6;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 12px;
                color: #111827;
            }
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                color: #111827;
                padding: 2px 8px;
                font-size: 12px;
                min-width: 110px;
                min-height: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                selection-background-color: #FFE4E6;
                selection-color: #FF6FA3;
                color: #111827;
                outline: none;
            }
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #D1D5DB;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:checked {
                background-color: #FFE4E6;
                border-color: #FF6FA3;
                color: #FF6FA3;
            }
        """)
        
        search_layout = QHBoxLayout(self.search_widget)
        search_layout.setContentsMargins(4, 2, 4, 2)
        search_layout.setSpacing(6)
        
        # Search input (with regex notice)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search transcript... (regex support, e.g. /word1|word2/i)")
        self.search_input.textChanged.connect(self._apply_filters)
        search_layout.addWidget(self.search_input)
        
        # Speaker filter dropdown
        self.speaker_filter = QComboBox()
        self.speaker_filter.addItem("All Speakers")
        self.speaker_filter.addItem("Speaker 1")
        self.speaker_filter.addItem("Speaker 2")
        self.speaker_filter.addItem("Speaker 3")
        self.speaker_filter.addItem("Speaker 4")
        self.speaker_filter.setMinimumWidth(130)
        self.speaker_filter.setToolTip("Filter by Speaker")
        self.speaker_filter.currentTextChanged.connect(self._apply_filters)
        search_layout.addWidget(self.speaker_filter)
        
        # Tag filter dropdown
        self.tag_filter = QComboBox()
        self.tag_filter.addItem("All Tags")
        self.tag_filter.addItem("Action Item")
        self.tag_filter.addItem("Quote")
        self.tag_filter.addItem("Sensitive")
        self.tag_filter.setMinimumWidth(120)
        self.tag_filter.setToolTip("Filter by Tag")
        self.tag_filter.currentTextChanged.connect(self._apply_filters)
        search_layout.addWidget(self.tag_filter)
        
        # Review Mode toggle
        self.review_btn = QPushButton("Review Mode (Tags Only)")
        self.review_btn.setCheckable(True)
        self.review_btn.clicked.connect(self._apply_filters)
        search_layout.addWidget(self.review_btn)
        
        # Wrap the search bar in a horizontal QScrollArea too for the same reason.
        search_scroll = QScrollArea()
        search_scroll.setWidget(self.search_widget)
        search_scroll.setWidgetResizable(True)
        search_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        search_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        search_scroll.setFixedHeight(44)
        search_scroll.setFrameShape(QFrame.NoFrame)
        search_scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:horizontal {
                height: 4px;
                background: #FFFFFF;
            }
            QScrollBar::handle:horizontal {
                background: #FFB3CA;
                border-radius: 2px;
                min-width: 20px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
        """)
        container_layout.addWidget(search_scroll)
        
        # 3. Text Editor
        self.text_edit = TranscriptionTextEdit()
        container_layout.addWidget(self.text_edit)
        
        layout.addWidget(container)
        
        # Connect listeners to update toolbar states
        self.text_edit.cursorPositionChanged.connect(self._update_toolbar_states)
        self.text_edit.textChanged.connect(self._on_text_changed)
        
        # Forward signals
        self.text_edit.seek_requested.connect(self.seek_requested.emit)
        self.text_edit.speaker_clicked.connect(self.speaker_clicked.emit)
        self.text_edit.split_segment_requested.connect(self.split_segment_requested.emit)

    def _create_separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #E5E7EB; width: 1px; margin: 2px 4px;")
        return line

    def _apply_filters(self) -> None:
        """Gathers filter inputs and propagates to the custom text edit view."""
        self.text_edit.set_filters(
            query=self.search_input.text(),
            speaker=self.speaker_filter.currentText(),
            tag=self.tag_filter.currentText(),
            review_mode=self.review_btn.isChecked()
        )

    def _apply_tag(self, tag_name: str, bg_color: str, fg_color: str) -> None:
        """Applies tag highlight style to selected text block and emits annotation info."""
        cursor = self.text_edit.textCursor()
        if not cursor.hasSelection():
            return
            
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(bg_color))
        fmt.setForeground(QColor(fg_color))
        cursor.mergeCharFormat(fmt)
        
        # Tag the corresponding segment block
        block_idx = cursor.blockNumber()
        if 0 <= block_idx < len(self.text_edit.segments):
            self.text_edit.segments[block_idx]["tag"] = tag_name
            
        selected_text = cursor.selectedText()
        self.tag_applied.emit(tag_name, selected_text)

    # Forward core methods
    def set_show_timestamps(self, enabled: bool) -> None:
        self.text_edit.set_show_timestamps(enabled)

    def update_segments(self, segments: List[Dict[str, Any]]) -> None:
        self.text_edit.update_segments(segments)

    @Slot(str)
    def update_partial(self, text: str) -> None:
        self.text_edit.update_partial(text)

    def clear_editor(self) -> None:
        self.text_edit.clear_editor()

    def setReadOnly(self, read_only: bool) -> None:
        self.text_edit.setReadOnly(read_only)
        self.toolbar_widget.setEnabled(not read_only)
        self.search_widget.setEnabled(not read_only)

    def toHtml(self) -> str:
        return self.text_edit.toHtml()

    def toPlainText(self) -> str:
        return self.text_edit.toPlainText()

    def setHtml(self, html: str) -> None:
        self.text_edit._is_programmatic = True
        try:
            self.text_edit.setHtml(html)
        finally:
            self.text_edit._is_programmatic = False

    def _on_text_changed(self) -> None:
        if not self.text_edit._is_programmatic:
            self.text_changed.emit()

    # Toolbar operations
    def _toggle_bold(self) -> None:
        fmt = self.text_edit.currentCharFormat()
        weight = QFont.Bold if self.bold_btn.isChecked() else QFont.Normal
        fmt.setFontWeight(weight)
        self.text_edit.mergeCurrentCharFormat(fmt)

    def _toggle_italic(self) -> None:
        fmt = self.text_edit.currentCharFormat()
        fmt.setFontItalic(self.italic_btn.isChecked())
        self.text_edit.mergeCurrentCharFormat(fmt)

    def _toggle_underline(self) -> None:
        fmt = self.text_edit.currentCharFormat()
        fmt.setFontUnderline(self.underline_btn.isChecked())
        self.text_edit.mergeCurrentCharFormat(fmt)

    def _set_alignment(self, align: Qt.AlignmentFlag) -> None:
        self.text_edit.setAlignment(align)
        self.align_left.setChecked(align == Qt.AlignLeft)
        self.align_center.setChecked(align == Qt.AlignHCenter)
        self.align_right.setChecked(align == Qt.AlignRight)
        self.align_justify.setChecked(align == Qt.AlignJustify)

    def _change_font_family(self, font_name: str) -> None:
        if font_name:
            fmt = self.text_edit.currentCharFormat()
            fmt.setFontFamily(font_name)
            self.text_edit.mergeCurrentCharFormat(fmt)

    def _change_font_size(self, size_str: str) -> None:
        if size_str:
            try:
                size = float(size_str)
                fmt = self.text_edit.currentCharFormat()
                fmt.setFontPointSize(size)
                self.text_edit.mergeCurrentCharFormat(fmt)
            except ValueError:
                pass

    def _choose_color(self) -> None:
        color = QColorDialog.getColor(self.text_edit.textColor(), self, "Select Text Color")
        if color.isValid():
            fmt = self.text_edit.currentCharFormat()
            fmt.setForeground(color)
            self.text_edit.mergeCurrentCharFormat(fmt)

    def _undo(self) -> None:
        self.text_edit.undo()

    def _redo(self) -> None:
        self.text_edit.redo()

    def _update_toolbar_states(self) -> None:
        self.bold_btn.blockSignals(True)
        self.italic_btn.blockSignals(True)
        self.underline_btn.blockSignals(True)
        self.font_combo.blockSignals(True)
        self.size_combo.blockSignals(True)
        self.align_left.blockSignals(True)
        self.align_center.blockSignals(True)
        self.align_right.blockSignals(True)
        self.align_justify.blockSignals(True)
        
        try:
            fmt = self.text_edit.currentCharFormat()
            self.bold_btn.setChecked(fmt.fontWeight() == QFont.Bold)
            self.italic_btn.setChecked(fmt.fontItalic())
            self.underline_btn.setChecked(fmt.fontUnderline())
            
            font = fmt.font()
            family = font.family()
            if family:
                idx = self.font_combo.findText(family, Qt.MatchExactly)
                if idx != -1:
                    self.font_combo.setCurrentIndex(idx)
                
            size = font.pointSize()
            if size > 0:
                idx = self.size_combo.findText(str(size), Qt.MatchExactly)
                if idx != -1:
                    self.size_combo.setCurrentIndex(idx)
                    
            align = self.text_edit.alignment()
            self.align_left.setChecked(bool(align & Qt.AlignLeft))
            self.align_center.setChecked(bool(align & Qt.AlignHCenter))
            self.align_right.setChecked(bool(align & Qt.AlignRight))
            self.align_justify.setChecked(bool(align & Qt.AlignJustify))
            
        except Exception as e:
            print("Exception in _update_toolbar_states:", e)
        finally:
            self.bold_btn.blockSignals(False)
            self.italic_btn.blockSignals(False)
            self.underline_btn.blockSignals(False)
            self.font_combo.blockSignals(False)
            self.size_combo.blockSignals(False)
            self.align_left.blockSignals(False)
            self.align_center.blockSignals(False)
            self.align_right.blockSignals(False)
            self.align_justify.blockSignals(False)
