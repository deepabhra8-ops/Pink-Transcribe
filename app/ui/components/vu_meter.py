from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QBrush, QPen
from PySide6.QtCore import Qt, QTimer

class VUMeter(QWidget):
    """Custom painted cyberpunk-style VU meter for real-time audio level visualization."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.level = 0.0  # Dynamic volume level (0.0 to 1.0)
        self.peak = 0.0
        self.decay_rate = 0.05
        # Minimum size settings — allow narrow layouts to compress this widget
        self.setMinimumHeight(24)
        self.setMinimumWidth(50)
        
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # Timer for peak decay animation
        self.decay_timer = QTimer(self)
        self.decay_timer.timeout.connect(self._decay_level)
        self.decay_timer.start(30)  # ~33 FPS

    def set_level(self, level: float) -> None:
        """Sets the current input level and updates the peak."""
        # Level clipping
        level = max(0.0, min(1.0, level))
        self.level = level
        if level > self.peak:
            self.peak = level
        self.update()

    def _decay_level(self) -> None:
        """Decays the level and peak indicator for smooth visual fallback."""
        # Slowly decay the active level
        if self.level > 0.0:
            self.level = max(0.0, self.level - 0.08)
            
        # Decay the peak level
        if self.peak > 0.0:
            self.peak = max(0.0, self.peak - self.decay_rate)
            
        self.update()

    def paintEvent(self, event) -> None:
        """Draws the segmented VU meter with dynamic gradients."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        
        # Draw background container with subtle pink border
        painter.setPen(QPen(QColor("#ffe5ec"), 1))
        painter.setBrush(QBrush(QColor("#fff0f2")))
        painter.drawRoundedRect(0, 0, width - 1, height - 1, 4, 4)
        
        # Calculate sizing
        spacing = 3
        bar_width = 6.0
        num_bars = int((width - spacing) / (bar_width + spacing))
        if num_bars < 5:
            num_bars = 5
            
        bar_height = height - 8
        
        # Calculate start_x to center the visual bars inside the container width
        total_bars_width = num_bars * (bar_width + spacing) - spacing
        start_x = (width - total_bars_width) / 2.0
        
        # Define color scheme complementing the new pink/magenta icon
        # 0.0 - 0.5: Muted Soft Pink
        # 0.5 - 0.8: Fuchsia Pink
        # 0.8 - 1.0: Deep Magenta
        
        for i in range(num_bars):
            bar_ratio = i / num_bars
            x = start_x + i * (bar_width + spacing)
            y = 4
            
            # Determine color based on position
            if bar_ratio < 0.5:
                color = QColor("#ff85a1")  # Soft Pink
            elif bar_ratio < 0.8:
                color = QColor("#ff477e")  # Fuchsia
            else:
                color = QColor("#ff0055")  # Deep Magenta
                
            # Draw active vs inactive state
            is_active = bar_ratio <= self.level
            is_peak = abs(bar_ratio - self.peak) < (1.0 / num_bars)
            
            if is_active:
                # Active glowing bar
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.NoPen)
                painter.drawRect(x, y, bar_width, bar_height)
            elif is_peak and self.peak > 0.05:
                # Persistent peak indicator dot
                painter.setBrush(QBrush(color.lighter(115)))
                painter.setPen(Qt.NoPen)
                # Draw narrow peak bar
                painter.drawRect(x, y + bar_height - 2, bar_width, 2)
            else:
                # Inactive light pink slot
                painter.setBrush(QBrush(QColor("#ffccd5")))
                painter.setPen(Qt.NoPen)
                painter.drawRect(x, y, bar_width, bar_height)
                
        painter.end()
