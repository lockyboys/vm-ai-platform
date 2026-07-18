from PySide6.QtWidgets import QMainWindow, QLabel, QStatusBar
from PySide6.QtCore import Qt


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Story Programming Document Studio (SPDS)")
        self.resize(1200, 800)

        label = QLabel("Welcome to SPDS\n\nStory starts here...")
        label.setAlignment(Qt.AlignCenter)

        self.setCentralWidget(label)

        status_bar = QStatusBar()
        status_bar.showMessage("Ready to create a Story.")
        self.setStatusBar(status_bar)