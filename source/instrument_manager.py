from borders import Border, IncidentLevel
from detect_windows import DetectWindow
import yaml
import numpy as np
from datetime import datetime
import cv2 as cv


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
            incidents_path (str): file where logged incidents will be saved
            video_name (str): video's name, that will be used in logs
        """

        self.incident_id = 1
        if not incidents_path is None:
            self.incidents_file = open(incidents_path, "w")
            self.video_name = video_name or "video"
        else:
            self.incidents_file = None

        self.objs = {}
        if config_path is None:
            return

        with open(config_path, "r") as file:
            data = yaml.safe_load(file)

        self.load_data(data)

    def load_data(self, data: list[dict]):
        borders = [
            Border(
                border["room_id"],
                border["accuracy"],
                border["point1"],
                border["point2"],
            )
            for border in data
            if border["type"] == "border"
        ]

        i = 0
        for border in borders:
            window = None
            while i < len(data):
                w_data = data[i]
                if w_data["type"] == "detect_window" and w_data["room_id"] == border.id:
                    window = DetectWindow(w_data["point1"], w_data["point2"], None)
                    break
                i += 1

            self.objs[border.id] = (border, window)

    def add_closed_example(self, id: int, closed_example: np.ndarray):
        if not self.objs.get(id, False):
            return False
        self.objs[id][1].add_closed_example(closed_example)
        return True

    def add_instrument(self, border: Border, detect_window: DetectWindow):
        self.objs[border.id] = (border, detect_window)

    def update(self, im: np.ndarray, ids_points: list[tuple[int, tuple[float]]]):
        for obj in self.objs.values():
            obj[0].update(ids_points)
            if obj[1] is None:
                continue
            obj[1].update(im)

    def write_incedents(self):

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
            im = obj[0].draw(im)
            if obj[1] is None:
                continue
            im = obj[1].draw(im)
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
            self.write_incedents()

        lamp_color = (0, 255, 73)  # green
        if incident_level == IncidentLevel.CUSTOMERS_2:
            lamp_color = (0, 255, 255)  # yellow
        elif incident_level == IncidentLevel.CUSTOMERS_MORE_THAN_2:
            lamp_color = (0, 0, 255)  # red
        elif incident_level == IncidentLevel.CLOSED_EMPTY:
            lamp_color = (255, 0, 217)  # purple

        im = cv.circle(im, (im.shape[1] - 20, 20), 10, lamp_color, 17)

        return im
