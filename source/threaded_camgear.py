from PyQt6.QtCore import QThread, QObject, pyqtSignal, QMutex, QMutexLocker, QTimer
from vidgear.gears import CamGear
from typing import Any
from datetime import datetime


RED = "\033[1;31m"
GREEN = "\033[32m"
FIOL = "\033[1;35m"
BLUE = "\033[1;36m"
WHITE = "\033[1;37m"
RESET = "\033[0m"


class _CamWorker(QObject):

    error = pyqtSignal(str)
    finished = pyqtSignal()
    initialization_succeed = pyqtSignal(bool)
    received_frame = pyqtSignal(object)

    def __init__(self, parent=...):
        super().__init__(parent=parent)
        self.init_succeeded = False
        self.mutex = QMutex()
        self.camgear = None

    def set_init_succeded(self):
        with QMutexLocker(self.mutex):
            self.init_succeeded = True

    def get_init_succeded(self):
        with QMutexLocker(self.mutex):
            return self.init_succeeded

    def init_cam(self, cam_options):
        """
        This constructor method initializes the object state and attributes of the CamGear class.

        Parameters:
            source (based on input): defines the source for the input stream.
            stream_mode (bool): controls the exclusive **Stream Mode** for handling streaming URLs.
            backend (int): selects the backend for OpenCV's VideoCapture class.
            colorspace (str): selects the colorspace of the input stream.
            logging (bool): enables/disables logging.
            time_delay (int): time delay (in sec) before start reading the frames.
            options (dict): provides ability to alter Source Tweak Parameters.
        """
        try:
            self.camgear = CamGear(**cam_options)
        except Exception as err:
            self.error.emit(str(err))
            self.camgear = None
            self.initialization_succeed.emit(False)
            raise err
        self.set_init_succeded()
        self.initialization_succeed.emit(True)

    def _read(self):
        """Tries to read the frame

        ------
        Emits frame with received_frame pyqtsignal
        """
        if not self.camgear:
            self.received_frame.emit(None)
            return
        try:
            frame = self.camgear.read()
        except Exception as err:
            self.error.emit(str(err))
            raise err
        self.received_frame.emit(frame)

    def stop(self):
        if self.camgear:
            self.camgear.stop()
        self.finished.emit()


class ThreadedCamGear(QObject):

    thread: QThread
    received_frame = pyqtSignal(object)
    init_succeed = pyqtSignal(bool)
    finished = pyqtSignal()
    _init_cam = pyqtSignal(dict)
    _read = pyqtSignal()
    _stop = pyqtSignal()

    def __init__(self, max_timeout: float = 5):
        """
        Parameters:
            max_timeout (float): max time to wait CamGear for initialization in seconds
        """
        super().__init__(parent=None)
        self.cam = None
        self.timeout = max_timeout
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._timeout)
        self._timer_type = 0

        self.thread = QThread(parent=None)
        self.thread.setObjectName(f"ThreadedCamGear.thread {id(self.thread)}")
        self.cam_worker = _CamWorker(parent=None)
        self.cam_worker.moveToThread(self.thread)

        self._read.connect(self.cam_worker._read)
        self._init_cam.connect(self.cam_worker.init_cam)
        self._stop.connect(self.cam_worker.stop)

        self.cam_worker.finished.connect(self.thread.quit)
        self.cam_worker.error.connect(self.error)
        self.cam_worker.initialization_succeed.connect(self._finalize_init_cam)
        self.cam_worker.received_frame.connect(self._finalize_read)

        self.thread.finished.connect(self.cam_worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._thread_finished)

        self._init_source = ""
        self.thread.start()

    def _thread_finished(self):
        self.finished.emit()

    def _timeout(self):
        if self._timer_type == 1:
            self._stop.emit()
            self.init_succeed.emit(False)
        if self._timer_type == 2:
            self.received_frame.emit(None)

        self._timer_type = 0

    def error(self, error_msg: str):
        print(error_msg)
        self._stop.emit()
        self.received_frame.emit(None)

    def _finalize_init_cam(self, success: bool):
        if self._timer_type != 1:
            return
        self.timer.stop()
        self._timer_type = 0
        source = self._init_source
        self._init_source = ""
        print(
            f"{GREEN}{datetime.now().strftime('%H:%M:%S')}{RESET} ::    {FIOL}ThreadedCamGear{RESET}    ::   {BLUE}INFO{RESET}   :: {WHITE}Trying init ThreadedCamGear with source: {source}{RESET}"
        )
        try:
            if (not success) and self.thread.isRunning():
                self._stop.emit()
                print(
                    f"{GREEN}{datetime.now().strftime('%H:%M:%S')}{RESET} ::    {FIOL}ThreadedCamGear{RESET}    ::   {RED}ERROR{RESET}  :: {WHITE}Failed init ThreadedCamGear with source: {source}{RESET}"
                )
                self.init_succeed.emit(False)
                return
        except Exception as err:
            print(
                f"{GREEN}{datetime.now().strftime('%H:%M:%S')}{RESET} ::    {FIOL}ThreadedCamGear{RESET}    ::   {RED}ERROR{RESET}  :: {WHITE}Failed init ThreadedCamGear with source: {source}{RESET}"
            )
            self.thread.quit()
            self.init_succeed.emit(False)
            raise err

        self.init_succeed.emit(True)

    def init_cam(
        self,
        source: Any = 0,
        stream_mode: bool = False,
        backend: int = 0,
        colorspace: str = None,
        logging: bool = False,
        time_delay: int = 0,
        **options: dict,
    ):
        """
        This constructor method tries to initialize the object state and attributes of the CamGear class.

        Success of the operation will be emitted within timeout with init_succeed(bool) pyqtsignal

        Parameters:
            source (based on input): defines the source for the input stream.
            stream_mode (bool): controls the exclusive **Stream Mode** for handling streaming URLs.
            backend (int): selects the backend for OpenCV's VideoCapture class.
            colorspace (str): selects the colorspace of the input stream.
            logging (bool): enables/disables logging.
            time_delay (int): time delay (in sec) before start reading the frames.
            options (dict): provides ability to alter Source Tweak Parameters.
        """
        self._init_source = source
        self._timer_type = 1
        self.timer.start(self.timeout * 10**3)
        self._init_cam.emit(
            {
                "source": source,
                "stream_mode": stream_mode,
                "backend": backend,
                "colorspace": colorspace,
                "logging": logging,
                "time_delay": time_delay,
                **options,
            }
        )

    def _finalize_read(self, frame):
        if self._timer_type != 2:
            return
        self.timer.stop()
        self._timer_type = 0
        self.received_frame.emit(frame)

    def read(self):
        """Try to read frame. Result will be emitted within timeout with received_frame pyqtsignal

        With failed initialization emits None"""
        self.timer.stop()
        if not self.thread.isRunning():
            self.received_frame.emit(None)
            return
        self._timer_type = 2
        self.timer.start(1000)
        self._read.emit()

    def stop(self):
        if self.thread.isRunning():
            self._stop.emit()
            self.thread.finished.connect(self.deleteLater)
        else:
            self.deleteLater()

    def isRunning(self):
        return self.thread.isRunning()

    def terminate(self):
        return self.thread.terminate()

    def wait(self, time: int) -> bool:
        return self.thread.wait(time)
