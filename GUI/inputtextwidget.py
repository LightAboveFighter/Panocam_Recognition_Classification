from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent


class InputTextWidget(QTextEdit):
    enterKeyPressed = pyqtSignal(str)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.enterKeyPressed.emit(self.toPlainText())
        else:
            super().keyPressEvent(event)
