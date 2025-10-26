from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QPen
from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QGraphicsItem

from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtCore import QRectF, QPointF
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
