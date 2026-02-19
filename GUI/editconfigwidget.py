import cv2 as cv
from edit_config_class import Ui_Form
from dialog import Dialog
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QWidget,
    QGraphicsView,
)
from PyQt6.QtGui import QImage, QPixmap, QPainter
from PyQt6.QtCore import Qt, QPointF, pyqtSignal, QObject, QEvent, QTimer
from enum import Enum
import yaml
from random_qt_color import get_rand_brush_color
from graphic_items import NgonItem, ClickableLineItem

from video_processing_thread import VideoProcessingThread
from file_methods import get_user_path_save_last_dir
from vidgear.gears import CamGear

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from source.track_objects import (
    AbstractTrackObject,
    DetectWindow,
    get_track_object_from_dict,
)


class ToolType(Enum):
    NoDrawing = 0
    DetectWindow = 2


class ScrollBarWheelFilter(QObject):
    """Event filter that ignores wheel events on scroll bars."""

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            return True
        return super().eventFilter(obj, event)


class ResizingGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def wheelEvent(self, event):
        zoom_factor = 1.15
        max_scale = 5.0
        min_scale = 1.0

        current_scale = self.transform().m11()

        if event.angleDelta().y() > 0:
            factor = zoom_factor
        else:
            factor = 1.0 / zoom_factor

        new_scale = current_scale * factor

        if new_scale < min_scale or new_scale > max_scale:
            event.ignore()
            return

        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self.scale(factor, factor)
        event.accept()


class DrawableGraphicsScene(QGraphicsScene):
    detect_window_completed = pyqtSignal(
        int, int, int, int, int, int, int, int
    )  # x1, y1, x2, y2, x3, y3, x4, y4
    drawing_interrupted = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_tool = ToolType.NoDrawing
        self.start_point = QPointF()
        self.current_item = None
        self.touched = 0
        self.second_point = (0, 0)
        self.curr_id = 0

    def set_color(self):
        self.brush, self.pen = get_rand_brush_color(alpha=100)

    def set_current_tool(self, tool: ToolType, id):
        self.current_tool = tool
        self.curr_id = id

    def draw_objects(self, data: list[AbstractTrackObject]):
        for track_object in data:
            dict_data = track_object.get_dict()
            obj_type = dict_data.get("type", "notype")
            id = dict_data["room_id"]

            x1, y1 = dict_data["point1"]
            x2, y2 = dict_data["point2"]

            drawing = None
            self.set_color()
            if obj_type == "detect_window":
                x3, y3 = dict_data["point3"]
                x4, y4 = dict_data["point4"]
                drawing = NgonItem(id, 4, x1, y1, x2, y2, x3, y3, x4, y4)
                drawing.setZValue(2.5)
                drawing.setBrush(self.brush)
            else:
                return
            if not drawing is None:
                drawing.setPen(self.pen)
                self.addItem(drawing)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)

        if event.button() == Qt.MouseButton.LeftButton:
            if self.current_tool == ToolType.NoDrawing:
                return super().mousePressEvent(event)

            self.touched += 1
            self.start_point = event.scenePos()
            self.second_point = (int(self.start_point.x()), int(self.start_point.y()))

            if self.current_tool == ToolType.DetectWindow:
                if not self.current_item:
                    self.set_color()
                    self.current_item = NgonItem(
                        self.curr_id, 4, *[self.start_point for _ in range(4)]
                    )
                    self.current_item.setZValue(2.5)
                    self.current_item.setPen(self.pen)
                    self.current_item.setBrush(self.brush)
                    self.addItem(self.current_item)
                else:
                    points = self.current_item.points
                    points[self.touched - 1] = self.start_point
                    self.current_item.setPoints(
                        *points,
                    )

        elif event.button() == Qt.MouseButton.RightButton:
            if self.current_tool == ToolType.DetectWindow:
                self.touched -= 1
                self.start_point = event.scenePos()
                if self.touched == 0:
                    self.removeItem(self.current_item)
                    self.current_item = None
                    self.current_tool = ToolType.NoDrawing
                    self.drawing_interrupted.emit()
                elif self.current_item:
                    points = self.current_item.points
                    points[self.touched] = points[0]
                    self.current_item.setPoints(
                        *points,
                    )

    def mouseReleaseEvent(self, event):
        if self.touched == 0:
            return super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            if self.current_tool != ToolType.NoDrawing:
                if self.current_tool == ToolType.DetectWindow:
                    if self.touched == 4:
                        self.detect_window_completed.emit(*self.current_item.get_xy())
                        self.touched = 0
                        self.current_tool = ToolType.NoDrawing
                        self.current_item = None

        return super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self.current_item:
            current_point = event.scenePos()
            self.second_point = (int(current_point.x()), int(current_point.y()))

            if self.current_tool == ToolType.DetectWindow:
                self.current_item.setPoints(
                    *[*self.current_item.points[:3], current_point],
                )

        return super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        event.ignore()


class EditConfigWidget(QWidget):

    video_processor: VideoProcessingThread
    data: list[AbstractTrackObject]
    _video_cap: CamGear
    processing = pyqtSignal(list)  # show, AI options

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.scene = DrawableGraphicsScene()

        self.scene.detect_window_completed.connect(self.get_detect_window)
        self.scene.drawing_interrupted.connect(self.stop_drawing)
        self.ui.button_add_detect_window.clicked.connect(self.draw_spectator)
        self.ui.button_save_config.clicked.connect(self.save_config)
        self.ui.action_save_config.triggered.connect(self.save_config)
        self.ui.button_load_config.clicked.connect(self.load_config)
        self.ui.action_open_config.triggered.connect(self.load_config)
        self.ui.button_process.clicked.connect(self.process)

        self.ui.frame_viewer.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.ui.frame_viewer.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scrollbar_event_filter = ScrollBarWheelFilter()
        self.ui.frame_viewer.horizontalScrollBar().installEventFilter(
            self.scrollbar_event_filter
        )
        self.ui.frame_viewer.verticalScrollBar().installEventFilter(
            self.scrollbar_event_filter
        )
        self.ui.frame_viewer.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.ui.frame_viewer.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.ui.frame_viewer.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.SmartViewportUpdate
        )
        self.ui.frame_viewer.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.ui.frame_viewer.setScene(self.scene)
        self.ui.frame_viewer.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )
        self.ui.frame_viewer.setOptimizationFlag(
            QGraphicsView.OptimizationFlag.DontSavePainterState, True
        )
        self.ui.frame_viewer.setInteractive(True)
        self.set_drag(True)

        self._video_cap = None
        self.video_processor = None
        self.data = []
        self.path = None
        self.curr_id = 0
        self.curr_scale = 1.0
        self.exit_connection = []
        self.connection_cooldown = False

    def set_path(self, path: str) -> bool:
        """Change frame, delete all previous data

        Returns
        -------------
        success : bool
        """
        self.path = path
        try:
            self._video_cap = CamGear(source=path)
        except Exception as err:
            print(err)
            return False
        self.data = []
        im = self._video_cap.read()
        if not im is None:
            self.change_frame(im)
        else:
            self._video_cap.stop()
            self._video_cap = None
        return not im is None

    def change_frame(self, frame):
        image = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        height, width, channels = image.shape
        bytes_per_line = channels * width
        self.current_frame = QPixmap.fromImage(
            QImage(
                image.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888,
            )
        )
        self.scene.clear()
        pixmap = self.scene.addPixmap(self.current_frame)
        pixmap.setZValue(-2)
        self.scene.setSceneRect(
            0,
            0,
            self.current_frame.width(),
            self.current_frame.height(),
        )
        self.aspect_ratio = self.current_frame.height() / self.current_frame.width()

    def update_view(self):
        self.ui.frame_viewer.fitInView(
            self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio
        )
        self.curr_scale = 1.0

    def showEvent(self, event):
        # ensure that the update only happens when showing the window
        # programmatically, otherwise it also happen when unminimizing the
        # window or changing virtual desktop
        if not event.spontaneous():
            self.update_view()

    def resizeEvent(self, event):
        self.update_view()
        return super().resizeEvent(event)

    def wheelEvent(self, event):
        zoom_factor = 1.15
        max_scale = 5.0  # 500%
        min_scale = 1.0  # 100%

        if event.angleDelta().y() > 0:
            factor = zoom_factor
        else:
            factor = 1.0 / zoom_factor

        new_scale = self.curr_scale * factor

        if new_scale < min_scale or new_scale > max_scale:
            event.ignore()
            return

        self.curr_scale = new_scale
        self.ui.frame_viewer.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.ui.frame_viewer.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.ui.frame_viewer.scale(factor, factor)
        event.accept()

    def get_rescaled_data(self, data):
        zoom_val = self.zoom_value()

        rescaled_data = []
        for track_object in data:
            res = track_object.get_dict()

            for i in range(1, 3):
                res[f"point{i}"] = [
                    res[f"point{i}"][0] * zoom_val,
                    res[f"point{i}"][1] * zoom_val,
                ]

            if "point4" in res.keys():
                for i in range(3, 5):
                    res[f"point{i}"] = [
                        res[f"point{i}"][0] * zoom_val,
                        res[f"point{i}"][1] * zoom_val,
                    ]

            rescaled_data.append(get_track_object_from_dict(res))
        return rescaled_data

    def heightForWidth(self, width):
        return int(width / self.aspect_ratio)

    def zoom_value(self):
        return self.scene.width() / self.current_frame.width()

    def draw_spectator(self):
        self.scene.set_current_tool(ToolType.DetectWindow, self.curr_id)
        self.set_drag(False)
        self.ui.frame_viewer.setMouseTracking(True)
        self.curr_id += 1

    def stop_drawing(self):
        self.set_drag(True)
        self.ui.frame_viewer.setMouseTracking(False)
        self.ui.frame_viewer.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self.ui.frame_viewer.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )

    def get_detect_window(
        self,
        p1_x: int,
        p1_y: int,
        p2_x: int,
        p2_y: int,
        p3_x: int,
        p3_y: int,
        p4_x: int,
        p4_y: int,
    ):
        zoom_val = self.zoom_value()
        pack = (
            [int(p1_x / zoom_val), int(p1_y / zoom_val)],
            [int(p2_x / zoom_val), int(p2_y / zoom_val)],
            [int(p3_x / zoom_val), int(p3_y / zoom_val)],
            [int(p4_x / zoom_val), int(p4_y / zoom_val)],
        )
        self.data.append(DetectWindow(self.curr_id, *pack))

        self.stop_drawing()

    def set_drag(self, is_active: bool):
        if is_active:
            mode = QGraphicsView.DragMode.ScrollHandDrag
        else:
            mode = QGraphicsView.DragMode.NoDrag
        self.ui.frame_viewer.setDragMode(mode)

    def save_config(self):
        path = get_user_path_save_last_dir(
            self,
            "s",
            "Выберите файл",
            "YAML (*.yaml)",
            "GUI/user_files/last_config_folder.txt",
        )

        if len(path) == 0:
            return

        dict_data = [track_object.get_dict() for track_object in self.data]
        with open(path, "w+") as file:
            yaml.dump(dict_data, file)

    def construct_data(self, data: list[dict]):
        """construct valid self.data from raw list[dict]"""
        approved = []
        for obj in data:
            x1, y1 = obj["point1"]
            if x1 > self.current_frame.width() or y1 > self.current_frame.height():
                continue

            x2, y2 = obj["point2"]
            if x2 > self.current_frame.width() or y2 > self.current_frame.height():
                continue

            if x1 == x2 and y1 == y2:
                continue

            approved.append(obj)
            self.curr_id = max(self.curr_id, obj["room_id"]) + 1

        for dict_info in approved:
            self.data.append(get_track_object_from_dict(dict_info))

    def load_config(self):
        path = get_user_path_save_last_dir(
            self,
            "o",
            "Выберите файл",
            "YAML (*.yaml)",
            "GUI/user_files/last_config_folder.txt",
        )

        if len(path) == 0:
            return

        with open(path, "r") as file:
            data = yaml.safe_load(file)

        self.construct_data(data)
        resized = self.get_rescaled_data(self.data)

        self.scene.draw_objects(resized)

    def process(self):
        dialog = Dialog(self, "Show processing?")
        dialog.set_saved_check_boxes(True)

        success, options, add_options = dialog.get_answer()
        if not success:
            return

        dialog.save_check_box_options([*options, *add_options])

        self.processing.emit([*options[1:], *add_options])
