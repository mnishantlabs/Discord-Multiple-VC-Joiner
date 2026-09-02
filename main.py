"""Entry point for the Discord Token Manager.

The old monolithic ``App`` class (importing ``Config``/``TokenStore`` from the
pre-refactor ``core.py``) was replaced by the composable ``MainWindow`` built
from views + services. This file is now just a thin launcher.

Launched with ``--beta`` the window renders in the experimental Material "Clean
Desktop" style (see ``ui/beta/``). Beta only re-themes the existing interface;
the main tool's own code is unchanged.
"""

import sys


def main() -> None:
    # Apply the beta design layer before any UI module is imported, so every
    # view/dialog/widget resolves colors, fonts, and radii from the beta tokens.
    from ui.beta import apply_beta, is_beta_argv

    beta = is_beta_argv(sys.argv[1:])
    if beta:
        apply_beta()

    # Imported lazily so the swap above happens first.
    from ui.views.main_window import MainWindow

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
