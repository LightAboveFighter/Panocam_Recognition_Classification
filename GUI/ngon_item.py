from PyQt6.QtWidgets import QApplication, QGraphicsView, QGraphicsScene, QGraphicsItem
from PyQt6.QtGui import QPen, QPolygonF
from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtWidgets import QGraphicsItem
import numpy as np

from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtCore import QRectF, QPointF
from PyQt6.QtGui import QPainter, QPainterPath, QBrush, QPen, QColor


class NgonItem(QGraphicsItem):
    def __init__(self, n_points: int = 4, *points: QPointF | int):
        super().__init__()
        self.n = n_points
        if len(points) == self.n * 2:
            self.points = [
                QPointF(points[i * 2], points[i * 2 + 1]) for i in range(self.n)
            ]
        else:
            self.points = points
        self.brush = QBrush(QColor(255, 165, 0, 128))
        self.pen = QPen(QColor(255, 140, 0), 2)

    def setPoints(self, *points: QPointF | int):
        """Установить четыре точки четырёхугольника"""
        if len(points) == self.n:
            self.points = points
        if len(points) == self.n * 2:
            self.points = [
                QPointF(points[i * 2], points[i * 2 + 1]) for i in range(self.n)
            ]
        self.update(self.boundingRect())

    def get_xy(self) -> list[int]:
        xy = []
        for point in self.points:
            xy.append(int(point.x()))
            xy.append(int(point.y()))
        return xy

    def setBrush(self, brush):
        """Установить кисть для заливки"""
        self.brush = brush
        self.update(self.boundingRect())

    def setPen(self, pen):
        """Установить перо для контура"""
        self.pen = pen
        self.update(self.boundingRect())

    def boundingRect(self):
        """Возвращает ограничивающий прямоугольник элемента"""
        min_x = min(point.x() for point in self.points)
        min_y = min(point.y() for point in self.points)
        max_x = max(point.x() for point in self.points)
        max_y = max(point.y() for point in self.points)
        return QRectF(min_x, min_y, max_x - min_x, max_y - min_y)

    def paint(self, painter, option, widget=None):
        """Отрисовывает четырёхугольник"""
        if len(self.points) != self.n:
            return

        # Создаем путь из четырех точек
        path = QPainterPath()
        path.moveTo(self.points[0])
        for i in range(1, self.n):
            path.lineTo(self.points[i])
        # path.lineTo(self.points[2])
        # path.lineTo(self.points[3])
        path.closeSubpath()  # Замыкаем путь

        # Заливаем и обводим контур
        painter.setBrush(self.brush)
        painter.setPen(self.pen)
        painter.drawPath(path)
