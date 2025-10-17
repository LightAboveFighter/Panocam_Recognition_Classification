from PyQt6.QtWidgets import QWidget, QDialog
from dialog_default import Ui_Dialog


class Dialog(QDialog):

    def __init__(self, parent=None, label: str = None):
        super().__init__(parent=parent)

        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # self.button_box.setText(left_button)
        # self.button_box.setText(right_button)
        self.ui.label.setText(label or "")
        self.ui.button_box.accepted.connect(self.accept)
        self.ui.button_box.rejected.connect(self.reject)

    def get_answer(self):
        return self.exec() == QDialog.DialogCode.Accepted
