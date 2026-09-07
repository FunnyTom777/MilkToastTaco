import sys
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QLineEdit, QTextEdit,
    QCheckBox, QRadioButton, QComboBox, QSpinBox, QSlider,
    QProgressBar, QTableWidget, QTableWidgetItem, QTreeWidget,
    QTreeWidgetItem, QCalendarWidget, QGroupBox, QFormLayout
)

class PyQt6Showcase(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQt6 Element Showcase")
        self.resize(800, 600)

        # Central Widget & Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Tab Widget container
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # Add showcasing tabs
        tabs.addTab(self.create_inputs_tab(), "Buttons & Inputs")
        tabs.addTab(self.create_data_views_tab(), "Data & Trees")
        tabs.addTab(self.create_pickers_tab(), "Pickers & Views")

    def create_inputs_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)

        # Left Column: Buttons & Toggles
        group1 = QGroupBox("Buttons & Checkables")
        vbox1 = QVBoxLayout()
        
        btn = QPushButton("Standard Push Button")
        toggle_btn = QPushButton("Toggle Button")
        toggle_btn.setCheckable(True)
        
        checkbox = QCheckBox("Checkbox Option")
        checkbox.setChecked(True)

        radio1 = QRadioButton("Radio Option A")
        radio2 = QRadioButton("Radio Option B")
        radio1.setChecked(True)

        vbox1.addWidget(btn)
        vbox1.addWidget(toggle_btn)
        vbox1.addWidget(checkbox)
        vbox1.addWidget(radio1)
        vbox1.addWidget(radio2)
        vbox1.addStretch()
        group1.setLayout(vbox1)

        # Right Column: Form Inputs & Adjusters
        group2 = QGroupBox("Form & Value Inputs")
        form_layout = QFormLayout()

        line_edit = QLineEdit()
        line_edit.setPlaceholderText("Enter text...")

        combo_box = QComboBox()
        combo_box.addItems(["Option 1", "Option 2", "Option 3"])

        spin_box = QSpinBox()
        spin_box.setRange(0, 100)
        spin_box.setValue(42)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(65)

        progress = QProgressBar()
        progress.setValue(65)
        # Link slider directly to progress bar using Qt signals
        slider.valueChanged.connect(progress.setValue)

        text_edit = QTextEdit()
        text_edit.setPlaceholderText("Multi-line text area...")
        text_edit.setMaximumHeight(80)

        form_layout.addRow("QLineEdit:", line_edit)
        form_layout.addRow("QComboBox:", combo_box)
        form_layout.addRow("QSpinBox:", spin_box)
        form_layout.addRow("QSlider:", slider)
        form_layout.addRow("QProgressBar:", progress)
        form_layout.addRow("QTextEdit:", text_edit)

        group2.setLayout(form_layout)

        layout.addWidget(group1)
        layout.addWidget(group2)
        return tab

    def create_data_views_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)

        # Table Widget
        table = QTableWidget(4, 2)
        table.setHorizontalHeaderLabels(["Name", "Role"])
        data = [("Alice", "Developer"), ("Bob", "Designer"), ("Charlie", "Manager"), ("Diana", "QA")]
        for row, (name, role) in enumerate(data):
            table.setItem(row, 0, QTableWidgetItem(name))
            table.setItem(row, 1, QTableWidgetItem(role))

        # Tree Widget
        tree = QTreeWidget()
        tree.setHeaderLabel("Project Structure")
        
        root = QTreeWidgetItem(tree, ["Root Directory"])
        sub_folder = QTreeWidgetItem(root, ["src"])
        QTreeWidgetItem(sub_folder, ["main.py"])
        QTreeWidgetItem(sub_folder, ["utils.py"])
        QTreeWidgetItem(root, ["README.md"])
        tree.expandAll()

        layout.addWidget(table)
        layout.addWidget(tree)
        return tab

    def create_pickers_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        label = QLabel("QCalendarWidget Example:")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        calendar = QCalendarWidget()
        calendar.setSelectedDate(QDate.currentDate())

        layout.addWidget(label)
        layout.addWidget(calendar)
        return tab

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PyQt6Showcase()
    window.show()
    sys.argv[0] if len(sys.argv) > 0 else None
    sys.exit(app.exec())