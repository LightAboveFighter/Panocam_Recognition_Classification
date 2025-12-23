from .track_objects import (
    IncidentLevel,
    DetectWindow,
)
import yaml
import numpy as np
from datetime import datetime
import cv2 as cv
from pathlib import Path
from ultralytics import YOLO


class InstrumentManager:
    objs = dict[int, DetectWindow]

    def __init__(
        self,
        config_path: str = None,
        incidents_path: str = None,
        video_name: str = None,
        initialize_curtains_model: bool = False,
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
        self.curtains_model = None
        if initialize_curtains_model:
            path = "materials/trained_models/curtains"
            if Path(path + ".engine").exists():
                path = path + ".engine"
            else:
                path = path + ".onnx"
            self.curtains_model = YOLO(path, task="classify")

        if config_path is None:
            return

        with open(config_path, "r") as file:
            data = yaml.safe_load(file)
        self.load_data(data)

    def load_data(self, data: list[DetectWindow]):
        self.objs = {obj.room_id: obj for obj in data}

    def add_instrument(self, detect_window: DetectWindow):
        self.objs[detect_window.room_id] = detect_window

    def _update(self, im: np.ndarray, ids_points: list[tuple[int, tuple[float]]]):
        if not self.curtains_model is None:
            for region, id in self.get_detect_frames(im):
                self.objs[id].update(ids_points, self.curtains_model, region)
        else:
            for obj in self.objs.values():
                obj.update(ids_points, None, None)

    def write_incidents(self):

        for obj in self.objs.values():
            room_id, incident_levels = obj.get_incident()
            act_datetime = datetime.now()
            if obj.contain == 0 and obj.is_closed:
                incident_name = "Room is empty and closed"
                incident_levels[1] = IncidentLevel.CLOSED_EMPTY
            if incident_levels[0] == incident_levels[1]:
                continue
            if incident_levels[1] != IncidentLevel.CLOSED_EMPTY:
                incident_name = "People inside: "
                incident_name += str(obj.contain)

            self.incidents_file.write(
                f"{act_datetime.date()} {str(act_datetime.time())[:-4]} RoomID:{room_id} EventID:{self.incident_id} {incident_name} [{incident_levels[1].value}] {self.video_name}\n"
            )
            self.incident_id += 1

    def draw_elements(self, im: np.ndarray) -> np.ndarray:
        frame_out = im.copy()
        for obj in self.objs.values():
            frame_out = obj.draw(frame_out)

        return frame_out

    def update_draw_incidents_lamp(
        self, im: np.ndarray, ids_points: list[tuple[int, tuple[float]]]
    ) -> np.ndarray:

        incident_level = IncidentLevel.NO_INCIDENT
        self._update(im, ids_points)
        for obj in self.objs.values():
            incident_level = IncidentLevel(
                max(incident_level.value, obj.incident_level[1].value)
            )
            if obj is None:
                continue
            if obj.is_closed and obj.contain == 0:
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

    def _perspective_correct_quadrilateral(self, frame: np.ndarray, points: list[int]):
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
        t = [(obj.room_id, obj.contain) for obj in self.objs.values()]
        return t

    def get_detect_frames(self, frame):

        for obj in self.objs.values():
            if obj is None:
                continue
            yield self._perspective_correct_quadrilateral(frame, obj.xy_s), obj.room_id

    def get_detect_windows_states(self) -> list[tuple[bool, int]]:
        return [(not obj.is_closed, obj.room_id) for obj in self.objs.values()]
