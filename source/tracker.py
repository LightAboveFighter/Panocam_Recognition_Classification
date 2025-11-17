import cv2 as cv
from ultralytics import YOLO
from .instrument_manager import InstrumentManager
import numpy as np


AI_names = [f"materials/trained_models/yolo11n.pt"]


class Tracker:

    def __init__(
        self,
        data: list[dict],
        video_out: cv.VideoWriter = None,
        tracker_name: str = None,
        options: list[bool] = None,
        verbose=False,
    ):
        """
        Args:
            data: list of Borders and DetectWindows
            tracker_name: default is bytetrack.yaml
        """

        # self.model = YOLO(f"materials/trained_models/{model_name}")

        self.models = []
        for option, model_name in zip(
            options, [*AI_names, *([None] * (len(options) - len(AI_names)))]
        ):
            if option and (not model_name is None):
                self.models.append(YOLO(model_name))
            else:
                self.models.append(None)

        self.video_out = video_out
        self.verbose = verbose
        self.tracker_name = tracker_name or "bytetrack.yaml"
        self.manager = InstrumentManager(
            incidents_path="materials/out/Incident.txt", video_name="1"
        )
        self.manager.load_data(data)

    def get_model_result(self, model, name, frame_in, frame_out):

        if name == AI_names[0]:
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
                    classes = (
                        result.boxes.cls.cpu().numpy()
                        if result.boxes.id is not None
                        else None
                    )

                    point_update_pack = []
                    if boxes is None or classes is None:
                        continue

                    for i, inf in enumerate(zip(boxes, classes)):
                        box, cls = inf

                        # if model.names[cls] != "person":
                        #     continue
                        people_count += 1
                        x1, y1, x2, y2 = box.astype(int)

                        frame_out = cv.rectangle(
                            frame_out, (x1, y1), (x2, y2), (0, 0, 255), 2
                        )
                        center = ((x1 + x2) // 2, (y1 + y2) // 2)
                        frame_out = cv.circle(frame_out, center, 5, (0, 255, 0), -1)

                        frame_out = cv.putText(
                            frame_out,
                            f"({center[0]}, {center[1]})",
                            (x2 - 5, y2 - 5),
                            cv.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (255, 0, 0),
                            1,
                        )

                        if ids is not None:
                            point_update_pack.append((int(ids[i]), center))
                    self.manager.update(frame_out, point_update_pack)

                frame_out = self.manager.draw(frame_out)
                frame_out = cv.putText(
                    frame_out,
                    f"{people_count} people",
                    (10, 30),
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
        for model, name in zip(self.models, AI_names):
            if model is None:
                continue
            frame_out = self.get_model_result(model, name, frame, frame_out)

        if not self.video_out is None:
            self.video_out.write(frame_out)

        return frame_out

        # if show:
        #     cv.imshow(
        #         "YOLO11 Tracking",
        #         cv.resize(
        #             frame, (int(frame.shape[1] / 1.2), int(frame.shape[0] / 1.2))
        #         ),
        #     )
