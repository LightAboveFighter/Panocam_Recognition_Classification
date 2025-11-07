import sys
from PyQt6.QtWidgets import QFileDialog, QMainWindow, QApplication, QWidget
from start_page import Ui_MainWindow
from pathlib import Path
from view_edit_window import Ui_MainWindow as EditConfigWindowUi
from video_processing_thread import VideoProcessingThread
from threaded_viewer import ThreadedViewer
from PyQt6.QtCore import QTimer


class EditConfigWindow(QMainWindow):

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.ui = EditConfigWindowUi()
        self.ui.setupUi(self)
        self.ui.stacked_widget.setCurrentIndex(0)  # editing page
        self.ui.edit_config_widget.processing.connect(self.process)
        self.ui.add_video_button.clicked.connect(self.show_start_page)

        self.hidden_processors = []
        self.viewers = []
        self.default_widget = QWidget()
        self.saved_viewer_size = None

    def show_start_page(self):
        self.parent().show()

    def closeEvent(self, event):

        self.hide()
        if self.parent():
            self.parent().hide()

        for hidden_process in self.hidden_processors:
            if hidden_process.isRunning():
                hidden_process.stop()
                if not hidden_process.wait(3000):
                    hidden_process.terminate()
                    hidden_process.wait(1000)
        for viewer in self.viewers:
            viewer.clear_thread(wait_time=1000)

        QTimer.singleShot(100, self.final_close)
        event.ignore()

    def final_close(self):
        """Финальное закрытие после завершения всех потоков"""
        QApplication.quit()

    def set_path(self, path: str) -> bool:
        success = self.ui.edit_config_widget.set_path(path)
        if success:
            self.ui.stacked_widget.setCurrentIndex(0)  # editing page
        return success

    def update_grid_stretch(self):
        viewers_count = len(self.viewers)
        for i in range(3):
            self.ui.viewers_grid_layout.setRowStretch(i, 0)
            self.ui.viewers_grid_layout.setColumnStretch(i, 0)

        if viewers_count >= 1:
            self.ui.viewers_grid_layout.setRowStretch(0, 1)
            self.ui.viewers_grid_layout.setColumnStretch(0, 1)
        if viewers_count >= 2:
            self.ui.viewers_grid_layout.setRowStretch(1, 1)
        if viewers_count >= 3:
            self.ui.viewers_grid_layout.setColumnStretch(1, 1)
        if viewers_count >= 5:
            self.ui.viewers_grid_layout.setColumnStretch(2, 1)
        if viewers_count >= 7:
            self.ui.viewers_grid_layout.setRowStretch(2, 1)

    def add_viewer(self):
        viewers_num = len(self.viewers) % 9 + 1
        if viewers_num == 1:
            row, column = (0, 0)
        elif viewers_num == 2:
            row, column = (1, 0)
        elif viewers_num <= 4:
            row, column = (viewers_num - 3, 1)
        elif viewers_num <= 6:
            row, column = (viewers_num - 5, 2)
        elif viewers_num <= 9:
            row, column = (2, viewers_num - 7)

        viewer = ThreadedViewer(row=row, column=column, parent=self)
        if len(self.viewers) > 9:
            self.viewers.insert(0, viewer)
            self.viewers.pop(1)
        else:
            self.viewers.append(viewer)

        viewer.clicked.connect(self.focus_viewer)
        self.ui.viewers_grid_layout.addWidget(viewer, row, column)

        self.update_grid_stretch()

        viewer.start_video_thread(
            self.ui.edit_config_widget.path,
            (
                self.ui.edit_config_widget.height(),
                self.ui.edit_config_widget.width(),
            ),
            self.ui.edit_config_widget.data,
        )

    def focus_viewer(self, row: int, column: int):
        if self.ui.stacked_widget.currentIndex() == 1:  # viewers page -> mono
            viewer = self.ui.viewers_grid_layout.itemAtPosition(row, column).widget()
            self.saved_viewer_size = viewer.size()

            self.ui.viewers_grid_layout.removeWidget(viewer)

            self.update_grid_stretch()

            self.ui.mono_viewing_layout.addWidget(viewer)
            self.ui.stacked_widget.setCurrentIndex(2)  # mono viewing page

        else:  # mono page -> viewers page
            viewer = self.ui.mono_viewing_layout.itemAt(0).widget()

            self.ui.mono_viewing_layout.removeWidget(viewer)

            self.ui.viewers_grid_layout.addWidget(viewer, row, column)

            if hasattr(self, "saved_viewer_size"):
                viewer.resize(self.saved_viewer_size)

            self.update_grid_stretch()

            self.ui.stacked_widget.setCurrentIndex(1)  # viewers page

    def process(self, show: bool = True):
        self.ui.stacked_widget.setCurrentIndex(1)  # viewers page
        if not show:
            self.hidden_processors.append(
                VideoProcessingThread(
                    False,
                    self.ui.edit_config_widget.path,
                    (
                        self.ui.edit_config_widget.height(),
                        self.ui.edit_config_widget.width(),
                    ),
                    self.ui.edit_config_widget.data,
                    parent=self,
                )
            )
            self.hidden_processors[-1].setObjectName(
                f"VideoProcessingThread in EditConfigWindowid=-{len(self.hidden_processors)}"
            )
            return

        self.add_viewer()


class StartPage(QMainWindow):

    thread_widgets: list[QWidget]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
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
        self.view_edit_window = None

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

        if self.view_edit_window is None:
            if self.parent() is None:
                self.view_edit_window = EditConfigWindow(parent=self)
            else:
                self.view_edit_window = self.parent()

        if self.view_edit_window.set_path(path):
            self.last_folder = str(Path(path).parent)
            with Path("GUI/user_files/last_video_folder.txt").open("w") as file:
                file.write(self.last_folder)

            self.view_edit_window.show()
            self.hide()
        else:
            self.ui.error_message.setVisible(True)

    def closeEvent(self, event):

        if self.view_edit_window is None or not self.view_edit_window.isVisible():
            return super().closeEvent(event)

        if self.view_edit_window.isVisible():
            self.hide()
            event.ignore()
            return

    def hide(self):
        self.ui.error_message.hide()
        self.ui.link_video_edit.setText("")
        return super().hide()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    wind = StartPage()

    wind.show()
    sys.exit(app.exec())
