from ultralytics import YOLO
import cv2 as cv
from borders import Borders


def track_video(
    model_name: str,
    tracker_name: str,
    video: cv.VideoCapture,
    borders: Borders,
    new_video: cv.VideoWriter = None,
    show: bool = False,
):

    model = YOLO(f"materials/trained_models/{model_name}")

    while video.isOpened():

        success, frame = video.read()
        if not success:
            break

        results = model.track(
            frame,
            show=False,
            persist=True,
            tracker=tracker_name,
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
                for i, inf in enumerate(zip(boxes, classes)):
                    box, cls = inf

                    if model.names[cls] != "person":
                        continue
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
                borders.update(point_update_pack)

            frame = borders.draw(frame)
            frame = cv.putText(
                frame,
                f"{people_count} people",
                (10, 30),
                cv.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 0, 0),
                2,
            )
            if not new_video is None:
                new_video.write(frame)

        if show:
            cv.imshow(
                "YOLO11 Tracking",
                cv.resize(
                    frame, (int(frame.shape[1] / 1.2), int(frame.shape[0] / 1.2))
                ),
            )

            if cv.waitKey(1) & 0xFF == ord("q"):
                break


model_name = "yolo11n.pt"
video_name = "Примерочные_2_этаж_двое_в_кабинке_ПЛОХО.avi"
tracker_name = "bytetrack.yaml"

video_in = cv.VideoCapture(f"materials/in/{video_name}")
first_pict = video_in.read()[1]
borders = Borders("materials/in/borders.yaml", "materials/out/Incident.txt", video_name)
# in и out определяются по часовой стрелке от первой точки

video_out = cv.VideoWriter(
    f"materials/out/{video_name}",
    fourcc=cv.VideoWriter_fourcc(*"FMP4"),
    fps=20.0,
    frameSize=(first_pict.shape[1], first_pict.shape[0]),
)


track_video(model_name, tracker_name, video_in, borders, video_out, True)

video_out.release()
video_in.release()
cv.destroyAllWindows()
