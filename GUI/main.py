import sys
from PyQt6.QtWidgets import QFileDialog, QMainWindow, QApplication
from PyQt6.QtGui import QImage, QPixmap
from start_page import Ui_MainWindow
from pathlib import Path


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        filename_last_path = Path("GUI/user_files/last_video_folder.txt")
        if not filename_last_path.parent.exists():
            Path(filename_last_path).parent.mkdir()
        if not filename_last_path.exists():
            self.last_folder = None
            filename_last_path.touch()
        else:
            with open(str(filename_last_path), "r") as file:
                self.last_folder = file.readline()

        self.ui.button_load_video.clicked.connect(self.open_video_file)
        self.ui.link_video_edit.enterKeyPressed.connect(self.view_frame_to_config)
        self.ui.error_message.setVisible(False)
        self.aspect_ratio = None

    def open_video_file(self):
        if self.last_folder is None:
            folder = Path().cwd()
        else:
            folder = self.last_folder

        path = QFileDialog.getOpenFileName(
            self,
            "Выберите видео",
            str(folder),
            "Видео файлы (*.mp4 *.avi)",
        )[0]

        self.view_frame_to_config(path)

    def view_frame_to_config(self, path: str = None):
        if len(path) == 0:
            return
        if self.ui.page_edit_config.set_path(path):
            self.last_folder = str(Path(path).parent)
            with open("GUI/user_files/last_video_folder.txt", "w") as file:
                file.write(self.last_folder)

            self.ui.stackedWidget.setCurrentIndex(1)
            self.resize(
                min(self.width(), self.height()),
                int(
                    min(self.width(), self.height())
                    / self.ui.page_edit_config.aspect_ratio
                ),
            )
            self.aspect_ratio = self.width() / self.height()
        else:
            self.ui.error_message.setVisible(True)

    def resizeEvent(self, event):
        if self.ui.stackedWidget.currentIndex() == 1:
            if hasattr(self.ui.page_edit_config, "aspect_ratio"):
                curr_aspect_ratio = event.size().width() / event.size().height()
                if (
                    abs(self.ui.page_edit_config.aspect_ratio - curr_aspect_ratio)
                    > 0.01
                ):
                    new_height = event.size().height()
                    new_width = event.size().width()
                    if new_width / self.ui.page_edit_config.aspect_ratio > new_height:
                        new_width = int(
                            new_height / self.ui.page_edit_config.aspect_ratio
                        )
                    else:
                        new_height = int(
                            new_width * self.ui.page_edit_config.aspect_ratio
                        )
                    self.resize(new_width, new_height)

        return super().resizeEvent(event)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    wind = MainWindow()

    wind.show()
    sys.exit(app.exec())
