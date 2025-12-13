from PyQt6.QtWidgets import (
    QGraphicsRectItem,
    QGraphicsEllipseItem,
    QGraphicsItem,
)
import math
from PyQt6.QtCore import QRectF, QPointF, Qt, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QPainterPath, QBrush, QPen, QColor, QPainterPathStroker, QCursor


class _ClickableLineItemSignals(QObject):
    clicked = pyqtSignal(int)  # id


class ClickableLineItem(QGraphicsItem):

    def __init__(
        self, id: int, x1: int = 0, y1: int = 0, x2: int = 0, y2: int = 0, parent=None
    ):
        self.iteraction_thickness = 30
        super().__init__(parent=parent)
        self.p1 = (x1, y1)
        self.p2 = (x2, y2)
        self.id = id
        self.setPen(QPen(QColor(255, 140, 0), 2))
        self.setBrush(QBrush(QColor(255, 165, 0, 128)))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setAcceptHoverEvents(True)
        self.setEnabled(False)
        self.setZValue(self.zValue() + 1)
        self._mouse_captured = False
        self._is_hovered = False
        self.signals = _ClickableLineItemSignals()
        self.clicked = self.signals.clicked

    def setLine(self, x1: int, y1: int, x2: int, y2: int):
        self.p1 = (x1, y1)
        self.p2 = (x2, y2)

        self.prepareGeometryChange()
        self.update()

    def setBrush(self, brush):
        self._brush = brush
        self.update(self.boundingRect())

    def setPen(self, pen):
        self._pen = pen
        self.orig_color = pen.color()
        self.update(self.boundingRect())

    def brush(self):
        return self._brush

    def pen(self):
        return self._pen

    def boundingRect(self):
        min_x, max_x = sorted([self.p1[0], self.p2[0]])
        min_y, max_y = sorted([self.p1[1], self.p2[1]])

        pen_width = self.pen().width()
        margin = self.iteraction_thickness / 2
        return QRectF(
            min_x - pen_width,
            min_y - pen_width,
            max_x - min_x + 2 * pen_width,
            max_y - min_y + 2 * pen_width,
        ).adjusted(-margin, -margin, margin, margin)

    def shape(self):
        path = QPainterPath()

        path.moveTo(QPointF(*self.p1))
        path.lineTo(QPointF(*self.p2))
        path.closeSubpath()
        stroker = QPainterPathStroker()
        stroker.setWidth(self.iteraction_thickness)
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
        stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return stroker.createStroke(path)

    def setEnabled(self, enabled):
        if enabled:
            self.setZValue(self.zValue() + 1)
        else:
            self.setZValue(self.zValue() - 1)
        return super().setEnabled(enabled)

    def paint(self, painter, option, widget=None):
        path = QPainterPath()
        path.moveTo(QPointF(*self.p1))
        path.lineTo(QPointF(*self.p2))
        path.closeSubpath()

        painter.setBrush(self._brush)
        painter.setPen(self._pen)
        painter.drawPath(path)

    def set_orig_color(self):
        self._pen.setColor(self.orig_color)

    def hoverEnterEvent(self, event):
        self.orig_color = self._pen.color()
        self._pen.setColor(QColor("white"))
        self.update()
        event.accept()

    def hoverLeaveEvent(self, event):
        self.set_orig_color()
        self.update()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.id)
        event.accept()


class _NgonItemSignals(QObject):

    clicked = pyqtSignal(int)  # id


class NgonItem(QGraphicsItem):

    def __init__(self, id: int, n_points: int = 4, *points: QPointF | int):
        super().__init__()
        self.id = id
        self._pen = None
        self._brush = None
        self.n = n_points
        if len(points) == self.n * 2:
            self.points = [
                QPointF(points[i * 2], points[i * 2 + 1]) for i in range(self.n)
            ]
        elif len(points) == self.n:
            self.points = points
        self.points = self.get_sorted_points()
        self.setPen(QPen(QColor(255, 140, 0), 2))
        self.setBrush(QBrush(QColor(255, 165, 0, 128)))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setAcceptHoverEvents(True)
        self.signals = _NgonItemSignals()
        self.clicked = self.signals.clicked
        self.setEnabled(False)
        self.setZValue(self.zValue() + 1)

    def get_sorted_points(self):
        center_x = sum(p.x() for p in self.points) / 4
        center_y = sum(p.y() for p in self.points) / 4

        def angle_from_center(point):
            dx = point.x() - center_x
            dy = point.y() - center_y
            angle = math.atan2(dy, dx)
            return angle if angle >= 0 else angle + 2 * math.pi

        return sorted(self.points, key=angle_from_center)

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
        self.orig_color = pen.color()
        self.update(self.boundingRect())

    def brush(self):
        return self._brush

    def pen(self):
        return self._pen

    def setEnabled(self, enabled):
        if enabled:
            self.setZValue(self.zValue() + 1)
        else:
            self.setZValue(self.zValue() - 1)
        return super().setEnabled(enabled)

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
        points = self.get_sorted_points()
        if len(points) < 2:
            return path

        path.moveTo(points[0])
        for i in range(1, len(points)):
            path.lineTo(points[i])
        path.closeSubpath()
        return path

    def paint(self, painter, option, widget=None):
        """Отрисовывает четырёхугольник"""
        points = self.get_sorted_points()
        if len(points) != self.n:
            return

        path = QPainterPath()
        path.moveTo(points[0])
        for i in range(1, self.n):
            path.lineTo(points[i])
        path.closeSubpath()

        painter.setBrush(self._brush)
        painter.setPen(self._pen)
        painter.drawPath(path)

    def set_orig_color(self):
        pen_color, brush_color = self.orig_color
        self._pen.setColor(pen_color)
        self._brush.setColor(brush_color)

    def hoverEnterEvent(self, event):
        self.orig_color = (self._pen.color(), self._brush.color())
        self._pen.setColor(self._pen.color().lighter(150))
        self._brush.setColor(self._brush.color().lighter(150))
        self.update()
        event.accept()

    def hoverLeaveEvent(self, event):
        self.set_orig_color()
        self.update()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.id)
        return super().mousePressEvent(event)


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
