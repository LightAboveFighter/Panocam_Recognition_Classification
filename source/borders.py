import cv2 as cv
import numpy as np
import yaml
from collections import deque
from shapely import LineString


class Border:

    def __init__(self, accuracy: int, point1: tuple[float], point2: tuple[float]):
        self.contain = 0
        self.nearby = {}

        self.p1 = np.array(point1)
        self.p2 = np.array(point2)

        vect = self.p2 - self.p1
        self.border = LineString([self.p1, self.p2])
        vect = vect / np.linalg.norm(vect)

        self.vect_perp = np.array([-vect[1], vect[0]])

        self.field_in = (
            np.array(
                [
                    self.p1,
                    self.p1 + accuracy * self.vect_perp,
                    self.p2 + accuracy * self.vect_perp,
                    self.p2,
                ]
            )
            .reshape((-1, 1, 2))
            .astype(np.int32)
        )

        self.field_out = (
            np.array(
                [
                    self.p1,
                    self.p1 - accuracy * self.vect_perp,
                    self.p2 - accuracy * self.vect_perp,
                    self.p2,
                ]
            )
            .reshape((-1, 1, 2))
            .astype(np.int32)
        )

    def under_surveillance(self, point) -> bool:
        point_tuple = (int(point[0]), int(point[1]))
        return (cv.pointPolygonTest(self.field_in, point_tuple, False) == 1) or (
            cv.pointPolygonTest(self.field_out, point_tuple, False) == 1
        )

    def __point_loc(self, point: tuple[float]) -> int:
        """return: 1 - point in field_in, -1 - point in field_out, 0 - point in field_surveillance"""
        point_tuple = (int(point[0]), int(point[1]))
        if cv.pointPolygonTest(self.field_in, point_tuple, False) >= 0:
            return 1
        elif cv.pointPolygonTest(self.field_out, point_tuple, False) >= 0:
            return -1
        else:
            return 0

    def __update(self, id: int, point: tuple[float]):
        if not self.nearby.get(id, False):
            self.nearby[id] = deque(maxlen=2)
            # self.nearby[id].put(0)
        self.nearby[id].append(point)
        if len(self.nearby[id]) == 2:
            id_line = LineString(list(self.nearby[id]))
            if id_line.intersects(self.border):
                self.contain += self.__point_loc(self.nearby[id][0])

    def update(self, id: int, point: tuple[float]):
        if not self.under_surveillance(point):
            self.nearby.pop(id, None)
            return
        self.__update(id, point)

    def draw(self, im) -> np.ndarray:
        return cv.putText(
            cv.line(im, self.p1, self.p2, (255, 0, 0), 2),
            str(self.contain),
            self.p1,
            cv.FONT_HERSHEY_COMPLEX,
            2,
            (255, 0, 0),
            2,
        )


class Borders:
    borders: list[Border]

    def __init__(self, config_path: str):

        with open(config_path, "r") as file:
            data = yaml.safe_load(file)

        self.borders = [
            Border(border["accuracy"], border["point1"], border["point2"])
            for border in data
        ]

    def update(self, id: int, point: tuple[float]):
        for border in self.borders:
            border.update(id, point)

    def draw(self, im) -> np.ndarray:
        for border in self.borders:
            im = border.draw(im)
        return im
