from PyQt6.QtWidgets import QDialog, QCheckBox
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
        self.check_boxes = []

    def set_check_box_states(self, states: list[bool]):
        for check_box, state in zip(
            self.check_boxes, [*states, [False] * (len(self.check_boxes) - len(states))]
        ):
            check_box.setChecked(state)

    def set_check_box_variants(self, var_list: list[str]):

        row = 0
        column = 0
        for var in var_list:
            check_box = QCheckBox(var, self)
            self.check_boxes.append(check_box)
            self.ui.optional_grid.addWidget(check_box, row, column)

            column += 1
            column %= 3
            if column == 0:
                row += 1

    def get_answer(self):
        answer = self.exec() == QDialog.DialogCode.Accepted
        check_box_options = [check_box.isChecked() for check_box in self.check_boxes]
        return answer, check_box_options
