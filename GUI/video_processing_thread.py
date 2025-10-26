from PyQt6.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker
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
        self._is_running = True
        self._lock = QMutex()

    def stop(self):
        with QMutexLocker(self._lock):
            self._is_running = False

    def is_running(self):
        with QMutexLocker(self._lock):
            return self._is_running

    def exit(self, returnCode=...):
        self._is_running = False
        return super().exit(returnCode)

    def quit(self):
        self._is_running = False
        return super().quit()

    def run(self):

        # video_out = cv.VideoWriter(
        #     f"materials/out/{id}.avi",
        #     fourcc=cv.VideoWriter_fourcc(*"XVID"),
        #     fps=20.0,
        #     frameSize=(self.shape[1], self.shape[0]),
        # )

        tracker = Tracker("yolo11n.pt", self.data, video_out=None)

        while self.video_cap.isOpened() and self._is_running:
            success, frame = self.video_cap.read()
            if not success:
                break

            frame = tracker.track_frame(frame)
            if self.show:
                self.frame_processed.emit(frame)
                # self.progress_bar.emit(i/len(self.video_cap))

        # video_out.release()
        self.processing_complete.emit()
