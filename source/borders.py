import cv2 as cv
import numpy as np
import yaml
from collections import deque
from shapely import LineString
from enum import Enum


class IncidentLevel(Enum):
    NO_INCIDENT = 0
    CUSTOMERS_2 = 1
    CUSTOMERS_MORE_THAN_2 = 2
    CLOSED_EMPTY = 3


class Border:
    accuracy: int
    incident_level: list[IncidentLevel]

    def __init__(
        self, room_id: int, accuracy: int, point1: tuple[float], point2: tuple[float]
    ):
        """in и out определяются по часовой стрелке от первой точки"""
        self.contain = 0
        self.nearby = {}
        self.intersected = False
        self.id = room_id
        self.incident_level = [IncidentLevel.NO_INCIDENT, IncidentLevel.NO_INCIDENT]

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

    def under_surveillance(self, point: tuple[float]) -> bool:
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
        self.nearby[id].append(point)
        if len(self.nearby[id]) == 2:
            id_line = LineString(list(self.nearby[id]))
            if id_line.intersects(self.border):
                self.contain += self.__point_loc(self.nearby[id][0])
                self.intersected = True

    def update(self, ids_points: list[tuple[int, tuple[float]]]):
        for id, point in ids_points:
            if not self.under_surveillance(point):
                self.nearby.pop(id, None)
            else:
                self.__update(id, point)
        self.incident_level[0] = self.incident_level[1]
        self.incident_level[1] = IncidentLevel(
            int(self.contain > 1) + int(self.contain > 2)
        )

    def get_incident(self) -> tuple[int, tuple[IncidentLevel]]:
        return (self.id, self.incident_level)

    def draw(self, im) -> np.ndarray:
        if self.intersected:
            line_color = (0, 0, 255)  # red
            self.intersected = False
        else:
            line_color = (0, 255, 73)  # green

        if self.contain < 0:
            number_color = (0, 0, 0)  # black
        elif self.contain < 2:
            number_color = (0, 255, 73)  # green
        elif self.contain == 2:
            number_color = (0, 255, 255)  # yellow
        else:
            number_color = (0, 0, 255)  # red

        return cv.putText(
            cv.line(im, self.p1, self.p2, line_color, 2),
            str(self.contain),
            self.p1,
            cv.FONT_HERSHEY_COMPLEX,
            2,
            number_color,
            2,
        )
