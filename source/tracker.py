import cv2 as cv
from ultralytics import YOLO
from .instrument_manager import InstrumentManager
import numpy as np
from vidgear.gears import WriteGear
from pathlib import Path
from .track_objects import AbstractTrackObject

base = "materials/trained_models/"
AI_names = [base + "yolo11n-pose", base + "TSD"]


class Tracker:

    def __init__(
        self,
        data: list[AbstractTrackObject],
        video_out: WriteGear = None,
        tracker_name: str = None,
        options: list[bool] = None,
        verbose=False,
    ):
        """
        Args:
            data: list of Borders and DetectWindows
            tracker_name: default is bytetrack.yaml
        """

        self.models = []
        for option, model_name in zip(
            options, [*AI_names, *([None] * (len(options) - len(AI_names)))]
        ):
            if option and (not model_name is None):

                path = model_name + ".onnx"
                if Path(model_name + ".engine").exists():
                    path = model_name + ".engine"
                self.models.append(YOLO(path))
            else:
                self.models.append(None)

        self.video_out = video_out
        self.verbose = verbose
        self.tracker_name = tracker_name or "bytetrack.yaml"
        self.manager = InstrumentManager(
            incidents_path="materials/out/Incident.txt", video_name="1"
        )
        self.manager.load_data(data)

    def get_model_result(
        self, model, name, frame_in, frame_out
    ) -> tuple[np.ndarray, list]:

        data = {"people": [], "tsds": []}
        if name in AI_names[:2]:
            results = model.track(
                frame_in,
                show=False,
                persist=True,
                tracker=self.tracker_name,
                verbose=self.verbose,
            )

            for result in results:
                people_count = 0
                if result.boxes is not None and len(result.boxes) > 0:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    ids = (
                        result.boxes.id.cpu().numpy()
                        if result.boxes.id is not None
                        else None
                    )

                    point_update_pack = []
                    if boxes is None:
                        continue

                    for i, box in enumerate(boxes):

                        people_count += 1
                        x1, y1, x2, y2 = box.astype(int)

                        if name == AI_names[0]:
                            data["people"].append([[x1, y1], [x2, y2]])
                        if name == AI_names[1]:
                            data["tsds"].append([[x1, y1], [x2, y2]])

                        center = ((x1 + x2) // 2, (y1 + y2) // 2)

                        if ids is not None:
                            point_update_pack.append((int(ids[i]), center))
                    self.manager.update(frame_out, point_update_pack)

                frame_out = self.manager.draw(frame_out)
                if name == AI_names[0]:
                    frame_out = cv.putText(
                        frame_out,
                        f"{people_count} people",
                        (10, 30),
                        cv.FONT_HERSHEY_SIMPLEX,
                        1,
                        (255, 0, 0),
                        2,
                    )
        return frame_out, data

    def track_frame(
        self,
        frame: np.ndarray,
    ):
        frame_out = frame
        frame_info = {"people": [], "tsds": []}
        for model, name in zip(self.models, AI_names):
            if model is None:
                continue
            frame_out, data = self.get_model_result(model, name, frame, frame_out)
            for key in frame_info.keys():
                frame_info[key].extend(data[key])

        if not self.video_out is None:
            self.video_out.write(frame_out)

        return frame_out, frame_info
