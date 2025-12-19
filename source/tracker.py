import cv2 as cv
from ultralytics import YOLO
from .instrument_manager import InstrumentManager
import numpy as np
from vidgear.gears import WriteGear
from pathlib import Path
from .track_objects import AbstractTrackObject

base = "materials/trained_models/"
AI_names = [
    base + "yolo11n-pose",  # 0
    base + "TSD",  # 1
    base + "curtains",  # 2
    base + "bills",  # 3
    base + "clothes",  # 4
    base + "cash_register",  # 5
    # base + "tags",  # 6
]


class Tracker:

    def __init__(
        self,
        data: list[AbstractTrackObject],
        video_out: WriteGear = None,
        tracker_name: str = None,
        options: list[bool] = None,
        verbose: bool = False,
        save_incidents: bool = False,
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
                if model_name == AI_names[2]:
                    self.models.append(YOLO(path, task="classify"))
                else:
                    self.models.append(YOLO(path))
            elif model_name == AI_names[2]:
                self.models.append("curtains")
            else:
                self.models.append(None)

        self.video_out = video_out
        self.verbose = verbose
        self.tracker_name = tracker_name or "bytetrack.yaml"
        if save_incidents:
            incidents_path = "materials/out/Incident.txt"
        else:
            incidents_path = None
        self.manager = InstrumentManager(
            incidents_path=incidents_path,
            video_name="1",
            initialize_curtains_model=options[2],
        )
        self.manager.load_data(data)

    def get_model_result(
        self, model, name, frame_in, frame_out
    ) -> tuple[np.ndarray, list]:

        data = {"people": [], "tsds": [], "curtains": [], "bills": [], "clothes": []}
        if name in [*AI_names[:2], AI_names[3]]:
            args = {"show": False, "persist": True, "tracker": self.tracker_name}
            if name == AI_names[3]:
                args["conf"] = 0.001
            results = model.track(frame_in, verbose=self.verbose, **args)

            for result in results:
                people_count = 0
                if name == AI_names[0]:
                    point_update_pack = []
                if result.boxes is not None and len(result.boxes) > 0:
                    boxes = result.boxes
                    ids = (
                        result.boxes.id.cpu().numpy()
                        if result.boxes.id is not None
                        else None
                    )

                    if boxes is None:
                        continue

                    for i, box in enumerate(boxes):

                        people_count += 1
                        x1, y1, x2, y2 = map(int, box.xyxy[0])

                        if name == AI_names[0]:
                            data["people"].append([[x1, y1], [x2, y2]])
                        if name == AI_names[1]:
                            data["tsds"].append([[x1, y1], [x2, y2]])
                        if name == AI_names[3]:
                            data["bills"].append([[x1, y1], [x2, y2]])
                        if name == AI_names[5]:
                            data["cash_registers"].append(
                                ([[x1, y1], [x2, y2]], model.names[int(box.cls[0])])
                            )
                        center = ((x1 + x2) // 2, (y1 + y2) // 2)

                        if ids is not None and name == AI_names[0]:
                            point_update_pack.append((int(ids[i]), center))

                if name == AI_names[0]:
                    frame_out = self.manager.update_draw_incidents_lamp(
                        frame_out, point_update_pack
                    )
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
        elif name == AI_names[2]:
            data["curtains"].extend(
                self.manager.get_detect_windows_states()  # (state, id)
            )  # state: {0: 'closed', 1: 'open'}
        elif name == AI_names[4]:
            results = model.predict(frame_in, stream=True, verbose=self.verbose)
            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    cls_id = int(box.cls[0])
                    cls_name = model.names[cls_id]
                    data["clothes"].append(([[x1, y1], [x2, y2]], cls_name))

        return frame_out, data

    def get_frame_to_writer(self, frame_in, frame_info: dict):
        frame_out = self.manager.draw_elements(frame_in)
        for key in ["people", "tsds", "bills"]:
            for p1, p2 in frame_info[key]:
                x1, y1 = p1
                x2, y2 = p2
                frame_out = cv.rectangle(frame_out, (x1, y1), (x2, y2), (0, 0, 255), 2)
                center = ((x1 + x2) // 2, (y1 + y2) // 2)
                frame_out = cv.circle(frame_out, center, 5, (0, 255, 0), -1)

        for (p1, p2), cloth_name in frame_info["clothes"]:
            x1, y1 = p1
            x2, y2 = p2
            frame_out = cv.rectangle(frame_in, (x1, y1), (x2, y2), (0, 0, 255), 2)
            center = ((x1 + x2) // 2, (y1 + y2) // 2)
            frame_out = cv.circle(frame_out, center, 5, (0, 255, 0), -1)

            frame_out = cv.putText(
                frame_out,
                cloth_name,
                (
                    max(0, int(np.mean([x1, x2]) - 30)),
                    max(0, min(y1, y2) - 15),
                ),
                cv.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 0, 0),
                2,
            )

        return frame_out

    def track_frame(
        self,
        frame: np.ndarray,
    ):
        frame_out = frame
        frame_info = {
            "people": [],
            "tsds": [],
            "curtains": [],
            "bills": [],
            "clothes": [],
            "cash_registers": [],
            # "tags": [],
        }
        for model, name in zip(self.models, AI_names):
            if model is None:
                continue
            frame_out, data = self.get_model_result(model, name, frame, frame_out)
            for key in frame_info.keys():
                frame_info[key].extend(data[key])

        frame_info["border_counts"] = self.manager.get_border_counts()

        if not self.video_out is None:
            frame_to_writer = self.get_frame_to_writer(frame_out.copy(), frame_info)
            self.video_out.write(frame_to_writer)

        return frame_out, frame_info
