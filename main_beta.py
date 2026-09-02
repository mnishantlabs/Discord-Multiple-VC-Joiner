"""Beta entry point: always launches the experimental Material 'Clean Desktop'
UI, regardless of CLI flags.

This mirrors ``main.py`` but hard-codes ``apply_beta()`` so the standalone beta
build never needs a ``--beta`` argument.
"""


def main() -> None:
    from ui.beta import apply_beta

    apply_beta()

    from ui.views.main_window import MainWindow

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
