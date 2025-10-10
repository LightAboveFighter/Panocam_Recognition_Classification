import cv2 as cv
from edit_config_class import Ui_Form
from PyQt6.QtWidgets import QGraphicsScene, QWidget
from PyQt6.QtGui import QImage, QPixmap


class EditConfigWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.scene = QGraphicsScene()
        self.ui = Ui_Form()
        self.ui.setupUi(self)
        self.ui.frame_viewer.setScene(self.scene)
        self.video_cap = None

    def set_path(self, path: str):
        self.video_cap = cv.VideoCapture(path)
        success, im = self.video_cap.read()
        if success:
            self.change_frame(im)
        else:
            self.video_cap.release()
            self.video_cap = None
        return success

    def change_frame(self, frame):

        image = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        height, width, channels = image.shape
        bytes_per_line = channels * width
        self.scene.addPixmap(
            QPixmap.fromImage(
                QImage(
                    image.data,
                    width,
                    height,
                    bytes_per_line,
                    QImage.Format.Format_RGB888,
                )
            )
        )

    # def resizeEvent()
