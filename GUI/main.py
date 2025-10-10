import sys
from PyQt6.QtWidgets import QFileDialog, QMainWindow, QApplication
from PyQt6.QtGui import QImage, QPixmap
from start_page import Ui_MainWindow
import pathlib


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.button_load_video.clicked.connect(self.open_video_file)
        self.ui.link_video_edit.enterKeyPressed.connect(self.view_frame_to_config)
        self.ui.error_message.setVisible(False)

    def open_video_file(self):
        path = QFileDialog.getOpenFileName(
            self,
            "Выберите видео",
            str(pathlib.Path().cwd().parent),
            "Видео файлы (*.mp4 *.avi)",
        )[0]

        self.view_frame_to_config(path)

    def view_frame_to_config(self, path: str = None):
        if len(path) == 0:
            return
        if self.ui.page_edit_config.set_path(path):
            self.ui.stackedWidget.setCurrentIndex(1)
        else:
            self.ui.error_message.setVisible(True)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    wind = MainWindow()

    wind.show()
    sys.exit(app.exec())
