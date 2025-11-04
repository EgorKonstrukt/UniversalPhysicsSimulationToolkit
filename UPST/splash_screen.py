import pathlib
import tkinter as tk
from tkinter import ttk
import threading
import time
import os
from PIL import Image, ImageTk


class SplashScreen:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg="black")
        self.logo_path = pathlib.Path(__file__).parent / "logo2.png"
        screen_w, screen_h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        win_w, win_h = 400, 200
        x, y = (screen_w - win_w) // 2, (screen_h - win_h) // 2
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")

        if self.logo_path and os.path.isfile(self.logo_path):
            try:
                img = Image.open(self.logo_path).convert("RGBA")
                img.thumbnail((120, 120), Image.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(img)
                logo_label = tk.Label(self.root, image=self.logo_img, bg="black")
                logo_label.pack(pady=(20, 5))
            except Exception:
                pass

        label = tk.Label(
            self.root,
            text="Loading UPST...",
            fg="#0af",
            bg="black",
            font=("Segoe UI", 16, "bold")
        )
        label.pack()

        progress = ttk.Progressbar(self.root, mode="indeterminate", length=300)
        progress.pack(pady=15)
        progress.start(10)

        self.root.update_idletasks()
        self.root.update()

    def destroy(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass


class FreezeWatcher:
    def __init__(self, threshold_sec=1.0, logo_path=None):
        self.threshold = threshold_sec
        self.logo_path = logo_path
        self.last_ping = time.perf_counter()
        self.splash = None
        self.lock = threading.Lock()
        self.paused = False
        self.pause_counter = 0

    def ping(self):
        with self.lock:
            self.last_ping = time.perf_counter()

    def pause(self):
        with self.lock:
            self.pause_counter += 1
            self.paused = True

    def resume(self):
        with self.lock:
            self.pause_counter = max(0, self.pause_counter - 1)
            if self.pause_counter == 0:
                self.paused = False
                self.last_ping = time.perf_counter()

    def _watch(self):
        while True:
            time.sleep(0.2)
            with self.lock:
                if self.paused:
                    if self.splash:
                        self.splash.destroy()
                        self.splash = None
                    continue
                elapsed = time.perf_counter() - self.last_ping
                if elapsed >= self.threshold:
                    if not self.splash:
                        self.splash = SplashScreen()
                else:
                    if self.splash:
                        self.splash.destroy()
                        self.splash = None

    def start(self):
        thread = threading.Thread(target=self._watch, daemon=True)
        thread.start()