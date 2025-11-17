from PyQt6.QtWidgets import QFileDialog
from pathlib import Path


def rec_create_file(path: str):
    filename_last_path = Path(path)
    if not filename_last_path.parent.exists():
        filename_last_path.parent.mkdir()
    if not filename_last_path.exists():
        filename_last_path.touch()


def get_user_path_save_last_dir(
    parent, mode: str, text: str, file_filter: str, last_file_path: str
) -> str:
    """
    Args:
        parent: QObject
        mode: "o" - user's path to open, "s" - user's path to save
        text: text insife file's menu
        file_filter: allowed file types
        last_file_path: where to save last dir
    """

    rec_create_file(last_file_path)
    with Path(last_file_path).open("r") as file:
        folder = file.readline()
    if len(folder) == 0:
        folder = Path.cwd()

    if mode == "o":
        user_file_path = QFileDialog.getOpenFileName(
            parent, text, str(folder), file_filter
        )[0]
    elif mode == "s":
        user_file_path = QFileDialog.getSaveFileName(
            parent, text, str(folder), file_filter
        )[0]

    if len(user_file_path) != 0:
        with Path(last_file_path).open("w") as file:
            file.write(str(Path(user_file_path).parent))

    return user_file_path
