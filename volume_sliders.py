import sys
import math
import random
from PySide6.QtCore import Qt, QPoint, Signal, QTimer
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QRadialGradient
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QHBoxLayout, QSlider, QGridLayout,
    QSizePolicy, QScrollArea
)

# A character set for the "encrypted" part of the text
CHAR_SET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()"

class DecryptedLabel(QLabel):
    """
    A QLabel widget that animates text decryption and can act like a button.
    """
    clicked = Signal()

    def __init__(self, text="", speed=50, characters=CHAR_SET, parent=None):
        super().__init__(parent)
        self._original_text = text
        self._speed_ms = speed
        self._char_set = characters
        self._revealed_count = 0
        self._is_animating = False
        self.is_in_view = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_text)
        self.reset_scramble()

    def setOriginalText(self, text):
        self._original_text = text
        self.reset_scramble()
        
    def _scramble(self, text):
        return "".join(random.choice(self._char_set) for _ in text)

    def _update_text(self):
        if self._revealed_count >= len(self._original_text):
            self._timer.stop()
            self._is_animating = False
            self.setText(self._original_text)
            return
            
        self._revealed_count += 1
        revealed_part = self._original_text[:self._revealed_count]
        scrambled_part = "".join(random.choice(self._char_set) for _ in range(len(self._original_text) - self._revealed_count))
        self.setText(revealed_part + scrambled_part)

    def start_decryption(self):
        if not self._is_animating and self._original_text:
            self._is_animating = True
            self._revealed_count = 0
            self._timer.start(self._speed_ms)

    def reset_scramble(self):
        if self._is_animating:
            self._timer.stop()
            self._is_animating = False
        self.setText(self._scramble(self._original_text))

    def mousePressEvent(self, event):
        if self.isEnabled():
            self.clicked.emit()
        super().mousePressEvent(event)

def color_distance(c1, c2):
    (r1, g1, b1, _) = c1.getRgb()
    (r2, g2, b2, _) = c2.getRgb()
    return ( (r1 - r2)**2 + (g1 - g2)**2 + (b1 - b2)**2 )**0.5

class GravitySlider(QWidget):
    """A volume slider controlled by tilting it and letting 'gravity' set the value."""
    volume_changed = Signal(int)

    def __init__(self):
        super().__init__()
        self._angle = 0.0
        self._target_angle = 0.0
        self._ball_pos = 0.0
        self._ball_velocity = 0.0
        self._is_dragging = False

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(250, 250)
        
        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(16)
        self._animation_timer.timeout.connect(self._update_physics)
        self._animation_timer.start()

        QTimer.singleShot(0, lambda: self.volume_changed.emit(50))

    def _update_physics(self):
        SMOOTHING_FACTOR = 0.1
        delta_angle = self._target_angle - self._angle
        if delta_angle > math.pi: delta_angle -= 2 * math.pi
        if delta_angle < -math.pi: delta_angle += 2 * math.pi
        self._angle += delta_angle * SMOOTHING_FACTOR

        GRAVITY_CONSTANT = 0.007
        FRICTION = 0.985
        BOUNCE_ENERGY_LOSS = -0.4

        acceleration = GRAVITY_CONSTANT * math.sin(self._angle)
        self._ball_velocity += acceleration
        self._ball_velocity *= FRICTION
        self._ball_pos += self._ball_velocity
        
        if self._ball_pos > 1.0:
            self._ball_pos = 1.0
            self._ball_velocity *= BOUNCE_ENERGY_LOSS
        elif self._ball_pos < -1.0:
            self._ball_pos = -1.0
            self._ball_velocity *= BOUNCE_ENERGY_LOSS
        
        volume = int(50 * (1 - self._ball_pos))
        volume = max(0, min(100, volume)) 
        self.volume_changed.emit(volume)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        center = QPoint(w // 2, h // 2)
        radius = min(w, h) * 0.4
        
        p1 = QPoint(int(center.x() + radius * math.cos(self._angle)), int(center.y() + radius * math.sin(self._angle)))
        p2 = QPoint(int(center.x() - radius * math.cos(self._angle)), int(center.y() - radius * math.sin(self._angle)))

        track_pen = QPen(QColor("#BDBDBD"), 12)
        track_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track_pen)
        painter.drawLine(p1, p2)
        
        ball_x = center.x() + radius * math.cos(self._angle) * self._ball_pos
        ball_y = center.y() + radius * math.sin(self._angle) * self._ball_pos
        ball_center = QPoint(int(ball_x), int(ball_y))

        painter.setPen(Qt.PenStyle.NoPen)
        gradient = QRadialGradient(ball_center, 15, ball_center - QPoint(5, 5))
        gradient.setColorAt(0, QColor("#85C1E9"))
        gradient.setColorAt(1, QColor("#3498DB"))
        painter.setBrush(gradient)
        painter.drawEllipse(ball_center, 15, 15)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self.mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False

    def mouseMoveEvent(self, event):
        if not event.buttons() & Qt.MouseButton.LeftButton: return
        center = QPoint(self.width() // 2, self.height() // 2)
        delta = event.pos() - center
        if delta.manhattanLength() == 0: return
        self._target_angle = math.atan2(delta.y(), delta.x())

class ColorMatcher(QWidget):
    """A control where you must match a constantly shifting target color."""
    volume_changed = Signal(int)

    def __init__(self):
        super().__init__()
        self._target_color = QColor("black")
        self._current_color = QColor("#808080")
        self._max_dist = color_distance(QColor("black"), QColor("white"))

        self._target_label = QLabel("Chase This Color:")
        self._target_swatch = self._create_color_swatch(self._target_color)
        self._current_label = QLabel("Your Color:")
        self._current_swatch = self._create_color_swatch(self._current_color)
        self._r_slider = self._create_slider(128)
        self._g_slider = self._create_slider(128)
        self._b_slider = self._create_slider(128)
        
        main_layout = QVBoxLayout(self)
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        row1 = QHBoxLayout()
        row1.addWidget(self._target_label)
        row1.addWidget(self._target_swatch)
        row1.addWidget(self._current_label)
        row1.addWidget(self._current_swatch)
        controls_layout.addLayout(row1)
        controls_layout.addWidget(QLabel("Red"))
        controls_layout.addWidget(self._r_slider)
        controls_layout.addWidget(QLabel("Green"))
        controls_layout.addWidget(self._g_slider)
        controls_layout.addWidget(QLabel("Blue"))
        controls_layout.addWidget(self._b_slider)
        main_layout.addStretch()
        main_layout.addWidget(controls_widget)
        main_layout.addStretch()

        self.reset_challenge()
        QTimer.singleShot(0, self._update_volume)

        self._shift_timer = QTimer(self)
        self._shift_timer.setInterval(150)
        self._shift_timer.timeout.connect(self._shift_target_color)
        self._shift_timer.start()

    def _shift_target_color(self):
        r, g, b, a = self._target_color.getRgb()
        r = max(0, min(255, r + random.randint(-2, 2)))
        g = max(0, min(255, g + random.randint(-2, 2)))
        b = max(0, min(255, b + random.randint(-2, 2)))
        self._target_color.setRgb(r, g, b, a)
        self._target_swatch.setStyleSheet(f"background-color: {self._target_color.name()}; border: 1px solid #AAA; border-radius: 8px;")
        self._update_volume()

    def reset_challenge(self):
        self._target_color = QColor.fromRgb(random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))
        self._target_swatch.setStyleSheet(f"background-color: {self._target_color.name()}; border: 1px solid #AAA; border-radius: 8px;")
        for slider in [self._r_slider, self._g_slider, self._b_slider]:
            slider.blockSignals(True)
            slider.setValue(128)
            slider.blockSignals(False)
        self._update_color()

    def _create_slider(self, value):
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 255)
        slider.setValue(value)
        slider.valueChanged.connect(self._update_color)
        return slider

    def _create_color_swatch(self, color):
        swatch = QLabel()
        swatch.setMinimumSize(100, 50)
        swatch.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        swatch.setAutoFillBackground(True)
        swatch.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #AAA; border-radius: 8px;")
        return swatch

    def _update_color(self):
        self._current_color.setRgb(self._r_slider.value(), self._g_slider.value(), self._b_slider.value())
        self._current_swatch.setStyleSheet(f"background-color: {self._current_color.name()}; border: 1px solid #AAA; border-radius: 8px;")
        self._update_volume()

    def _update_volume(self):
        dist = color_distance(self._target_color, self._current_color)
        similarity = 1.0 - (dist / self._max_dist)
        volume = int(100 * similarity)
        volume = max(0, min(100, volume))
        self.volume_changed.emit(volume)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unintuitive Volume Controls")
        self.setGeometry(100, 100, 800, 600)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        self.labels_to_check = []

        self.menu_page = QWidget()
        self.setup_menu_page()

        self.gravity_control = GravitySlider()
        self.color_control = ColorMatcher()
        
        self.gravity_page = self.setup_volume_page("Gravity Slider", "Drag to tilt the bar. The volume is set by the resting position of the ball.", self.gravity_control)
        self.color_page = self.setup_volume_page("Color Matcher", "Recreate the target color using the RGB sliders.", self.color_control)
        
        self.stacked_widget.addWidget(self.menu_page)
        self.stacked_widget.addWidget(self.gravity_page)
        self.stacked_widget.addWidget(self.color_page)

        QTimer.singleShot(100, self._check_visibility)

    def setup_menu_page(self):
        scroll_area = QScrollArea(self.menu_page)
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("MenuScrollArea")
        
        container_widget = QWidget()
        main_layout = QVBoxLayout(container_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        page_layout = QVBoxLayout(self.menu_page)
        page_layout.setContentsMargins(0,0,0,0)
        page_layout.addWidget(scroll_area)

        title = DecryptedLabel(text="Unintuitive Volume Controls", speed=30)
        title.setObjectName("MenuTitle")
        
        button_grid = QGridLayout()
        button_grid.setSpacing(20)

        btn_gravity = DecryptedLabel(text="Gravity Slider", speed=40)
        btn_gravity.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        btn_gravity.setObjectName("MenuButton")
        btn_gravity.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        btn_color = DecryptedLabel(text="Color Matcher", speed=40)
        btn_color.clicked.connect(lambda: (self.color_control.reset_challenge(), self.stacked_widget.setCurrentIndex(2)))
        btn_color.setObjectName("MenuButton")
        btn_color.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        button_grid.addWidget(btn_gravity, 0, 0)
        button_grid.addWidget(btn_color, 0, 1)
        
        self.labels_to_check.extend([title, btn_gravity, btn_color])

        for i in range(24):
            row_offset, col = divmod(i, 2)
            row = 1 + row_offset
            placeholder = DecryptedLabel(text=f"Placeholder {i+1}", speed=60)
            placeholder.setObjectName("MenuButton")
            placeholder.setEnabled(False)
            placeholder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            button_grid.addWidget(placeholder, row, col)
            self.labels_to_check.append(placeholder)

        button_grid.setColumnStretch(0, 1)
        button_grid.setColumnStretch(1, 1)
        main_layout.addWidget(title, stretch=0)
        main_layout.addLayout(button_grid, stretch=1)
        
        scroll_area.setWidget(container_widget)
        scroll_area.verticalScrollBar().valueChanged.connect(self._check_visibility)

    def _check_visibility(self):
        scroll_area = self.menu_page.findChild(QScrollArea)
        if not scroll_area: return
        scroll_y = scroll_area.verticalScrollBar().value()
        viewport_height = scroll_area.viewport().height()
        visible_bottom = scroll_y + viewport_height

        for label in self.labels_to_check:
            label_top = label.y()
            label_center_y = label_top + (label.height() / 2)
            is_now_visible = (label_center_y >= scroll_y) and (label_center_y <= visible_bottom)
            if is_now_visible and not label.is_in_view:
                label.is_in_view = True
                label.start_decryption()
            elif not is_now_visible and label.is_in_view:
                label_bottom = label_top + label.height()
                if (label_bottom < scroll_y) or (label_top > visible_bottom):
                    label.is_in_view = False
                    label.reset_scramble()

    def setup_volume_page(self, title_text, instructions_text, control_widget):
        page_widget = QWidget()
        layout = QVBoxLayout(page_widget)
        layout.setContentsMargins(30, 20, 30, 20)
        
        title = QLabel(title_text)
        title.setObjectName("PageTitle")
        instructions = QLabel(instructions_text)
        instructions.setWordWrap(True)
        instructions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        volume_label = QLabel("Volume: --")
        volume_label.setObjectName("VolumeLabel")
        control_widget.volume_changed.connect(lambda v: volume_label.setText(f"Volume: {v}"))
        back_button = QPushButton("← Back to Menu")
        back_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))

        layout.addWidget(title, stretch=0)
        layout.addWidget(instructions, stretch=0)
        layout.addWidget(control_widget, stretch=1)
        layout.addWidget(volume_label, stretch=0)
        layout.addWidget(back_button, stretch=0)
        
        return page_widget

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Times New Roman", 12))
    
    app.setStyleSheet("""
        QMainWindow, QWidget {
            background-color: white;
            font-family: "Times New Roman";
        }
        QScrollArea#MenuScrollArea {
            border: none;
        }
        QLabel {
            color: black;
            font-size: 16px;
        }
        QLabel#MenuTitle {
            font-size: 30px;
            font-weight: bold;
            border-bottom: 4px solid black;
            padding-bottom: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        QLabel#PageTitle {
            font-size: 24px;
            font-weight: bold;
            text-align: center;
            margin-bottom: 10px;
        }
        QLabel#VolumeLabel {
            font-size: 32px;
            font-weight: bold;
            text-align: center;
            margin-top: 10px;
        }
        QPushButton {
            padding: 10px;
            background-color: #f0f0f0;
            color: black;
            border: 2px solid #cccccc;
            border-radius: 12px;
            min-height: 40px;
        }
        QPushButton:hover {
            background-color: #e0e0e0;
        }
        QLabel#MenuButton {
            background-color: white;
            color: black;
            border: 4px solid black;
            border-radius: 15px;
            font-weight: bold;
            font-size: 20px;
            text-align: left;
            padding: 15px;
            min-height: 120px;
        }
        QLabel#MenuButton:hover {
            background-color: #f9f9f9;
        }
        QLabel#MenuButton:disabled {
            background-color: #f8f8f8;
            color: #a0a0a0;
            border: 4px solid #e0e0e0;
        }
        QSlider::groove:horizontal {
            border: 1px solid #bbb;
            background: #e0e0e0;
            height: 10px;
            border-radius: 5px;
        }
        QSlider::handle:horizontal {
            background: #666;
            border: 1px solid #555;
            width: 20px;
            margin: -5px 0;
            border-radius: 10px;
        }
    """)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
