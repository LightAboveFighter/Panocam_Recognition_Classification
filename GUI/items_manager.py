from PyQt6.QtGui import QPen, QBrush, QColor
from graphic_items import TrackGraphicItem
from PyQt6.QtWidgets import QGraphicsScene


class ItemsManager:

    def __init__(self, scene: QGraphicsScene):

        self.pens = {
            "red_border": QPen(QColor("red")),
            "filled_red": QPen(QColor(255, 0, 0, 0)),
        }
        self.brushes = {"filled_red_circle": QBrush(QColor(255, 0, 0, 0))}
        self.items = {"people": [], "tsds": []}
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

    def update(self, data: dict):

        for key in ["people", "tsds"]:
            self._update_rects(data, key)
