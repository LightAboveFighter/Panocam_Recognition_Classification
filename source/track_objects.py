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
    AbstractActivatedIdGraphicsItem,
)


def get_track_object_from_dict(data: dict):
    obj_type = data.pop("type")
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
    if obj_dict["type"] == "detect_window":
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


class DetectWindow(AbstractTrackObject):
    is_closed: bool

    def __init__(
        self,
        room_id: int,
        point1: tuple[float],
        point2: tuple[float],
        point3: tuple[float],
        point4: tuple[float],
        accuracy: int = 40,
    ):
        super().__init__(room_id)
        xy_s = (
            list(map(int, point1))[:2],
            list(map(int, point2))[:2],
            list(map(int, point3))[:2],
            list(map(int, point4))[:2],
        )

        center_x = sum(p[0] for p in xy_s) / 4
        center_y = sum(p[1] for p in xy_s) / 4

        sorted_p = sorted(
            xy_s, key=lambda p: np.atan2(p[1] - center_y, p[0] - center_x), reverse=True
        )

        shift = accuracy // 2

        self.outer_attention_field = (
            np.array(
                [
                    [sorted_p[0][0] - shift, sorted_p[0][1] - shift],
                    [sorted_p[1][0] + shift, sorted_p[1][1] - shift],
                    [sorted_p[2][0] + shift, sorted_p[2][1] + shift],
                    [sorted_p[3][0] - shift, sorted_p[3][1] + shift],
                ]
            )
            .reshape((-1, 1, 2))
            .astype(np.int32)
        )

        self.xy_s = sorted_p
        self.exact_attention_field = (
            np.array(self.xy_s).reshape((-1, 1, 2)).astype(np.int32)
        )

        self.borders = [
            LineString([sorted_p[i], sorted_p[(i + 1) % 4]]) for i in range(4)
        ]

        self.nearby = {}
        self.is_closed = False
        self.contain = 0

        self.incident_level = [IncidentLevel.NO_INCIDENT, IncidentLevel.NO_INCIDENT]
        self.intersected = False

    def get_type(self):
        return "detect_window"

    def get_dict(self) -> dict:
        return {
            "type": self.get_type(),
            "accuracy": 20,
            **{f"point{i+1}": p for i, p in enumerate(self.xy_s)},
            "room_id": self.room_id,
        }

    def __point_loc(self, point: tuple[float]) -> int:
        """return: 1 - point in field_in, -1 - point in field_out, 0 - point in field_surveillance"""
        point_tuple = (int(point[0]), int(point[1]))
        inn = cv.pointPolygonTest(self.exact_attention_field, point_tuple, False)
        outt = cv.pointPolygonTest(self.outer_attention_field, point_tuple, False)
        if inn >= 0:
            return -1
        elif outt >= 0:
            return 1
        else:
            return 0

    def under_surveillance(self, point: tuple[float]) -> bool:
        point_tuple = (int(point[0]), int(point[1]))
        in_outer = (
            cv.pointPolygonTest(self.outer_attention_field, point_tuple, False) == 1
        )
        return in_outer

    def people_in_view(self, ids_points: list[tuple[int, tuple[float]]]):
        for id, point in ids_points:
            if cv.pointPolygonTest(self.exact_attention_field, point, False) == 1:
                return True
        return False

    def __update(self, id: int, point: tuple[float]):
        if not self.nearby.get(id, False):
            self.nearby[id] = deque(maxlen=2)
        self.nearby[id].append(point)
        if len(self.nearby[id]) == 2:
            id_line = LineString(list(self.nearby[id]))
            intersections = 0
            for border in self.borders:
                if id_line.intersects(border):
                    intersections += 1
            if intersections == 1:
                self.contain += self.__point_loc(self.nearby[id][0])
                self.intersected = True

    def update(
        self,
        ids_points: list[tuple[int, tuple[float]]],
        model=None,
        region: np.ndarray = None,
    ):
        for id, point in ids_points:
            if not self.under_surveillance(point):
                self.nearby.pop(id, None)
            else:
                self.__update(id, point)
        self.incident_level[0] = self.incident_level[1]
        self.incident_level[1] = IncidentLevel(
            int(self.contain > 1) + int(self.contain > 2)
        )

        if self.people_in_view(ids_points):
            self.is_closed = False
            return region
        results = model.predict(region, task="classify", verbose=False)
        self.is_closed = not bool(results[0].probs.top1)

        return region

    def get_incident(self) -> tuple[int, tuple[IncidentLevel]]:
        return (self.room_id, self.incident_level)

    def get_qt_graphic_item(self):
        data = []
        for x, y in self.xy_s:
            data.append(x)
            data.append(y)
        return NgonItem(self.room_id, 4, *data)

    def draw(self, im: np.ndarray):

        box_color = (0, 0, 255)  # red
        if self.intersected:
            self.intersected = False
        elif not self.is_closed:
            box_color = (0, 255, 73)  # green

        im = cv.polylines(
            im,
            [np.array(self.xy_s).reshape((-1, 1, 2))],
            True,
            box_color,
            2,
        )

        return cv.putText(
            im,
            str(self.contain),
            self.xy_s[0],
            cv.FONT_HERSHEY_COMPLEX,
            2,
            box_color,
            2,
        )
