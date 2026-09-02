"""Entry point for the Discord Token Manager.

The old monolithic ``App`` class (importing ``Config``/``TokenStore`` from the
pre-refactor ``core.py``) was replaced by the composable ``MainWindow`` built
from views + services. This file is now just a thin launcher.
"""

from ui.views.main_window import MainWindow


def main() -> None:
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()