import sys
import math
import random
from PySide6.QtCore import Qt, QPoint, Signal, QTimer, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QRadialGradient, QPainterPath
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QHBoxLayout, QSlider, QGridLayout,
    QSizePolicy, QScrollArea
)

# A character set for the "encrypted" part of the text
CHAR_SET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

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

# --- EXISTING WIDGETS ---

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

# --- NEW WIDGETS ---

class Slingshot(QWidget):
    volume_changed = Signal(int)
    
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(250, 250)
        self._is_dragging = False
        self._drag_pos = QPointF()
        self._slingshot_base = QPointF()
        
        # Projectile state
        self._is_firing = False
        self._projectile_pos = QPointF()
        self._projectile_vel = QPointF()
        self._projectile_timer = QTimer(self)
        self._projectile_timer.setInterval(16)
        self._projectile_timer.timeout.connect(self._update_projectile_physics)

    def _update_projectile_physics(self):
        if not self._is_firing: return

        GRAVITY = 0.1
        ENERGY_LOSS = -0.85

        self._projectile_vel.setY(self._projectile_vel.y() + GRAVITY)
        self._projectile_pos += self._projectile_vel

        w, h = self.width(), self.height()
        radius = 8
        if self._projectile_pos.x() < radius or self._projectile_pos.x() > w - radius:
            self._projectile_vel.setX(self._projectile_vel.x() * ENERGY_LOSS)
            self._projectile_pos.setX(max(radius, min(self._projectile_pos.x(), w - radius)))

        if self._projectile_pos.y() < radius or self._projectile_pos.y() > h - radius:
            self._projectile_vel.setY(self._projectile_vel.y() * ENERGY_LOSS)
            self._projectile_pos.setY(max(radius, min(self._projectile_pos.y(), h - radius)))

        if self._projectile_vel.manhattanLength() < 0.1 and self._projectile_pos.y() > h - 15:
            self._is_firing = False
            self._projectile_timer.stop()

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        self._slingshot_base = QPointF(w / 2, h * 0.8)
        
        # Draw slingshot frame
        pen = QPen(QColor("#8B4513"), 20) # Thicker frame
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(self._slingshot_base, self._slingshot_base - QPointF(0, 50))
        painter.drawLine(self._slingshot_base - QPointF(0, 50), self._slingshot_base - QPointF(30, 80))
        painter.drawLine(self._slingshot_base - QPointF(0, 50), self._slingshot_base + QPointF(30, -80))

        projectile_pen = QPen(Qt.GlobalColor.black, 2)
        projectile_brush = QBrush(Qt.GlobalColor.darkGray)

        if self._is_dragging:
            # Draw rubber band
            painter.setPen(QPen(Qt.GlobalColor.black, 3))
            painter.drawLine(self._slingshot_base - QPointF(30, 80), self._drag_pos)
            painter.drawLine(self._slingshot_base + QPointF(30, -80), self._drag_pos)
            # Draw projectile
            painter.setPen(projectile_pen)
            painter.setBrush(projectile_brush)
            painter.drawEllipse(self._drag_pos, 8, 8)
        
        if self._is_firing:
            painter.setPen(projectile_pen)
            painter.setBrush(projectile_brush)
            painter.drawEllipse(self._projectile_pos, 8, 8)

    def mousePressEvent(self, event):
        self._is_firing = False
        self._projectile_timer.stop()
        self._is_dragging = True
        self._drag_pos = event.position()
        self.update()

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            self._drag_pos = event.position()
            self.update()

    def mouseReleaseEvent(self, event):
        if not self._is_dragging: return
        self._is_dragging = False
        
        pullback_vector = self._slingshot_base - self._drag_pos
        distance = (pullback_vector.x()**2 + pullback_vector.y()**2)**0.5
        volume = int(min(100, (distance / 200.0) * 100))
        self.volume_changed.emit(volume)

        self._is_firing = True
        self._projectile_pos = QPointF(self._drag_pos)
        FIRE_STRENGTH = 0.15
        self._projectile_vel = pullback_vector * FIRE_STRENGTH
        self._projectile_timer.start()
        self.update()

class UnstableIsotope(QWidget):
    volume_changed = Signal(int)
    
    def __init__(self):
        super().__init__()
        self._true_value = 50.0
        layout = QVBoxLayout(self)
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(int(self._true_value))
        
        self._slider.valueChanged.connect(self.volume_changed.emit)
        self._slider.sliderMoved.connect(self._update_true_value)
        
        layout.addStretch()
        layout.addWidget(self._slider)
        layout.addStretch()
        
        self._decay_timer = QTimer(self)
        self._decay_timer.setInterval(50) # Faster timer for smoother decay
        self._decay_timer.timeout.connect(self._decay)
        self._decay_timer.start()

    def _update_true_value(self, value):
        """Syncs the float value when the user moves the slider."""
        self._true_value = float(value)
        
    def _decay(self):
        """Decays the float value and updates the integer slider."""
        if self._true_value > 0:
            # Decay rate is 0.25 per tick, which is 5 per second (0.25 * (1000/50))
            self._true_value -= 0.25
            if self._true_value < 0:
                self._true_value = 0
            
            # Only update the slider if the integer value has changed
            if self._slider.value() != int(self._true_value):
                self._slider.setValue(int(self._true_value))
            
class PerfectCircle(QWidget):
    volume_changed = Signal(int)

    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(250, 250)
        self._is_drawing = False
        self._points = []

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self._points: return
        
        path = QPainterPath()
        path.moveTo(self._points[0])
        for point in self._points[1:]:
            path.lineTo(point)
        painter.setPen(QPen(Qt.GlobalColor.black, 3))
        painter.drawPath(path)

    def mousePressEvent(self, event):
        self._is_drawing = True
        self._points = [event.position()]
        self.update()

    def mouseMoveEvent(self, event):
        if self._is_drawing:
            self._points.append(event.position())
            self.update()

    def mouseReleaseEvent(self, event):
        if not self._is_drawing or len(self._points) < 10:
            self._is_drawing = False
            return
        
        self._is_drawing = False
        # Analyze the circle
        center_x = sum(p.x() for p in self._points) / len(self._points)
        center_y = sum(p.y() for p in self._points) / len(self._points)
        center = QPointF(center_x, center_y)
        
        radii = [((p.x() - center.x())**2 + (p.y() - center.y())**2)**0.5 for p in self._points]
        avg_radius = sum(radii) / len(radii)
        if avg_radius == 0:
            self.volume_changed.emit(0)
            return

        # Calculate standard deviation of radii
        variance = sum([(r - avg_radius)**2 for r in radii]) / len(radii)
        std_dev = variance**0.5
        
        # Map deviation to volume (lower is better)
        perfection = 1.0 - (std_dev / avg_radius)
        volume = int(max(0, min(100, perfection * 150 - 50))) # Scale and shift
        self.volume_changed.emit(volume)
        
        # Reset for next drawing
        QTimer.singleShot(1000, self.clear_drawing)

    def clear_drawing(self):
        self._points = []
        self.update()

class BouncingBall(QWidget):
    volume_changed = Signal(int)
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._ball_pos = QPointF(self.width() / 2, 20)
        self._ball_vel = QPointF(0, 0)
        self._bounces = 0
        self._is_animating = False
        self._is_dragging = False
        self._mouse_history = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_physics)
        
    def mousePressEvent(self, event):
        self._timer.stop()
        self._is_animating = False
        self._is_dragging = True
        self._ball_vel = QPointF(0, 0)
        self._bounces = 0
        self.volume_changed.emit(0)
        self._ball_pos = event.position()
        self._mouse_history = [event.position()]
        self.update()
        
    def mouseMoveEvent(self, event):
        if self._is_dragging:
            self._ball_pos = event.position()
            self._mouse_history.append(event.position())
            if len(self._mouse_history) > 5:
                self._mouse_history.pop(0)
            self.update()

    def mouseReleaseEvent(self, event):
        if self._is_dragging:
            self._is_dragging = False
            self._is_animating = True
            
            # Fling mechanic
            if len(self._mouse_history) > 1:
                delta = self._mouse_history[-1] - self._mouse_history[0]
                self._ball_vel = delta * 0.2 # Adjust multiplier for desired fling strength
            else:
                self._ball_vel = QPointF(0,0)

            self._timer.start(16)

    def _update_physics(self):
        GRAVITY = 0.5
        ENERGY_LOSS = -0.8
        radius = 20
        
        self._ball_vel.setY(self._ball_vel.y() + GRAVITY)
        self._ball_pos += self._ball_vel
        
        w, h = self.width(), self.height()
        bounced = False

        if self._ball_pos.x() < radius or self._ball_pos.x() > w - radius:
            self._ball_vel.setX(self._ball_vel.x() * ENERGY_LOSS)
            self._ball_pos.setX(max(radius, min(self._ball_pos.x(), w - radius)))
            bounced = True

        if self._ball_pos.y() < radius:
            self._ball_vel.setY(self._ball_vel.y() * ENERGY_LOSS)
            self._ball_pos.setY(radius)
            bounced = True
        elif self._ball_pos.y() >= h - radius:
            self._ball_pos.setY(h - radius)
            self._ball_vel.setY(self._ball_vel.y() * ENERGY_LOSS)
            bounced = True

        if bounced and self._ball_vel.manhattanLength() > 1.5:
             self._bounces += 1
             self.volume_changed.emit(min(100, self._bounces))

        if self._ball_vel.manhattanLength() < 0.1 and self._ball_pos.y() >= h - radius -1:
            self._is_animating = False
            self._timer.stop()

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(Qt.GlobalColor.black, 4))
        painter.setBrush(Qt.GlobalColor.red)
        painter.drawEllipse(self._ball_pos, 20, 20)

class MemoryGame(QWidget):
    volume_changed = Signal(int)
    def __init__(self):
        super().__init__()
        self.setObjectName("MemoryGameWidget")
        self.grid = QGridLayout(self)
        self.symbols = ['A','A','B','B','C','C','D','D','E','E','F','F','G','G','H','H']
        self.buttons = []
        self.first_card = None
        self.second_card = None
        self.matched_pairs = 0
        self.setup_game()

    def setup_game(self):
        for i in reversed(range(self.grid.count())): 
            self.grid.itemAt(i).widget().setParent(None)

        random.shuffle(self.symbols)
        self.buttons = []
        self.first_card = None
        self.second_card = None
        self.matched_pairs = 0
        
        for i in range(16):
            button = QPushButton("?")
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            button.setProperty("symbol", self.symbols[i])
            button.setProperty("index", i)
            button.clicked.connect(self.card_clicked)
            self.grid.addWidget(button, i // 4, i % 4)
            self.buttons.append(button)

    def card_clicked(self):
        button = self.sender()
        if not button.isEnabled() or (self.first_card and self.second_card):
            return

        button.setText(button.property("symbol"))

        if not self.first_card:
            self.first_card = button
        elif button != self.first_card:
            self.second_card = button
            self.check_match()

    def check_match(self):
        if self.first_card.property("symbol") == self.second_card.property("symbol"):
            self.first_card.setEnabled(False)
            self.second_card.setEnabled(False)
            self.matched_pairs += 1
            volume = int((self.matched_pairs / 8.0) * 100)
            self.volume_changed.emit(volume)
            self.first_card = None
            self.second_card = None
        else:
            QTimer.singleShot(1000, self.reset_cards)

    def reset_cards(self):
        if self.first_card: self.first_card.setText("?")
        if self.second_card: self.second_card.setText("?")
        self.first_card = None
        self.second_card = None


# --- MAIN WINDOW ---

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

        # Instantiate all controls
        self.gravity_control = GravitySlider()
        self.color_control = ColorMatcher()
        self.slingshot_control = Slingshot()
        self.isotope_control = UnstableIsotope()
        self.circle_control = PerfectCircle()
        self.bounce_control = BouncingBall()
        self.memory_control = MemoryGame()
        
        # Setup pages for all controls
        self.gravity_page = self.setup_volume_page("Gravity Slider", "Drag to tilt the bar. The volume is set by the resting position of the ball.", self.gravity_control)
        self.color_page = self.setup_volume_page("Color Matcher", "Recreate the target color using the RGB sliders.", self.color_control)
        self.slingshot_page = self.setup_volume_page("Slingshot", "Pull back and release to set the volume.", self.slingshot_control)
        self.isotope_page = self.setup_volume_page("Unstable Isotope", "The volume constantly decays over time.", self.isotope_control)
        self.circle_page = self.setup_volume_page("Perfect Circle", "Draw a circle. Volume is based on its perfection.", self.circle_control)
        self.bounce_page = self.setup_volume_page("Bouncing Ball", "Click and drag to fling the ball. Volume is set by wall bounces.", self.bounce_control)
        self.memory_page = self.setup_volume_page("Memory Game", "Match all pairs. Volume increases with each match.", self.memory_control)
        
        # Add all pages to the stacked widget
        self.stacked_widget.addWidget(self.menu_page)
        for page in [self.gravity_page, self.color_page, self.slingshot_page, self.isotope_page, self.circle_page, self.bounce_page, self.memory_page]:
            self.stacked_widget.addWidget(page)
        
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

        # List of (Button Text, Page Index)
        buttons_to_create = [
            ("Gravity Slider", 1), ("Color Matcher", 2),
            ("Slingshot", 3), ("Unstable Isotope", 4),
            ("Perfect Circle", 5), ("Bouncing Ball", 6),
            ("Memory Game", 7)
        ]

        for i, (text, index) in enumerate(buttons_to_create):
            button = DecryptedLabel(text=text, speed=40)
            button.clicked.connect(lambda idx=index: self.stacked_widget.setCurrentIndex(idx))
            button.setObjectName("MenuButton")
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            
            button_grid.addWidget(button, i // 2, i % 2)
            self.labels_to_check.append(button)

        main_layout.addWidget(title, stretch=0)
        main_layout.addLayout(button_grid, stretch=1)
        
        scroll_area.setWidget(container_widget)
        scroll_area.verticalScrollBar().valueChanged.connect(self._check_visibility)
        self.labels_to_check.insert(0, title)

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
        if hasattr(control_widget, 'volume_changed'):
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
        #MemoryGameWidget QPushButton {
            border: 4px solid black;
            font-size: 24px;
            font-weight: bold;
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

