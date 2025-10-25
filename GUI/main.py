import sys
from PyQt6.QtWidgets import QFileDialog, QMainWindow, QApplication, QWidget
from PyQt6.QtGui import QImage, QPixmap
from start_page import Ui_MainWindow
from pathlib import Path
from editconfigwidget import EditConfigWidget
from edit_config_window import Ui_MainWindow as EditConfigWindowUi


class EditConfigWindow(QMainWindow):

    def __init__(self, parent):
        super().__init__(parent)
        self.ui = EditConfigWindowUi()
        self.ui.setupUi(self)
        self.edit_config_widget = self.ui.centralwidget


class MainWindow(QMainWindow):

    thread_widgets: list[QWidget]

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
            with filename_last_path.open("r") as file:
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
        edit_config = EditConfigWindow(parent=self)
        if edit_config.edit_config_widget.set_path(path):
            self.last_folder = str(Path(path).parent)
            with Path("GUI/user_files/last_video_folder.txt").open("w") as file:
                file.write(self.last_folder)

            edit_config.show()
        else:
            self.ui.error_message.setVisible(True)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    wind = MainWindow()

    wind.show()
    sys.exit(app.exec())
