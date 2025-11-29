from PyQt6.QtGui import QColor, QBrush, QPen
from numpy.random import randint


def get_rand_brush_color(alpha: int = 0) -> tuple[QBrush, QPen]:
    r, g, b = randint(20, 255), randint(20, 255), randint(20, 255)
    pen = QPen(QColor(r - 10, g - 10, b - 10), 2)
    brush = QBrush(QColor(r, g, b, alpha))
    return brush, pen
