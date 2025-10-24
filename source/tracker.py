import cv2 as cv
from ultralytics import YOLO
from .instrument_manager import InstrumentManager
import numpy as np


class Tracker:

    def __init__(
        self,
        model_name,
        data: list[dict],
        video_out: cv.VideoWriter = None,
        tracker_name: str = None,
        verbose=False,
    ):
        """
        Args:
            data: list of Borders and DetectWindows
            tracker_name: default is bytetrack.yaml
        """

        self.model = YOLO(f"materials/trained_models/{model_name}")
        self.video_out = video_out
        self.verbose = verbose
        self.tracker_name = tracker_name or "bytetrack.yaml"
        self.manager = InstrumentManager(
            incidents_path="materials/out/Incident.txt", video_name="1"
        )
        self.manager.load_data(data)

    def track_frame(
        self,
        frame: np.ndarray,
    ):

        results = self.model.track(
            frame,
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

                    frame = cv.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    center = ((x1 + x2) // 2, (y1 + y2) // 2)
                    frame = cv.circle(frame, center, 5, (0, 255, 0), -1)

                    frame = cv.putText(
                        frame,
                        f"({center[0]}, {center[1]})",
                        (x2 - 5, y2 - 5),
                        cv.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        (255, 0, 0),
                        1,
                    )

                    if ids is not None:
                        point_update_pack.append((int(ids[i]), center))
                self.manager.update(frame, point_update_pack)

            frame = self.manager.draw(frame)
            frame = cv.putText(
                frame,
                f"{people_count} people",
                (10, 30),
                cv.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 0, 0),
                2,
            )
            if not self.video_out is None:
                self.video_out.write(frame)

        return frame
        # if show:
        #     cv.imshow(
        #         "YOLO11 Tracking",
        #         cv.resize(
        #             frame, (int(frame.shape[1] / 1.2), int(frame.shape[0] / 1.2))
        #         ),
        #     )
