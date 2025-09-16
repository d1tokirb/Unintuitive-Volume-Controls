import sys
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QGridLayout,
    QSizePolicy, QScrollArea
)

# --- Import our custom widgets from the 'widgets' package ---
from widgets.decrypted_label import DecryptedLabel
from widgets.gravity_slider import GravitySlider
from widgets.color_matcher import ColorMatcher

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unintuitive Volume Controls")
        self.setGeometry(100, 100, 800, 600)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        self.labels_to_check = [] # List for scroll-triggered animations

        # Create Pages and Controls
        self.menu_page = QWidget()
        self.setup_menu_page() # Menu page is now a scroll area

        self.gravity_control = GravitySlider()
        self.color_control = ColorMatcher()
        
        self.gravity_page = self.setup_volume_page(
            "Gravity Slider", 
            "Drag to tilt the bar. The volume is set by the resting position of the ball.",
            self.gravity_control
        )
        self.color_page = self.setup_volume_page(
            "Color Matcher", 
            "Recreate the target color using the RGB sliders.",
            self.color_control
        )
        
        # Add pages to the stack
        self.stacked_widget.addWidget(self.menu_page)
        self.stacked_widget.addWidget(self.gravity_page)
        self.stacked_widget.addWidget(self.color_page)

        # Check visibility once on startup
        QTimer.singleShot(100, self._check_visibility)


    def setup_menu_page(self):
        """Sets up the scrollable main menu with animated labels."""
        # Create a scroll area and a container for its content
        scroll_area = QScrollArea(self.menu_page)
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("MenuScrollArea")
        
        container_widget = QWidget()
        main_layout = QVBoxLayout(container_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # The entire menu page is now a QVBoxLayout containing the scroll area
        page_layout = QVBoxLayout(self.menu_page)
        page_layout.setContentsMargins(0,0,0,0)
        page_layout.addWidget(scroll_area)

        # --- Add content to the container ---
        title = DecryptedLabel(text="Unintuitive Volume Controls", speed=30)
        title.setObjectName("MenuTitle")
        
        button_grid = QGridLayout()
        button_grid.setSpacing(20)

        # Replace QPushButtons with styled, clickable DecryptedLabels
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

        # Add 24 placeholder buttons
        for i in range(24):
            row_offset, col = divmod(i, 2)
            row = 1 + row_offset # Start from the second row

            placeholder = DecryptedLabel(text=f"Placeholder {i+1}", speed=60)
            placeholder.setObjectName("MenuButton")
            placeholder.setEnabled(False) # Make them non-interactive
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
        """Checks which labels are visible and triggers their animations."""
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
        """Generic setup for a page that hosts a volume control. Returns the configured page widget."""
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


# --- Run the App ---
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
        /* Style for the back button */
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
        /* Specific style for the large menu buttons (now labels) */
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

