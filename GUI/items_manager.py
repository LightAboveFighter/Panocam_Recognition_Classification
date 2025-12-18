from PyQt6.QtGui import QPen, QBrush, QColor
from graphic_items import (
    TrackGraphicItem,
    AbstractActivatedIdGraphicsItem,
    TextGraphicItem,
)
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsTextItem
from random_qt_color import get_rand_brush_color

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from source.track_objects import AbstractTrackObject


class ItemsManager:

    static_items: dict[int, list[AbstractActivatedIdGraphicsItem]]

    def __init__(self, scene: QGraphicsScene):

        self.pens = {
            "red_border": QPen(QColor("red")),
            "filled_red": QPen(QColor(255, 0, 0, 0)),
        }
        self.brushes = {"filled_red_circle": QBrush(QColor(255, 0, 0, 0))}
        self.items = {
            "people": [],
            "tsds": [],
            "curtains": [],
            "bills": [],
            "border_counts": [],
            "clothes": [],
        }
        self.static_items = {}
        self.scene = scene

    def _update_rects(self, data: dict, key: str):

        for i, points in enumerate(data[key]):
            p1, p2 = points
            if i >= len(self.items[key]):
                item = TrackGraphicItem(*p1, *p2, parent=None)
                self.items[key].append(item)
                self.scene.addItem(item)
            else:
                self.items[key][i].setRect(*p1, *p2)
                self.items[key][i].show()

        for i in range(
            len(data[key]),
            len(self.items[key]),
        ):
            self.items[key][i].hide()

    def _update_texts(
        self,
        data: dict,
        key: str,
        margins_x: list[int],
        margins_y: list[int],
        color: QColor,
    ):

        for i, (points, cloth_name) in enumerate(data[key]):
            p1, p2 = points[0], points[1]
            if i >= len(self.items[key]):
                item = TextGraphicItem(cloth_name)
                item.setFontAndColor(20, color)
                item.setValidPos(p1, p2, margins_x[i], margins_y[i], self.scene)
                self.items[key].append(item)
                self.scene.addItem(item)
            else:
                item = self.items[key][i]
                item.setValidPos(p1, p2, margins_x[i], margins_y[i], self.scene)
                item.show()

        for i in range(
            len(data[key]),
            len(self.items[key]),
        ):
            self.items[key][i].hide()

    def _update_static_colors(self, data: dict[int, dict]):
        """
        Args: data: dict = {id: (border: None|QColor, detect_window: None|QColor) }
        """
        for id, (border_color, detect_window_color) in data.items():
            item_pair = self.static_items[id]
            if border_color is None:
                item_pair[0].set_orig_color()
            else:
                item_pair[0]._pen.setColor(border_color)
                item_pair[0]._brush.setColor(border_color)
            item_pair[0].update()

            if (not detect_window_color is None) and (not item_pair[1] is None):
                item_pair[1]._pen.setColor(detect_window_color)
                item_pair[1]._brush.setColor(detect_window_color)
                item_pair[1].update()

    def add_static_item(self, track_object: AbstractTrackObject):
        brush, pen = get_rand_brush_color(alpha=40)
        item = track_object.get_qt_graphic_item()
        id = track_object.room_id
        item_type = 0

        if track_object.get_type() == "detect_window":
            item.setBrush(brush)
            item_type = 1
        else:
            count_item = TextGraphicItem("0")
            count_item.setFontAndColor(30, QColor("black"))
            p1, p2 = (
                track_object.get_dict()["point1"],
                track_object.get_dict()["point2"],
            )
            if p1[0] < p2[0]:
                margin = 30
            else:
                margin = -30
            count_item.setValidPos(p1, p2, margin, -40)

            self.static_items[id][2] = count_item
            self.scene.addItem(count_item)
        item.setPen(pen)
        if id not in self.static_items.keys():
            self.static_items[id] = [None, None, None]
        self.static_items[id][item_type] = item

        self.scene.addItem(item)

    def update(self, data: dict):

        for key in ["people", "tsds", "bills"]:
            self._update_rects(data, key)

        self._update_rects(
            {key: [[points[0], points[1]] for points, _ in data["clothes"]]}, key
        )
        margins_x = []
        margins_y = []
        for xyxy, _ in data["clothes"]:
            p1, p2 = xyxy[0], xyxy[1]
            if p1[0] < p2[0]:
                margins_x.append(30)
            else:
                margins_x.append(-30)
            margins_y.append(-40)
        self._update_texts(data, "clothes", margins_x, margins_y, QColor("red"))

        detect_windows_colours = {}
        for val, id in data["curtains"]:
            if val == 0:
                colour = QColor(255, 0, 0, 50)
            else:
                colour = QColor(0, 255, 0, 50)
            detect_windows_colours[id] = [
                None,
                colour,
            ]  # border, detect_window (colours)
        for id, border_count in data["border_counts"]:
            if self.static_items[id][2].toPlainText() != str(abs(border_count)):
                color = QColor("white")
            else:
                color = None

            if not id in detect_windows_colours.keys():
                detect_windows_colours[id] = [color, None]
            else:
                detect_windows_colours[id][0] = color
            if not color is None:
                self.static_items[id][2].setPlainText(str(abs(border_count)))

        self._update_static_colors(detect_windows_colours)
