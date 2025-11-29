from PyQt6.QtCore import QThread, pyqtSignal
import numpy as np
from vidgear.gears import CamGear, WriteGear
import time

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from source.tracker import Tracker
from source.track_objects import AbstractTrackObject


class VideoProcessingThread(QThread):

    frame_processed = pyqtSignal(np.ndarray, dict)
    processing_complete = pyqtSignal()

    def __init__(
        self,
        show: bool,
        path: str,
        shape: tuple[int],
        data: list[AbstractTrackObject],
        options: list[bool],
        parent=...,
    ):
        super().__init__(parent)
        self.path = path
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

        output_params = {
            "-input_framerate": 25,
            "-vcodec": "libx264",  # Кодек для MP4
        }
        writer = WriteGear(
            output=f"materials/out/{id(self)}.avi",
            compression_mode=False,
            **output_params,
        )
        try:
            tracker = Tracker(self.data, video_out=writer, options=self.options)
            _video_cap = CamGear(source=(self.path), logging=True).start()

            while self._is_running:

                frame = _video_cap.read()
                if frame is None:
                    success = False
                    for i in range(5):
                        time.sleep(0.2)
                        _video_cap.stop()
                        _video_cap = CamGear(source=(self.path), logging=True).start()
                        frame = _video_cap.read()
                        if not frame is None:
                            success = True
                            break
                    if not success:
                        break

                frame, frame_info = tracker.track_frame(frame)
                if self.show:
                    self.frame_processed.emit(frame, frame_info)
        except Exception as err:
            print(err)
            raise err

        finally:
            if not writer is None:
                writer.close()
                writer = None
            self.stop()
            if not _video_cap is None:
                _video_cap.stop()
                _video_cap = None
                print("Stopped ", self.path)
            self.processing_complete.emit()
