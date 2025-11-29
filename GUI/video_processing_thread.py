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
        path: str,
        shape: tuple[int],
        data: list[dict],
        options: list[bool],
        parent=...,
    ):
        super().__init__(parent)
        self.path = path
        self._video_cap = None
        self.shape = shape
        self.data = data
        self.show = show
        self.options = options
        self._is_running = True

    def stop(self):
        self._is_running = False

    def is_running(self):
        return self._is_running

    def exit(self, returnCode=...):
        self.stop()
        return super().exit(returnCode)

    def quit(self):
        self.stop()
        return super().quit()

    def run(self):

        # video_out = cv.VideoWriter(
        #     f"materials/out/{id}.avi",
        #     fourcc=cv.VideoWriter_fourcc(*"XVID"),
        #     fps=20.0,
        #     frameSize=(self.shape[1], self.shape[0]),
        # )
        try:
            tracker = Tracker(self.data, video_out=None, options=self.options)
            self._video_cap = cv.VideoCapture(self.path)

            while self._video_cap.isOpened() and self._is_running:

                success, frame = self._video_cap.read()
                if not success:
                    break

                frame = tracker.track_frame(frame)
                if self.show:
                    self.frame_processed.emit(frame)
        except Exception as err:
            print(err)
            pass
        finally:
            # video_out.release()
            self.stop()
            if not self._video_cap is None:
                self._video_cap.release()
            self.processing_complete.emit()
