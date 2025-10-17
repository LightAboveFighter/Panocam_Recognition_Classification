import cv2 as cv
from edit_config_class import Ui_Form
from dialog import Dialog
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QWidget,
    QGraphicsView,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QFileDialog,
)
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QPointF, pyqtSignal, QObject, QEvent
from enum import Enum
from pathlib import Path
import yaml

import sys

# Добавляем путь к директории выше текущей
print(str(Path().cwd().parent / "tracker.py"))
sys.path.insert(0, str(Path().cwd().parent))
from ..source.tracker import Tracker


class ToolType(Enum):
    NoDrawing = 0
    Border = 1
    DetectWindow = 2


class ScrollBarWheelFilter(QObject):
    """Event filter that ignores wheel events on scroll bars."""

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            return True
        return super().eventFilter(obj, event)


class DrawableGraphicsScene(QGraphicsScene):
    drawing_completed = pyqtSignal(
        int, int, int, int, int
    )  # x1, y1, x2, y2, ToolType.value

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_tool = ToolType.NoDrawing  # rectangle, line
        self.start_point = QPointF()
        self.current_item = None
        self.touched = False
        self.pen = QPen(QColor(255, 0, 0), 2)
        self.second_point = (0, 0)

    def set_current_tool(self, tool: ToolType):
        self.current_tool = tool

    def draw_objects(self, data: list[dict]):
        for obj in data:
            obj_type = obj.get("type", "notype")

            x1, y1 = obj["point1"]
            x2, y2 = obj["point2"]

            drawing = None
            if obj_type == "border":
                drawing = QGraphicsLineItem(x1, y1, x2, y2)
            elif obj_type == "detect_window":
                drawing = QGraphicsRectItem(x1, y1, abs(x1 - x2), abs(y1 - y2))
            else:
                return
            if not drawing is None:
                drawing.setPen(self.pen)
                self.addItem(drawing)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.current_tool == ToolType.NoDrawing:
                return super().mouseReleaseEvent(event)

            self.touched = True
            self.start_point = event.scenePos()
            self.second_point = (int(self.start_point.x()), int(self.start_point.y()))

            if self.current_tool == ToolType.Border:
                self.current_item = QGraphicsLineItem()
                self.current_item.setLine(
                    self.start_point.x(),
                    self.start_point.y(),
                    self.start_point.x(),
                    self.start_point.y(),
                )
            elif self.current_tool == ToolType.DetectWindow:
                self.current_item = QGraphicsRectItem()
                self.current_item.setRect(
                    self.start_point.x(), self.start_point.y(), 0, 0
                )

            if self.current_item:
                self.current_item.setPen(self.pen)
                self.addItem(self.current_item)
        elif event.button() == Qt.MouseButton.RightButton:
            if self.current_item:
                self.removeItem(self.current_item)
            self.current_tool = ToolType.NoDrawing
            self.current_item = None
            self.drawing_completed.emit(0, 0, 0, 0, ToolType.NoDrawing.value)
            self.touched = False

        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if not self.touched:
            return super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            if self.current_tool != ToolType.NoDrawing:
                self.drawing_completed.emit(
                    int(self.start_point.x()),
                    int(self.start_point.y()),
                    *self.second_point,
                    self.current_tool.value,
                )

                self.touched = False
                self.current_tool = ToolType.NoDrawing
                self.current_item = None
        return super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self.current_item:
            current_point = event.scenePos()
            self.second_point = (int(current_point.x()), int(current_point.y()))

            if self.current_tool == ToolType.DetectWindow:
                rect = self.current_item.rect()
                rect.setCoords(
                    min(self.start_point.x(), current_point.x()),
                    min(self.start_point.y(), current_point.y()),
                    max(self.start_point.x(), current_point.x()),
                    max(self.start_point.y(), current_point.y()),
                )
                self.current_item.setRect(rect)
            elif self.current_tool == ToolType.Border:
                self.current_item.setLine(
                    self.start_point.x(),
                    self.start_point.y(),
                    current_point.x(),
                    current_point.y(),
                )
        return super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        event.ignore()


class EditConfigWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.ui = Ui_Form()
        self.ui.setupUi(self)

        self.scene = DrawableGraphicsScene()

        self.scene.drawing_completed.connect(self.get_points)
        self.ui.button_add_border.clicked.connect(self.draw_border)
        self.ui.button_add_detect_window.clicked.connect(self.draw_spectator)
        self.ui.button_save_config.clicked.connect(self.save_config)
        self.ui.action_save_config.triggered.connect(self.save_config)
        self.ui.button_load_config.clicked.connect(self.open_config)
        self.ui.action_open_config.triggered.connect(self.open_config)
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
        self.ui.frame_viewer.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.ui.frame_viewer.setScene(self.scene)
        self.ui.frame_viewer.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )
        self.ui.frame_viewer.setOptimizationFlag(
            QGraphicsView.OptimizationFlag.DontSavePainterState, True
        )
        self.set_drag_on()

        filename_last_path = Path("GUI/user_files/last_config_folder.txt")
        if not filename_last_path.parent.exists():
            Path(filename_last_path).parent.mkdir()
        if not filename_last_path.exists():
            self.last_folder = None
            filename_last_path.touch()
        else:
            with filename_last_path.open("r") as file:
                self.last_folder = file.readline()

        self.video_cap = None
        self.data = []
        self.curr_id = 0
        self.curr_scale = 1.0

    def set_path(self, path: str):
        self.video_cap = cv.VideoCapture(path)
        success, im = self.video_cap.read()
        if success:
            self.change_frame(im)
            self.set_scene(im)
        else:
            self.video_cap.release()
            self.video_cap = None
        return success

    def set_scene(self, frame):
        self.scene.clear()
        self.scene.addPixmap(self.current_frame)
        self.scene.setSceneRect(
            0,
            0,
            self.current_frame.width(),
            self.current_frame.height(),
        )
        self.aspect_ratio = frame.shape[0] / frame.shape[1]

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

    def update_view(self):
        self.ui.frame_viewer.fitInView(
            self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio
        )

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
        zoom_factor = 1.1
        max_zoom = 5.0
        min_zoom = 1.0

        event.accept()
        if event.angleDelta().y() < 0:
            if self.curr_scale * zoom_factor < min_zoom:
                zoom_factor = 1.0
            else:
                zoom_factor = 1 / zoom_factor
        if event.angleDelta().y() > 0:
            if self.curr_scale >= max_zoom:
                zoom_factor = max_zoom / self.curr_scale

        self.curr_scale *= zoom_factor
        self.ui.frame_viewer.scale(zoom_factor, zoom_factor)

    def get_rescaled_data(self, data):
        zoom_val = self.zoom_value()

        rescaled_data = []
        for obj in data:
            res = obj.copy()
            res["point1"] = [
                obj["point1"][0] * zoom_val,
                obj["point1"][1] * zoom_val,
            ]
            res["point2"] = [
                obj["point2"][0] * zoom_val,
                obj["point2"][1] * zoom_val,
            ]
            rescaled_data.append(res)
        return rescaled_data

    def heightForWidth(self, width):
        return int(width / self.aspect_ratio)

    def zoom_value(self):
        return self.scene.width() / self.current_frame.width()

    def draw_border(self):
        self.scene.set_current_tool(ToolType.Border)
        self.ui.frame_viewer.setDragMode(QGraphicsView.DragMode.NoDrag)

    def draw_spectator(self):
        self.scene.set_current_tool(ToolType.DetectWindow)
        self.ui.frame_viewer.setDragMode(QGraphicsView.DragMode.NoDrag)

    def get_points(self, p1_x: int, p1_y: int, p2_x: int, p2_y: int, tool_type: int):
        if tool_type == ToolType.NoDrawing.value:
            self.set_drag_on()
            return

        zoom_val = self.zoom_value()
        pack = (
            [int(p1_x / zoom_val), int(p1_y / zoom_val)],
            [int(p2_x / zoom_val), int(p2_y / zoom_val)],
        )
        if tool_type == ToolType.Border.value:
            self.data.append(
                {
                    "type": "border",
                    "room_id": self.curr_id,
                    "accuracy": 20,
                    "point1": pack[0],
                    "point2": pack[1],
                }
            )
        elif tool_type == ToolType.DetectWindow.value:
            self.data.append(
                {
                    "type": "detect_window",
                    "room_id": self.curr_id,
                    "accuracy": 20,
                    "point1": pack[0],
                    "point2": pack[1],
                }
            )
        self.set_drag_on()
        self.curr_id += 1

    def set_drag_on(self):
        self.ui.frame_viewer.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def save_config(self):

        if self.last_folder is None:
            folder = Path().cwd()
        else:
            folder = self.last_folder

        path = QFileDialog.getSaveFileName(
            self,
            "Выберите файл",
            str(folder),
            "YAML (*.yaml)",
        )[0]
        if len(path) == 0:
            return

        self.last_folder = str(Path(path).parent)
        with open(path, "w+") as file:
            yaml.dump(self.data, file)

    def open_config(self):
        if self.last_folder is None:
            folder = Path().cwd()
        else:
            folder = self.last_folder

        path = QFileDialog.getOpenFileName(
            self,
            "Выберите файл",
            str(folder),
            "YAML (*.yaml)",
        )[0]
        if len(path) == 0:
            return

        with open(path, "r") as file:
            data = yaml.safe_load(file)

        approved = []
        resized = []
        for obj in data:
            x1, y1 = obj["point1"]
            if x1 > self.current_frame.width() or y1 > self.current_frame.height():
                continue

            x2, y2 = obj["point2"]
            if x2 > self.current_frame.width() or y2 > self.current_frame.height():
                continue

            resized.append(self.get_rescaled_data([obj])[0])
            approved.append(obj)
            self.curr_id = max(self.curr_id, obj["room_id"])
        self.data.extend(approved)
        self.scene.draw_objects(resized)

    def process(self):
        show = Dialog(self, "Show processing?").get_answer()

        video_out = cv.VideoWriter(f"materials/out/1.avi")

        tracker = Tracker("yolo11n.pt", self.data, video_out)

        while self.video_cap.isOpened():
            success, frame = self.video_cap.read()
            if not success:
                continue

            frame = tracker.track_frame(frame)
            if show:
                self.change_frame(frame)
