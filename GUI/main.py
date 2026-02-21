import sys
from PyQt6.QtWidgets import QMainWindow, QApplication, QWidget
from start_page import Ui_MainWindow
from pathlib import Path
from view_edit_window import Ui_MainWindow as EditConfigWindowUi
from video_processing_thread import VideoProcessingThread
from threaded_viewer import ThreadedViewer
from PyQt6.QtCore import QTimer, QThread, pyqtSignal
import yaml
import torch.cuda as cuda
from ultralytics import YOLO
from file_methods import get_user_path_save_last_dir

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from source.tracker import AI_names


class EditConfigWindow(QMainWindow):

    session: list[dict]
    viewers: list[ThreadedViewer]
    hidden_processors: list[VideoProcessingThread]
    set_path_succeded = pyqtSignal(bool)
    load_session_succeded = pyqtSignal(bool)

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.ui = EditConfigWindowUi()
        self.ui.setupUi(self)
        self.ui.stacked_widget.setCurrentIndex(0)  # editing page
        self.ui.edit_config_widget.processing.connect(self.process)
        self.ui.edit_config_widget.set_path_succeded.connect(self._finalize_editconfigwidget_set_path)
        self.ui.add_video_button.clicked.connect(self.show_start_page)
        self.ui.save_session_button.clicked.connect(self.save_session)
        self.ui.load_session_button.clicked.connect(self.load_session)

        self.hidden_processors = []
        self.viewers = []
        self.saved_viewer_size = None
        self.session = []
        self._finalize_editconfigwidget_set_path_scenario = 0
        self._load_session_list = []
        self._load_session_success = False

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

    def _finalize_editconfigwidget_set_path(self, success: bool):
        if self._finalize_editconfigwidget_set_path_scenario == 1:
            self._finalize_editconfigwidget_set_path_scenario = 0
            if success:
                self.ui.stacked_widget.setCurrentIndex(0)  # editing page
            self.set_path_succeded.emit(success)
            return
        
        if self._finalize_editconfigwidget_set_path_scenario == 2:

            if success:
                self._load_session_success = True
                self.ui.edit_config_widget.construct_data(self._load_session_list[0]["data"])
                self.process(self._load_session_list[0]["options"])

            self._load_session_list.pop(0)

            if len(self._load_session_list) == 0:
                self._finalize_editconfigwidget_set_path_scenario = 0
                load_session_success = self._load_session_success
                self._load_session_success = False
                if not load_session_success:
                    self.load_session_succeded.emit(False)
                    return
                else:
                    self.ui.stacked_widget.setCurrentIndex(1)
                self.load_session_succeded.emit(True)
                return

            self.ui.edit_config_widget.set_path(self._load_session_list[0]["path"])
            return
        
        if self._finalize_editconfigwidget_set_path_scenario == -1:
            self._finalize_editconfigwidget_set_path_scenario = 0
            self.load_session_succeded.emit(False)


    def set_path(self, path: str):
        """Emits success of the operation with set_path_succeded(bool) pyqtsignal"""
        if self._finalize_editconfigwidget_set_path_scenario != 0:
            return
        self._finalize_editconfigwidget_set_path_scenario = 1
        self.ui.edit_config_widget.set_path(path)

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

    def get_row_column(self, ordinal_index):
        if ordinal_index == 0:
            row, column = (0, 0)
        elif ordinal_index == 1:
            row, column = (1, 0)
        elif ordinal_index <= 3:
            row, column = (ordinal_index - 2, 1)
        elif ordinal_index <= 5:
            row, column = (ordinal_index - 4, 2)
        elif ordinal_index <= 8:
            row, column = (2, ordinal_index - 6)

        return row, column

    def add_viewer(self, options):
        last_viewer_ind = len(self.viewers) % 9
        row, column = self.get_row_column(last_viewer_ind)

        viewer = ThreadedViewer(row=row, column=column, parent=self)
        if len(self.viewers) > 9:
            self.viewers.insert(0, viewer)
            self.viewers.pop(1)
            self.session.insert(
                0,
                {
                    "options": options,
                    "path": self.ui.edit_config_widget.path,
                    "data": [
                        track_object.get_dict()
                        for track_object in self.ui.edit_config_widget.data
                    ],
                },
            )
            self.session.pop(1)
        else:
            self.viewers.append(viewer)
            self.session.append(
                {
                    "options": options,
                    "path": self.ui.edit_config_widget.path,
                    "data": [
                        track_object.get_dict()
                        for track_object in self.ui.edit_config_widget.data
                    ],
                }
            )

        viewer.closed.connect(self.remove_viewer)
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
            options,
        )

    def remove_viewer(self, row: int, column: int):

        last_viewer_ind = len(self.viewers) % 9 - 1

        if row == 2:
            deleted_index = 6 + column
        else:
            deleted_index = 2 * column + row

        if self.ui.stacked_widget.currentIndex() != 1:
            self.ui.stacked_widget.setCurrentIndex(1)
            deleted_viewer = self.ui.mono_viewing_layout.itemAt(0).widget()
        else:
            deleted_viewer = self.ui.viewers_grid_layout.itemAtPosition(
                row, column
            ).widget()

        del_index = self.viewers.index(deleted_viewer)
        self.viewers.pop(del_index)
        self.session.pop(del_index)
        deleted_viewer.deleteLater()

        i = deleted_index
        while i <= last_viewer_ind - 1:
            i_row, i_column = self.get_row_column(i)
            curr_viewer = self.viewers[i]
            curr_viewer.row = i_row
            curr_viewer.column = i_column
            self.ui.viewers_grid_layout.addWidget(curr_viewer, i_row, i_column)
            i += 1

        self.ui.viewers_grid_layout.removeItem(
            self.ui.viewers_grid_layout.itemAtPosition(*self.get_row_column(i))
        )
        self.update_grid_stretch()

        if last_viewer_ind == 0:
            self.show_start_page()
            self.hide()

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

    def process(self, options: list[bool] = None):
        self.ui.stacked_widget.setCurrentIndex(1)  # viewers page

        self.add_viewer(options)

    def save_session(self):

        path = get_user_path_save_last_dir(
            self,
            "s",
            "Выберите куда сохранить файл сессии",
            "YAML (*.yaml)",
            "GUI/user_files/last_session_folder.txt",
        )

        if len(path) == 0:
            return

        with Path(path).open("w") as file:
            yaml.safe_dump(self.session, file, encoding="utf-8")

    def load_session(self):
        """
        Emits success of the operation with load_session_succeded(bool) pyqtsignal
        """

        path = get_user_path_save_last_dir(
            self,
            "o",
            "Выберите файл сессии",
            "YAML (*.yaml)",
            "GUI/user_files/last_session_folder.txt",
        )

        if len(str(path)) == 0:
            return False

        with Path(path).open("r") as file:
            self._load_session_list = yaml.safe_load(file)

        for i in range(len(self.viewers)):
            self.ui.viewers_grid_layout.removeItem(
                self.ui.viewers_grid_layout.itemAt(i)
            )
        self.viewers = []
        self.update_grid_stretch()
        if len(self._load_session_list) == 0:
            self._finalize_editconfigwidget_set_path_scenario = -1
            return
        self._finalize_editconfigwidget_set_path_scenario = 2
        self.ui.edit_config_widget.set_path(self._load_session_list[0]["path"])


class ExportModelsThread(QThread):
    def run(self):
        if cuda.is_available():
            for model_name in AI_names:
                if (
                    Path(model_name + ".engine").exists()
                    or Path(model_name + ".onnx").exists()
                ):
                    continue
                step_model = YOLO(model_name + ".pt")
                failed = False
                try:
                    step_model.export(
                        format="engine",
                        half=False,
                        int8=False,
                        dynamic=True,
                        simplify=True,
                        opset=17,
                    )
                except Exception as err:
                    print(err)
                    failed = True
                if failed:
                    step_model.export(
                        format="onnx",
                        half=False,
                        int8=False,
                        dynamic=True,
                        simplify=True,
                        opset=17,
                    )
            return
        for model_name in AI_names:
            if not Path(model_name + ".onnx").exists():
                step_model = YOLO(model_name + ".pt")
                step_model.export(
                    format="onnx",
                    half=False,
                    int8=False,
                    dynamic=True,
                    simplify=True,
                    opset=17,
                )


class StartPage(QMainWindow):

    thread_widgets: list[QWidget]

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.button_load_video.clicked.connect(self.open_video_file)
        self.ui.link_video_edit.enterKeyPressed.connect(self.view_frame_to_config)
        self.ui.load_session_button.clicked.connect(self.load_session)
        self.ui.button_update_models.clicked.connect(self.update_models)
        self.ui.error_message.setVisible(False)
        self.aspect_ratio = None
        self.view_edit_window = None
        self._exporting_thread = ExportModelsThread()
        self._exporting_thread.finished.connect(self.enable_update_models_button)
        self._exporting_thread.start()
        self._view_frame_to_config_path = None

    def set_view_edit_window(self):
        if self.view_edit_window is None:
            if self.parent() is None:
                self.view_edit_window = EditConfigWindow(parent=self)
                self.view_edit_window.set_path_succeded.connect(self._finalize_view_frame_to_config)
                self.view_edit_window.load_session_succeded.connect(self._finalize_load_session)
            else:
                self.view_edit_window = self.parent()

    def _finalize_load_session(self, success: bool):
        if not success:
            self.ui.error_message.setText(f"Unable to open any files from session file")
            self.ui.error_message.setVisible(True)
            return
        self.view_edit_window.show()
        self.hide()


    def load_session(self):
        self.set_view_edit_window()
        self.view_edit_window.load_session()

    def open_video_file(self):
        path = get_user_path_save_last_dir(
            self,
            "o",
            "Выберите видео",
            "Видео файлы (*.mp4 *.avi)",
            "GUI/user_files/last_video_folder.txt",
        )

        self.view_frame_to_config(path)
    
    def _finalize_view_frame_to_config(self, success: bool):
        if success:
            self.view_edit_window.show()
            self.hide()
        else:
            self.ui.error_message.setText(f"Unable to open {self._view_frame_to_config_path}")
            self.ui.error_message.setVisible(True)
            self._view_frame_to_config_path = None


    def view_frame_to_config(self, path: str = None):
        if len(path) == 0:
            return

        self._view_frame_to_config_path = path
        self.set_view_edit_window()
        self.view_edit_window.set_path(path)

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
        self.ui.button_update_models.hide()
        return super().hide()

    def enable_update_models_button(self):
        self.ui.button_update_models.setEnabled(True)

    def update_models(self):
        for path in Path("materials/trained_models").glob("*.onnx"):
            path.unlink()
            print(f"Deleted {path}")
        for path in Path("materials/trained_models").glob("*.engine"):
            path.unlink()
            print(f"Deleted {path}")
        self._exporting_thread.start()
        self.ui.button_update_models.setEnabled(False)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    wind = StartPage()

    wind.show()
    sys.exit(app.exec())