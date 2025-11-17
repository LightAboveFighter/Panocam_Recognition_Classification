from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QSizePolicy, QPushButton
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from video_processing_thread import VideoProcessingThread
import cv2 as cv


class HidingButton(QPushButton):

    def __init__(self, text, parent=None):
        super().__init__(text, parent)

    def leaveEvent(self, a0):
        self.hide()
        return super().leaveEvent(a0)

    def hide(self):
        self.setMouseTracking(False)
        return super().hide()

    def focusOutEvent(self, a0):
        self.hide()
        return super().focusOutEvent(a0)


class ThreadedViewer(QGraphicsView):

    scene: QGraphicsScene
    clicked = pyqtSignal(int, int)  # row, column
    closed = pyqtSignal(int, int)  # row, column

    def __init__(
        self,
        row: int,
        column: int,
        parent=None,
    ):
        super().__init__(parent=parent)

        self.scene = QGraphicsScene()
        self.setScene(self.scene)
        self.video_processor = None
        self.row = row
        self.column = column
        self.button = HidingButton("Закрыть", self)
        self.button.hide()
        self.button.clicked.connect(self.close_on_button)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFrameStyle(0)

    def showEvent(self, event):
        """Обновление масштабирования при показе виджета"""
        super().showEvent(event)
        QTimer.singleShot(0, self.update_view)

    def update_view(self):
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event):
        self.update_view()
        return super().resizeEvent(event)

    def mouseMoveEvent(self, event):
        if self.button.isVisible() and not self.button.underMouse():
            self.button.hide()
        super().mouseMoveEvent(event)

    def leaveEvent(self, a0):
        self.button.hide()
        return super().leaveEvent(a0)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.row, self.column)
        elif event.button() == Qt.MouseButton.RightButton:
            right_side = self.rect().x() + self.rect().width()
            bottom_side = self.rect().y() + self.rect().height()
            self.button.move(
                QPoint(
                    min(
                        event.pos().x() - 5,
                        right_side - self.button.geometry().width() - 4,
                    ),
                    min(
                        event.pos().y() - 5,
                        bottom_side - self.button.geometry().height() - 4,
                    ),
                )
            )
            self.button.setMouseTracking(True)
            self.button.show()
        else:
            self.button.hide()

        return super().mousePressEvent(event)

    def change_frame(self, frame):
        image = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        height, width, channels = image.shape
        bytes_per_line = channels * width
        self.current_frame = QPixmap.fromImage(
            QImage(
                image.data,
                width,
                height,
                bytes_per_line,
                QImage.Format.Format_RGB888,
            )
        )
        self.scene.clear()
        self.scene.addPixmap(self.current_frame)
        self.scene.setSceneRect(
            0,
            0,
            self.current_frame.width(),
            self.current_frame.height(),
        )
        self.aspect_ratio = self.current_frame.height() / self.current_frame.width()

    def close_on_button(self):
        self.button.hide()
        self.clear_thread()
        self.closed.emit(self.row, self.column)

    def closeEvent(self, event):
        self.clear_thread()
        return super().closeEvent(event)

    def __del__(self):
        if hasattr(self, "video_processor") and self.video_processor is not None:
            self.clear_thread()

    def clear_thread(self, wait_time: int = 5000):  # Увеличили время ожидания
        if self.video_processor is None:
            return

        try:
            if self.video_processor.frame_processed:
                self.video_processor.frame_processed.disconnect()
            if self.video_processor.processing_complete:
                self.video_processor.processing_complete.disconnect(self.clear_thread)
        except Exception as e:
            print(f"Ошибка при отключении сигналов: {e}")

        if self.video_processor.isRunning():
            self.video_processor.stop()

            if not self.video_processor.wait(wait_time):
                print(
                    f"Поток не завершился за {wait_time}ms, принудительное завершение"
                )
                self.video_processor.terminate()
                self.video_processor.wait(1000)

        self.video_processor = None

    def start_video_thread(
        self, path: str, shape: tuple[int], data: list[dict], options: list[bool]
    ):

        self.video_processor = VideoProcessingThread(
            True,
            path=path,
            shape=shape,
            data=data,
            options=options,
            parent=self,
        )
        self.video_processor.setObjectName(
            f"VideoProcessingThread in ThreadedViewer id={self.row*10 + self.column}"
        )
        self.video_processor.frame_processed.connect(self.change_frame)
        self.video_processor.processing_complete.connect(self.clear_thread)
        self.video_processor.start()
