from PyQt6.QtWidgets import (
    QGraphicsScene,
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsItem,
)
from PyQt6.QtGui import QPen, QBrush, QColor
from PyQt6.QtCore import QRectF, Qt
import numpy as np


class TrackGraphicItem(QGraphicsItem):

    def __init__(self, x1: int, y1: int, x2: int, y2: int, parent=...):
        super().__init__(parent)

        self.rect = None
        self.centre_point = None
        self.pen = QPen(QColor(255, 0, 0))
        self.pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        self.pen.setWidth(2)
        self.brush = QBrush(QColor(255, 0, 0, 0))
        self.setRect(x1, y1, x2, y2)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)

    def boundingRect(self):
        if self.rect is None:
            return QRectF()

        pen_width = self.pen.widthF()
        return self.rect.adjusted(-pen_width, -pen_width, pen_width, pen_width)

    def height(self):
        if self.rect:
            return self.rect.height()
        return 0

    def width(self):
        if self.rect:
            return self.rect.width()
        return 0

    def paint(self, painter, option, widget=None):
        painter.setPen(self.pen)
        painter.setBrush(self.brush)

        if self.rect:
            painter.drawRect(self.rect)

        if self.centre_point:
            painter.setBrush(QBrush(QColor(255, 0, 0, 255)))
            painter.drawEllipse(self.centre_point)

    def setRect(self, x1: int, y1: int, x2: int, y2: int):
        sorted_x = sorted([x1, x2])
        sorted_y = sorted([y1, y2])

        self.p1 = [sorted_x[0], sorted_y[0]]
        self.p2 = [sorted_x[1], sorted_y[1]]

        width = self.p2[0] - self.p1[0]
        height = self.p2[1] - self.p1[1]

        self.rect = QRectF(self.p1[0], self.p1[1], width, height)

        center_x = self.p1[0] + width / 2 - 2.5
        center_y = self.p1[1] + height / 2 - 2.5
        self.centre_point = QRectF(center_x, center_y, 5, 5)

        self.prepareGeometryChange()

    def setPen(self, pen):
        self.pen = pen
        self.update()

    def setBrush(self, brush):
        self.brush = brush
        self.update()


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
