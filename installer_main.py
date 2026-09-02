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
        self.geometry("580x400")
        self._set_window_icon()
        self.selected = tk.StringVar(value=str(default_install_dir()))
        self.desktop_chk = tk.BooleanVar(value=False)
        self.start_chk = tk.BooleanVar(value=True)
        self.install_dir = installed_dir()
        self._page = 0
        self._build_ui()
        self._show_page(0)

    def _set_window_icon(self) -> None:
        """Set the window/taskbar icon from the bundled .ico (if present)."""
        base = getattr(sys, "_MEIPASS", str(Path.cwd()))
        for name in ("icon.ico", "app_icon.ico"):
            candidate = Path(base) / name
            if candidate.exists():
                try:
                    self.iconbitmap(str(candidate))
                    return
                except Exception:
                    continue

    def _build_ui(self) -> None:
        self.content = tk.Frame(self)
        self.content.pack(fill="both", expand=True)
        self.steps = [self._make_step1(), self._make_step2(), self._make_step3()]
        self._show_step_indicator()
        self.buttons_frame = tk.Frame(self)
        self.buttons_frame.pack(fill="x", side="bottom", padx=20, pady=(4, 12))
        self._show_buttons()

    def _make_step1(self) -> tk.Frame:
        f = tk.Frame(self.content)
        f.columnconfigure(0, weight=1)
        tk.Label(f, text=TITLE, font=("Segoe UI", 14, "bold"),
                 anchor="w").grid(row=0, column=0, sticky="w", padx=20, pady=(12, 4))
        if self.install_dir:
            tk.Label(f, text=(
                f"Discord Token Manager is already installed in:\n"
                f"{self.install_dir}\n\n"
                f"Choose an action below."
            ), font=("Segoe UI", 10), anchor="w", justify="left",
                wraplength=540).grid(row=1, column=0, sticky="w", padx=20, pady=(4, 0))
        else:
            tk.Label(f, text=(
                "This wizard will install Discord Token Manager on your computer.\n\n"
                "Click Next to continue."
            ), font=("Segoe UI", 10), anchor="w", justify="left",
                wraplength=540).grid(row=1, column=0, sticky="w", padx=20, pady=(4, 0))
        return f

    def _make_step2(self) -> tk.Frame:
        f = tk.Frame(self.content)
        f.columnconfigure(0, weight=1)
        tk.Label(f, text="Choose Install Location",
                 font=("Segoe UI", 12, "bold"),
                 anchor="w").grid(row=0, column=0, sticky="w", padx=20, pady=(12, 4))
        tk.Label(f, text="Select the folder where Discord Token Manager will "
                 "be installed:",
                 font=("Segoe UI", 10),
                 anchor="w").grid(row=1, column=0, sticky="w", padx=20)
        row = tk.Frame(f)
        row.grid(row=2, column=0, sticky="ew", padx=20, pady=(8, 12))
        row.columnconfigure(0, weight=1)
        tk.Entry(row, textvariable=self.selected, width=44).grid(
            row=0, column=0, sticky="ew")
        tk.Button(row, text="Browse…", command=self._choose).grid(
            row=0, column=1, padx=(8, 0))
        tk.Label(f, text="Additional Options:",
                 font=("Segoe UI", 10, "bold"),
                 anchor="w").grid(row=3, column=0, sticky="w", padx=20, pady=(4, 0))
        tk.Checkbutton(f, text="Create Start Menu shortcuts",
                       variable=self.start_chk).grid(
            row=4, column=0, sticky="w", padx=40)
        tk.Checkbutton(f, text="Create Desktop shortcut",
                       variable=self.desktop_chk).grid(
            row=5, column=0, sticky="w", padx=40, pady=(0, 8))
        return f

    def _make_step3(self) -> tk.Frame:
        f = tk.Frame(self.content)
        f.columnconfigure(0, weight=1)
        self.title_label = tk.Label(f, text="Installing…",
                                    font=("Segoe UI", 12, "bold"),
                                    anchor="w")
        self.title_label.grid(row=0, column=0, sticky="w", padx=20, pady=(12, 4))
        self.info = tk.Label(f, text="", font=("Segoe UI", 10),
                             anchor="w", justify="left", wraplength=540)
        self.info.grid(row=1, column=0, sticky="w", padx=20, pady=(4, 0))
        self.progress = ttk.Progressbar(f, length=520, mode="determinate")
        self.progress.grid(row=2, column=0, sticky="ew", padx=20, pady=(12, 4))
        self.status = tk.Label(f, text="", font=("Segoe UI", 9),
                               foreground="#666", anchor="w")
        self.status.grid(row=3, column=0, sticky="w", padx=20)
        return f

    def _show_step_indicator(self) -> None:
        frame = tk.Frame(self)
        frame.pack(fill="x", padx=20, pady=(12, 0))
        if self.install_dir:
            labels = ["Welcome", "Install"]
            self._step_pages = [0, 2]
        else:
            labels = ["Welcome", "Options", "Install"]
            self._step_pages = [0, 1, 2]
        self.step_dots = []
        for i, label in enumerate(labels):
            step_page = self._step_pages[i]
            color = "#2f81f7" if step_page <= self._page else "#bbb"
            dot = tk.Label(frame, text=f"● {label}", font=("Segoe UI", 9),
                           fg=color, padx=8)
            dot.pack(side="left")
            self.step_dots.append(dot)

    def _update_step_indicator(self) -> None:
        for i, dot in enumerate(self.step_dots):
            step_page = self._step_pages[i]
            color = "#2f81f7" if step_page <= self._page else "#bbb"
            dot.configure(fg=color)

    def _show_buttons(self) -> None:
        for w in self.buttons_frame.winfo_children():
            w.destroy()
        btn_style = {"font": ("Segoe UI", 10), "width": 12}
        if self._page == 0:
            tk.Button(self.buttons_frame, text="Cancel",
                      command=self.destroy, **btn_style).pack(side="right", padx=4)
            if self.install_dir:
                tk.Button(self.buttons_frame, text="Reinstall / Repair",
                          command=self._start_install, width=18,
                          **btn_style).pack(side="right", padx=4)
                tk.Button(self.buttons_frame, text="Uninstall",
                          bg="#d9534f", fg="white",
                          command=self._uninstall, **btn_style).pack(
                              side="right", padx=4)
            else:
                tk.Button(self.buttons_frame, text="Next  ▸",
                          bg="#2f81f7", fg="white",
                          command=lambda: self._show_page(1), **btn_style).pack(
                              side="right", padx=4)
        elif self._page == 1:
            tk.Button(self.buttons_frame, text="Cancel",
                      command=self.destroy, **btn_style).pack(side="right", padx=4)
            tk.Button(self.buttons_frame, text="Next  ▸",
                      bg="#2f81f7", fg="white",
                      command=lambda: self._start_install(), **btn_style).pack(
                          side="right", padx=4)
            tk.Button(self.buttons_frame, text="◂ Back",
                      command=lambda: self._show_page(0), **btn_style).pack(
                          side="right", padx=4)
        elif self._page == 2:
            tk.Button(self.buttons_frame, text="Cancel",
                      command=self.destroy, state="disabled",
                      **btn_style).pack(side="right", padx=4)

    def _show_page(self, page: int) -> None:
        self._page = page
        for i, step in enumerate(self.steps):
            step.grid_forget()
        self.steps[page].grid(row=0, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)
        self._update_step_indicator()
        self._show_buttons()

    def _choose(self) -> None:
        d = filedialog.askdirectory(initialdir=self.selected.get(),
                                    title="Choose install folder")
        if d:
            self.selected.set(d)

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        for w in self.buttons_frame.winfo_children():
            try:
                w.configure(state=state)
            except Exception:
                pass

    def _step(self, value: int) -> None:
        self.progress["value"] = value
        self.update_idletasks()

    def _start_install(self) -> None:
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
        self.info.configure(
            text=f"Installing Discord Token Manager to:\n{dest}")
        self._show_page(2)
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
        self._step(100)
        self.status.configure(text="Creating shortcuts…")
        try:
            make_shortcuts(dest, self.start_chk.get(), self.desktop_chk.get())
            _write_registry(dest, os.path.abspath(sys.executable))
        except Exception as exc:
            print(f"[installer] shortcuts/registry failed: {exc}")
        self.status.configure(text="Done")
        self.title_label.configure(text="Installation Complete!")
        self._set_busy(False)
        for w in self.buttons_frame.winfo_children():
            w.destroy()
        btn_style = {"font": ("Segoe UI", 10), "width": 12}
        tk.Button(self.buttons_frame, text="Close",
                  command=self.destroy, **btn_style).pack(side="right", padx=4)
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
        remove_shortcuts(dest or Path())
        _remove_registry()
        if dest:
            shutil.rmtree(dest, ignore_errors=True)
        self._set_busy(False)
        messagebox.showinfo("Setup", "Discord Token Manager was removed.")
        self.destroy()


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
