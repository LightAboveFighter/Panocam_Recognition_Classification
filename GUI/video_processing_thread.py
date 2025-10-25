from PyQt6.QtCore import QThread, pyqtSignal
import cv2 as cv
import numpy as np

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from source.tracker import Tracker


class VideoProcessingThread(QThread):

    frame_processed = pyqtSignal(np.ndarray)
    processing_complete = pyqtSignal()

    def __init__(
        self,
        show: bool,
        video_cap: cv.VideoCapture,
        shape: tuple[int],
        data: list[dict],
        parent=...,
    ):
        super().__init__(parent)
        self.video_cap = video_cap
        self.shape = shape
        self.data = data
        self.show = show
        self.is_running = True

    def stop(self):
        self.is_running = False
        self.wait()

    def run(self):

        video_out = cv.VideoWriter(
            f"materials/out/1.avi",
            fourcc=cv.VideoWriter_fourcc(*"FMP4"),
            fps=20.0,
            frameSize=(self.shape[1], self.shape[0]),
        )

        tracker = Tracker("yolo11n.pt", self.data, video_out)

        while self.video_cap.isOpened():
            success, frame = self.video_cap.read()
            if not success:
                break

            frame = tracker.track_frame(frame)
            if self.show:
                self.frame_processed.emit(frame)
                # self.progress_bar.emit(i/len(self.video_cap))

        self.processing_complete.emit()
