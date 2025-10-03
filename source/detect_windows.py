import numpy as np
import cv2 as cv


class DetectWindow:

    def __init__(
        self, point1: tuple[float], point2: tuple[float], closed_example: np.ndarray
    ):

        self.xyxy = (list(map(int, point1))[:2], list(map(int, point2))[:2])
        self.closed_ref = None or closed_example
        self.is_closed = 0

    def add_closed_example(self, closed_example: np.ndarray):
        self.closed_ref = closed_example

    def update(self, im: np.ndarray):
        if self.closed_ref is None:
            return

        x1, y1, x2, y2 = (
            self.xyxy[0][0],
            self.xyxy[0][1],
            self.xyxy[1][0],
            self.xyxy[1][1],
        )
        roi = im[y1:y2, x1:x2]

        if roi.size == 0:
            return

        histSize = [8, 8, 8]  # Количество бинов для каждого канала
        ranges = [0, 256, 0, 256, 0, 256]  # Диапазон значений для каждого канала
        h_in = cv.calcHist([roi], [0, 1, 2], None, histSize, ranges)
        h_ref = cv.calcHist([self.closed_ref], [0, 1, 2], None, histSize, ranges)

        h_in = cv.normalize(h_in, h_in)
        h_ref = cv.normalize(h_ref, h_ref)

        self.is_closed = round(cv.compareHist(h_in, h_ref, cv.HISTCMP_BHATTACHARYYA), 3)

        # self.is_closed = np.sum(
        #     cv.matchTemplate(
        #         im[
        #             self.xyxy[0][1] : self.xyxy[1][1], self.xyxy[0][0] : self.xyxy[1][0]
        #         ],
        #         self.closed_ref,
        #         cv.TM_SQDIFF_NORMED,
        #     )
        # ) / (self.closed_ref.shape[0] * self.closed_ref.shape[1] * 255)
        # print(self.is_closed)

    def draw(self, im: np.ndarray):

        if self.is_closed:
            box_color = (0, 0, 255)  # red
        else:
            box_color = (0, 255, 73)  # green

        im = cv.rectangle(im, self.xyxy[0], self.xyxy[1], box_color, 2)
        im = cv.putText(
            im,
            str(self.is_closed),
            self.xyxy[1],
            cv.FONT_HERSHEY_COMPLEX,
            2,
            box_color,
            2,
        )
        return im
