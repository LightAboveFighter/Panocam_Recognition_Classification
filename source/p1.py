from ultralytics import YOLO
import cv2 as cv
from borders import Borders
import torch
import yaml


def get_tracks(model_name: str, tracker_name: str, video_name: str, save=False) -> list:
    model = YOLO(f"materials/trained_models/{model_name}")
    results = model.track(
        source=f"materials/in/{video_name}",
        show=False,
        persist=True,
        tracker=tracker_name,
    )
    # if save:
    #     with open(f"materials/out/{video_name}.yaml", "w") as file:
    #         yaml.dump(results[:100], file)
    return results


# def load_tracks(video_name: str) -> list:
#     with open(f"{video_name}.yaml", "r") as file:
#         return yaml.load(file)


def save_tracked_video(model_name: str, video_name: str, tracks: list):

    fourcc = cv.VideoWriter_fourcc(*"FMP4")
    vid_in = cv.VideoCapture(f"materials/in/{video_name}")
    first_pict = vid_in.read()[1]
    borders = Borders("materials/in/borders.yaml")
    # in и out определяются по часовой стрелке от первой точки

    vid = cv.VideoWriter(
        f"materials/out/{video_name}",
        fourcc=fourcc,
        fps=20.0,
        frameSize=(first_pict.shape[1], first_pict.shape[0]),
    )
    vid_in.release()

    model_names = YOLO(f"materials/trained_models/{model_name}").names

    for result in tracks:
        im = result.orig_img

        people_count = 0
        if result.boxes is not None and len(result.boxes) > 0:
            boxes = result.boxes.xyxy.cpu().numpy()
            ids = result.boxes.id.cpu().numpy() if result.boxes.id is not None else None
            classes = (
                result.boxes.cls.cpu().numpy() if result.boxes.id is not None else None
            )

            for i, inf in enumerate(zip(boxes, classes)):
                box, cls = inf

                if model_names[cls] != "person":
                    continue
                people_count += 1
                x1, y1, x2, y2 = box.astype(int)

                im = cv.rectangle(im, (x1, y1), (x2, y2), (0, 0, 255), 2)
                center = ((x1 + x2) // 2, (y1 + y2) // 2)
                im = cv.circle(im, center, 5, (0, 255, 0), -1)

                im = cv.putText(
                    im,
                    f"({center[0]}, {center[1]})",
                    (x2 - 5, y2 - 5),
                    cv.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 0, 0),
                    1,
                )

                if ids is not None:
                    borders.update(int(ids[i]), center)

        im = borders.draw(im)
        im = cv.putText(
            im,
            f"{people_count} people",
            (10, 30),
            cv.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 0, 0),
            2,
        )
        vid.write(im)

    vid.release()
