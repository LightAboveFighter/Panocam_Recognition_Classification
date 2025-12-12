from PyQt6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsItem,
)

from PyQt6.QtCore import QRectF, QPointF, Qt
from PyQt6.QtGui import QPainterPath, QBrush, QPen, QColor


class NgonItem(QGraphicsItem):
    def __init__(self, n_points: int = 4, *points: QPointF | int):
        super().__init__()
        self._pen = None
        self._brush = None
        self.n = n_points
        if len(points) == self.n * 2:
            self.points = [
                QPointF(points[i * 2], points[i * 2 + 1]) for i in range(self.n)
            ]
        else:
            self.points = points
        self.setPen(QPen(QColor(255, 140, 0), 2))
        self.setBrush(QBrush(QColor(255, 165, 0, 128)))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    def setPoints(self, *points: QPointF | int):
        """Установить точки многоугольника"""
        if len(points) == self.n:
            self.points = list(points)
        elif len(points) == self.n * 2:
            self.points = [
                QPointF(points[i * 2], points[i * 2 + 1]) for i in range(self.n)
            ]
        else:
            return

        self.prepareGeometryChange()
        self.update()

    def get_xy(self) -> list[int]:
        xy = []
        for point in self.points:
            xy.append(int(point.x()))
            xy.append(int(point.y()))
        return xy

    def setBrush(self, brush):
        self._brush = brush
        self.update(self.boundingRect())

    def setPen(self, pen):
        self._pen = pen
        self.update(self.boundingRect())

    def brush(self):
        return self._brush

    def pen(self):
        return self._pen

    def boundingRect(self):
        """Возвращает ограничивающий прямоугольник элемента"""
        if not self.points:
            return QRectF()

        min_x = min(point.x() for point in self.points)
        min_y = min(point.y() for point in self.points)
        max_x = max(point.x() for point in self.points)
        max_y = max(point.y() for point in self.points)

        pen_width = self.pen().width()
        return QRectF(
            min_x - pen_width,
            min_y - pen_width,
            max_x - min_x + 2 * pen_width,
            max_y - min_y + 2 * pen_width,
        )

    def shape(self):
        """Возвращает точную форму для обработки событий"""
        path = QPainterPath()
        if len(self.points) < 2:
            return path

        path.moveTo(self.points[0])
        for i in range(1, len(self.points)):
            path.lineTo(self.points[i])
        path.closeSubpath()
        return path

    def paint(self, painter, option, widget=None):
        """Отрисовывает четырёхугольник"""
        if len(self.points) != self.n:
            return

        path = QPainterPath()
        path.moveTo(self.points[0])
        for i in range(1, self.n):
            path.lineTo(self.points[i])
        path.closeSubpath()

        painter.setBrush(self._brush)
        painter.setPen(self._pen)
        painter.drawPath(path)


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
