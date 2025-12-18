from .track_objects import (
    Border,
    IncidentLevel,
    DetectWindow,
    AbstractTrackObject,
)
import yaml
import numpy as np
from datetime import datetime
import cv2 as cv
from pathlib import Path


class InstrumentManager:
    objs = dict[int, tuple[Border, DetectWindow]]

    def __init__(
        self,
        config_path: str = None,
        incidents_path: str = None,
        video_name: str = None,
    ):
        """
        Args:
            config_path (str): from where lines will be loaded. You also can load data lated with load_data() method
            incidents_path (str): file where logged incidents will be saved. If None: won't be saved
            video_name (str): video's name, that will be used in logs
        """

        self.incident_id = 1

        if not incidents_path is None:
            path = Path(incidents_path)
            if not path.parent.exists():
                path.parent.mkdir()
            self.incidents_file = path.open("w")
            self.video_name = video_name or "video"
        else:
            self.incidents_file = None

        self.objs = {}
        if config_path is None:
            return

        with open(config_path, "r") as file:
            data = yaml.safe_load(file)

        self.load_data(data)

    def load_data(self, data: list[AbstractTrackObject]):
        for j in range(len(data)):
            if data[j].get_type() != "border":
                continue
            i = 0
            # объединяем окна и границы с одинаковыми айди
            # мы можем иметь линию без окна, но не наоборот
            window = None
            while i < len(data):
                if (
                    data[i].get_type() == "detect_window"
                    and data[i].room_id == data[j].room_id
                ):
                    window = data[i]
                i += 1
                if i == j:
                    i += 1

            self.objs[data[j].room_id] = (data[j], window)

    def add_instrument(self, border: Border, detect_window: DetectWindow):
        self.objs[border.room_id] = (border, detect_window)

    def update(self, im: np.ndarray, ids_points: list[tuple[int, tuple[float]]]):
        for obj in self.objs.values():
            obj[0].update(ids_points)
            if obj[1] is None:
                continue
            obj[1].update(im)

    def write_incidents(self):

        for obj in self.objs.values():
            room_id, incident_levels = obj[0].get_incident()
            act_datetime = datetime.now()
            if (not obj[1] is None) and obj[0].contain == 0 and obj[1].is_closed > 0.7:
                incident_name = "Room is empty and closed"
                incident_levels[1] = IncidentLevel.CLOSED_EMPTY
            if incident_levels[0] == incident_levels[1]:
                continue
            if incident_levels[1] != IncidentLevel.CLOSED_EMPTY:
                incident_name = "People inside: "
                incident_name += str(obj[0].contain)

            self.incidents_file.write(
                f"{act_datetime.date()} {str(act_datetime.time())[:-4]} RoomID:{room_id} EventID:{self.incident_id} {incident_name} [{incident_levels[1].value}] {self.video_name}\n"
            )
            self.incident_id += 1

    def draw(self, im: np.ndarray) -> np.ndarray:

        incident_level = IncidentLevel.NO_INCIDENT
        for obj in self.objs.values():
            incident_level = IncidentLevel(
                max(incident_level.value, obj[0].incident_level[1].value)
            )
            if obj[1] is None:
                continue
            if obj[1].is_closed > 0.7 and obj[0].contain == 0:
                incident_level = IncidentLevel.CLOSED_EMPTY
                break
        if not self.incidents_file is None:
            self.write_incidents()

        lamp_color = (0, 255, 73)  # green
        if incident_level == IncidentLevel.CUSTOMERS_2:
            lamp_color = (0, 255, 255)  # yellow
        elif incident_level == IncidentLevel.CUSTOMERS_MORE_THAN_2:
            lamp_color = (0, 0, 255)  # red
        elif incident_level == IncidentLevel.CLOSED_EMPTY:
            lamp_color = (255, 0, 217)  # purple

        im = cv.circle(im, (im.shape[1] - 20, 20), 10, lamp_color, 17)

        return im

    def _perspective_correct_quadrilateral(self, frame, points):
        """
        Extract quadrilateral region and perform perspective correction to get a straight rectangle
        """
        src_pts = np.array(points, dtype=np.float32)
        width = max(
            np.linalg.norm(src_pts[0] - src_pts[1]),
            np.linalg.norm(src_pts[2] - src_pts[3]),
        )
        height = max(
            np.linalg.norm(src_pts[1] - src_pts[2]),
            np.linalg.norm(src_pts[3] - src_pts[0]),
        )

        dst_pts = np.array(
            [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
            dtype=np.float32,
        )
        matrix = cv.getPerspectiveTransform(src_pts, dst_pts)
        result = cv.warpPerspective(frame, matrix, (int(width), int(height)))

        return result

    def get_border_counts(self):
        return [(obj[0].room_id, obj[0].contain) for obj in self.objs.values()]

    def get_detect_frames(self, frame):

        for obj in self.objs.values():
            if obj[1] is None:
                continue
            yield self._perspective_correct_quadrilateral(frame, obj[1].xy_s), obj[
                1
            ].room_id
