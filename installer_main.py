"""Self-contained installer for Discord Token Manager.

Packaged by PyInstaller (setup.spec) as a single one-file EXE with the
portable onedir build embedded as data under ``appdata``. Pure stdlib +
tkinter so the installer stays small.

Flags:
    DiscordTokenManager-setup.exe          -> install wizard / reinstall / uninstall
    DiscordTokenManager-setup.exe --uninstall -> silent uninstall
"""

import os
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

APP_NAME = "DiscordTokenManager"
EXE_NAME = "DiscordTokenManager.exe"
TITLE = "Discord Token Manager – Setup"
UNINSTALL_KEY = (r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
                 r"\DiscordTokenManager")


def app_icon_ok(path: Path) -> bool:
    return path.exists() and path.is_dir()


def payload_dir() -> Path:
    base = getattr(sys, "_MEIPASS", str(Path.cwd()))
    return Path(base) / "appdata"


def default_install_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return Path(root) / "Programs" / APP_NAME


def start_menu_dir() -> Path:
    root = os.environ.get("APPDATA") or os.path.expanduser("~")
    return Path(root) / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def desktop_dir() -> Path:
    return Path(os.environ.get("USERPROFILE") or os.path.expanduser("~")) / "Desktop"


def installed_dir() -> Path | None:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
            value, _ = winreg.QueryValueEx(key, "InstallLocation")
        p = Path(value)
        if (p / EXE_NAME).exists():
            return p
    except OSError:
        pass
    return None


def _write_registry(install_dir: Path, setup_exe: str) -> None:
    import winreg
    app = str(install_dir / EXE_NAME)
    uninst = f'"{setup_exe}" --uninstall'
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ,
                          "Discord Token Manager")
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.0")
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ,
                          "mnishantlabs")
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, app + ",0")
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ,
                          str(install_dir))
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, uninst)
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)


def _remove_registry() -> None:
    import winreg
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except OSError:
        pass


def _shortcut(lnk: Path, target: str, description: str = "", icon: str = "") -> None:
    """Create a .lnk through WScript.Shell COM via PowerShell (no pywin32)."""
    lnk.parent.mkdir(parents=True, exist_ok=True)
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut({!r});"
          "$s.TargetPath={!r};").format(str(lnk), target)
    if icon:
        ps += "$s.IconLocation={!r};".format(icon)
    if description:
        ps += "$s.Description={!r};".format(description)
    ps += "$s.Save()"
    subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", ps],
                   check=True, capture_output=True)


def make_shortcuts(install_dir: Path, start_menu: bool, desktop: bool) -> None:
    app = str(install_dir / EXE_NAME)
    setup_exe = os.path.abspath(sys.executable)
    links = []
    if start_menu:
        links.append((start_menu_dir() / "Discord Token Manager.lnk",
                      app, "Launch Discord Token Manager", app + ",0"))
        links.append((start_menu_dir() / "Uninstall Discord Token Manager.lnk",
                      setup_exe, "Remove Discord Token Manager", ""))
    if desktop:
        links.append((desktop_dir() / "Discord Token Manager.lnk",
                      app, "Launch Discord Token Manager", app + ",0"))
    for lnk, target, desc, icon in links:
        try:
            _shortcut(lnk, target, desc, icon)
        except Exception as exc:
            print(f"[installer] shortcut failed: {lnk} ({exc})")


def remove_shortcuts(install_dir: Path) -> None:
    for lnk in (start_menu_dir() / "Discord Token Manager.lnk",
                start_menu_dir() / "Uninstall Discord Token Manager.lnk",
                desktop_dir() / "Discord Token Manager.lnk"):
        try:
            if lnk.exists():
                lnk.unlink()
        except OSError:
            pass


def ripple_cmd(install_dir: Path) -> None:
    """cmd needs an absolute single-string command on some systems."""
    app = install_dir / EXE_NAME
    try:
        subprocess.Popen([str(app)],
                         cwd=str(install_dir), shell=False)
    except Exception as exc:
        print(f"[installer] launch failed: {exc}")


class Installer(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(TITLE)
        self.resizable(False, False)
        self.geometry("560x340")
        self.selected = tk.StringVar(value=str(default_install_dir()))
        self.desktop_chk = tk.BooleanVar(value=False)
        self.start_chk = tk.BooleanVar(value=True)
        self.install_dir = installed_dir()
        self._build()
        self._route()

    def _build(self) -> None:
        pad = {"padx": 20, "pady": 8}
        tk.Label(self, text=TITLE, font=("Segoe UI", 14, "bold"),
                 anchor="w").pack(fill="x", **pad)
        self.info = tk.Label(self, text="", font=("Segoe UI", 10),
                             anchor="w", justify="left", wraplength=520)
        self.info.pack(fill="x", **pad)

        row = tk.Frame(self)
        row.pack(fill="x", **pad)
        tk.Entry(row, textvariable=self.selected, width=44).pack(
            side="left", ipady=2)
        tk.Button(row, text="Browse…", command=self._choose).pack(
            side="left", padx=(8, 0))

        self.opts = tk.Frame(self)
        self.opts.pack(fill="x", **pad)
        tk.Checkbutton(self.opts, text="Start Menu shortcuts",
                       variable=self.start_chk).pack(anchor="w")
        tk.Checkbutton(self.opts, text="Desktop shortcut",
                       variable=self.desktop_chk).pack(anchor="w")

        self.progress = ttk.Progressbar(self, length=520, mode="determinate")
        self.progress.pack(fill="x", **pad)

        self.status = tk.Label(self, text="", font=("Segoe UI", 9),
                               foreground="#666", anchor="w")
        self.status.pack(fill="x", **pad)

        self.buttons = tk.Frame(self)
        self.buttons.pack(fill="x", side="bottom", **pad)
        self.cancel = tk.Button(self.buttons, text="Close",
                                command=self.destroy)
        self.cancel.pack(side="right")

    def _route(self) -> None:
        if self.install_dir:
            self.info.configure(
                text=f"Discord Token Manager is already installed in:\n"
                     f"{self.install_dir}\n\n"
                     f"Choose an action below.")
            self.buttons = tk.Frame(self)
            self.buttons.pack(fill="x", pady=(4, 12))
            tk.Button(self.buttons, text="Uninstall", fg="white",
                      bg="#d9534f", command=self._uninstall).pack(side="right")
            tk.Button(self.buttons, text="Reinstall / repair", width=18,
                      command=self._install).pack(side="right", padx=(0, 8))
        else:
            self.info.configure(
                text=f"Installs Discord Token Manager to:\n{self.selected.get()}\n\n"
                     f"All data (tokens, settings) is stored in your user "
                     f"profile, so reinstalling never loses anything.")
            self.opts.pack()
            self.cancel.configure(text="Cancel")
            tk.Button(self.buttons, text="Install", width=14, bg="#2f81f7",
                      fg="white", command=self._install).pack(side="right", padx=(0, 8))

    def _choose(self) -> None:
        d = filedialog.askdirectory(initialdir=self.selected.get(),
                                    title="Choose install folder")
        if d:
            self.selected.set(d)

    def _step(self, value: int) -> None:
        self.progress["value"] = value
        self.update_idletasks()

    def _install(self) -> None:
        dest = Path(self.selected.get())
        try:
            dest.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("Setup", f"Cannot create folder:\n{dest}\n\n{exc}")
            return
        src = payload_dir()
        if not app_icon_ok(src):
            messagebox.showerror("Setup",
                                 "Payload missing. Please run from the "
                                 "official setup package.")
            return
        self._set_busy(True)
        files = [p for p in src.rglob("*")]
        total = max(len(files), 1)
        for i, f in enumerate(files):
            rel = f.relative_to(src)
            out = dest / rel
            if f.is_dir():
                out.mkdir(parents=True, exist_ok=True)
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, out)
            if i % max(1, total // 40) == 0:
                self._step(int(i / total * 100))
                self.status.configure(text=f"Copying {rel}…")
        # Belts and braces: keep a copy of the payload so a repaired install
        # that is missing _internal can be restored from the same volume.
        self._step(100)
        self.status.configure(text="Creating shortcuts…")
        try:
            make_shortcuts(dest, self.start_chk.get(), self.desktop_chk.get())
            _write_registry(dest, os.path.abspath(sys.executable))
        except Exception as exc:
            print(f"[installer] shortcuts/registry failed: {exc}")
        self.status.configure(text="Done")
        self._set_busy(False)
        if messagebox.askyesno("Setup",
                               "Installation complete.\n\nLaunch Discord "
                               "Token Manager now?"):
            ripple_cmd(dest)
        self.destroy()

    def _uninstall(self) -> None:
        if not messagebox.askyesno("Setup",
                                   "Remove Discord Token Manager and all its "
                                   "files?\n\nYour tokens and settings in "
                                   "your user profile are kept."):
            return
        dest = self.install_dir
        self._set_busy(True)
        self.status.configure(text="Removing…")
        remove_shortcuts(dest or Path())
        _remove_registry()
        if dest:
            shutil.rmtree(dest, ignore_errors=True)
        self._set_busy(False)
        messagebox.showinfo("Setup", "Discord Token Manager was removed.")
        self.destroy()

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for w in self.winfo_children():
            try:
                if isinstance(w, tk.Button):
                    w.configure(state=state)
            except Exception:
                pass


def main() -> None:
    if "--uninstall" in sys.argv:
        dest = installed_dir()
        if dest:
            remove_shortcuts(dest)
            _remove_registry()
            shutil.rmtree(dest, ignore_errors=True)
        return
    app = Installer()
    app.mainloop()


if __name__ == "__main__":
    main()