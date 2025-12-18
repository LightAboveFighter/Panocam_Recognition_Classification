from PyQt6.QtWidgets import QDialog, QCheckBox
from dialog_default import Ui_Dialog
import yaml
from file_methods import rec_create_file
from options_lists import AI_options, additional_options


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
        self.ungrouped_check_boxes = []
        self.row = 0
        self.column = 0
        self.options_path = "GUI/user_files/last_checkbox_options.yaml"
        self.sum_check_box_exists = False

    def set_saved_check_boxes(self, add_sum_check_box: bool = True):
        self.add_check_box_variants(AI_options, add_sum_check_box)
        self.add_ungrouped_check_box_variants(additional_options)

        rec_create_file(self.options_path)
        with open(self.options_path, "r") as file:
            saved_options = yaml.safe_load(file)
            if not saved_options is None:
                self.set_grouped_check_box_states(saved_options[: len(AI_options)])
                self.set_ungrouped_check_box_states(saved_options[len(AI_options) :])

    def save_check_box_options(self, options: list[bool]):
        with open(self.options_path, "w") as file:
            yaml.safe_dump(options[1:], file)

    def set_grouped_check_box_states(self, states: list[bool]):
        if self.sum_check_box_exists:
            self.check_boxes[0].setChecked(all(states))
            start_index = 1
        else:
            start_index = 0
        for i, (check_box, state) in enumerate(
            zip(
                self.check_boxes[start_index:],
                [*states, *([False] * (len(self.check_boxes) - len(states)))],
            )
        ):
            check_box.setChecked(state)

    def set_ungrouped_check_box_states(self, states: list[bool]):
        for i, (check_box, state) in enumerate(
            zip(
                self.ungrouped_check_boxes,
                [*states, *([False] * (len(self.ungrouped_check_boxes) - len(states)))],
            )
        ):
            check_box.setChecked(state)

    def mark_all_grouped(self):
        state = self.check_boxes[0].isChecked()
        for check_box in self.check_boxes:
            check_box.blockSignals(True)
            check_box.setChecked(state)
            check_box.blockSignals(False)

    def update_mark_all_check_box(self):
        state = True
        for i in range(1, len(self.check_boxes)):
            state = state and self.check_boxes[i].isChecked()

        self.check_boxes[0].blockSignals(True)
        self.check_boxes[0].setChecked(state)
        self.check_boxes[0].blockSignals(False)

    def add_check_box_variants(
        self, var_list: list[str], add_sum_check_box: bool = False
    ):

        if len(var_list) > 0 and add_sum_check_box and (not self.sum_check_box_exists):
            self.sum_check_box_exists = True
            check_box = QCheckBox("Выбрать все", self)
            check_box.stateChanged.connect(self.mark_all_grouped)
            self.check_boxes.insert(0, check_box)
            self.ui.optional_grid.addWidget(check_box, self.row, self.column)

            self.column += 1

        for var in var_list:
            check_box = QCheckBox(var, self)
            check_box.stateChanged.connect(self.update_mark_all_check_box)
            self.check_boxes.append(check_box)
            self.ui.optional_grid.addWidget(check_box, self.row, self.column)

            self.column += 1
            self.column %= 3
            if self.column == 0:
                self.row += 1

    def add_ungrouped_check_box_variants(self, var_list: list[str]):
        """add check boxes, not connected with "choose all" check box"""

        for var in var_list:
            check_box = QCheckBox(var, self)
            self.ungrouped_check_boxes.append(check_box)
            self.ui.optional_grid.addWidget(check_box, self.row, self.column)

            self.column += 1
            self.column %= 3
            if self.column == 0:
                self.row += 1

    def get_answer(self):
        success = self.exec() == QDialog.DialogCode.Accepted
        check_box_options = [check_box.isChecked() for check_box in self.check_boxes]
        ungrouped_options = [
            check_box.isChecked() for check_box in self.ungrouped_check_boxes
        ]
        return success, check_box_options, ungrouped_options
