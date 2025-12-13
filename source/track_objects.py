import cv2 as cv
import numpy as np
from collections import deque
from shapely import LineString
from enum import Enum
from abc import ABC, abstractmethod

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from GUI.graphic_items import (
    NgonItem,
    ClickableLineItem,
    AbstractActivatedIdGraphicsItem,
)


def get_track_object_from_dict(data: dict):
    obj_type = data.pop("type")
    if obj_type == "border":
        return Border(**data)
    if obj_type == "detect_window":
        data.pop("accuracy")
        return DetectWindow(**data)


class AbstractTrackObject(ABC):
    track_type: str

    def __init__(self, room_id: int):
        self.room_id = room_id

    @abstractmethod
    def get_type(self) -> str:
        pass

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def get_qt_graphic_item(self) -> AbstractActivatedIdGraphicsItem:
        pass

    @abstractmethod
    def get_dict(self) -> dict:
        pass


def get_track_obj(obj_dict: dict) -> AbstractTrackObject:
    if obj_dict["type"] == "border":
        return Border(
            obj_dict["room_id"],
            obj_dict["accuracy"],
            obj_dict["point1"],
            obj_dict["point2"],
        )
    elif obj_dict["type"] == "detect_window":
        return DetectWindow(
            obj_dict["room_id"],
            *[obj_dict[f"point{i}"] for i in range(1, 5)],
        )
    else:
        raise RuntimeError("Got incorrect object dictionary")


class IncidentLevel(Enum):
    NO_INCIDENT = 0
    CUSTOMERS_2 = 1
    CUSTOMERS_MORE_THAN_2 = 2
    CLOSED_EMPTY = 3


class Border(AbstractTrackObject):
    accuracy: int
    incident_level: list[IncidentLevel]

    def __init__(
        self,
        room_id: int,
        accuracy: int,
        point1: tuple[float],
        point2: tuple[float],
    ):
        """in и out определяются по часовой стрелке от первой точки"""

        super().__init__(room_id)

        self.contain = 0
        self.accuracy = accuracy
        self.nearby = {}
        self.intersected = False
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

    def get_type(self):
        return "border"

    def get_dict(self) -> dict:
        return {
            "type": self.get_type(),
            "accuracy": self.accuracy,
            "point1": list(map(int, self.p1)),
            "point2": list(map(int, self.p2)),
            "room_id": self.room_id,
        }

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
        return (self.room_id, self.incident_level)

    def get_qt_graphic_item(self):
        return ClickableLineItem(self.room_id, *self.p1, *self.p2, parent=None)

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
            # cv.drawContours(
            #     im,
            #     [
            #         np.array([*self.field_in[1:3], *self.field_out[2:0:-1]])
            #         .reshape(-1, 1, 2)
            #         .astype(np.int32)
            #     ],
            #     -1,
            #     line_color,
            #     2,
            # ),
            str(self.contain),
            self.p1,
            cv.FONT_HERSHEY_COMPLEX,
            2,
            number_color,
            2,
        )


class DetectWindow(AbstractTrackObject):

    def __init__(
        self,
        room_id: int,
        point1: tuple[float],
        point2: tuple[float],
        point3: tuple[float],
        point4: tuple[float],
    ):

        super().__init__(room_id)

        self.xy_s = (
            list(map(int, point1))[:2],
            list(map(int, point2))[:2],
            list(map(int, point3))[:2],
            list(map(int, point4))[:2],
        )
        self.is_closed = 0

    def get_type(self):
        return "detect_window"

    def get_dict(self) -> dict:
        return {
            "type": self.get_type(),
            "accuracy": 20,
            **{f"point{i+1}": p for i, p in enumerate(self.xy_s)},
            "room_id": self.room_id,
        }

    def update(self, im: np.ndarray):

        return im
        # x1, y1, x2, y2 = (
        #     self.xy_s[0][0],
        #     self.xy_s[0][1],
        #     self.xy_s[1][0],
        #     self.xy_s[1][1],
        # )
        # roi = im[y1:y2, x1:x2]

        # if roi.size == 0:
        #     return

        # histSize = [8, 8, 8]  # Количество бинов для каждого канала
        # ranges = [0, 256, 0, 256, 0, 256]  # Диапазон значений для каждого канала
        # h_in = cv.calcHist([roi], [0, 1, 2], None, histSize, ranges)
        # h_ref = cv.calcHist([self.closed_ref], [0, 1, 2], None, histSize, ranges)

        # h_in = cv.normalize(h_in, h_in)
        # h_ref = cv.normalize(h_ref, h_ref)

        # self.is_closed = round(cv.compareHist(h_in, h_ref, cv.HISTCMP_BHATTACHARYYA), 3)

        # self.is_closed = np.sum(
        #     cv.matchTemplate(
        #         im[
        #             self.xyxy[0][1] : self.xyxy[1][1], self.xyxy[0][0] : self.xyxy[1][0]
        #         ],
        #         self.closed_ref,
        #         cv.TM_SQDIFF_NORMED,
        #     )
        # ) / (self.closed_ref.shape[0] * self.closed_ref.shape[1] * 255)
        # print(self.is_closed)

    def get_qt_graphic_item(self):
        data = []
        for x, y in self.xy_s:
            data.append(x)
            data.append(y)
        return NgonItem(self.room_id, 4, *data)

    def draw(self, im: np.ndarray):

        if self.is_closed:
            box_color = (0, 0, 255)  # red
        else:
            box_color = (0, 255, 73)  # green

        im = cv.rectangle(im, self.xy_s[0], self.xy_s[1], box_color, 2)
        im = cv.putText(
            im,
            str(self.is_closed),
            self.xy_s[1],
            cv.FONT_HERSHEY_COMPLEX,
            2,
            box_color,
            2,
        )
        return im
