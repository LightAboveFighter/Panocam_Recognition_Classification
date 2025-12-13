from PyQt6.QtGui import QPen, QBrush, QColor
from graphic_items import TrackGraphicItem, AbstractActivatedIdGraphicsItem
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsItem
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
        self.items = {"people": [], "tsds": [], "curtains": []}
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

    def _update_static_items(self, data: dict[int, dict]):
        """
        Args: data: dict = {id: (border: None|QColor, detect_window: None|QColor) }
        """
        for id, (border_color, detect_window_color) in data.items():
            item_pair = self.static_items[id]
            if not border_color is None:
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
        item.setPen(pen)
        if id not in self.static_items.keys():
            self.static_items[id] = [None, None]
        self.static_items[id][item_type] = item

        self.scene.addItem(item)

    def update(self, data: dict):

        for key in ["people", "tsds"]:
            self._update_rects(data, key)
        detect_windows_colours = {}
        for val, id in data["curtains"]:
            if val == 0:
                colour = QColor(255, 0, 0, 50)
            else:
                colour = QColor(0, 255, 0, 50)
            detect_windows_colours[id] = (
                None,
                colour,
            )  # border, detect_window (colours)

        self._update_static_items(detect_windows_colours)
