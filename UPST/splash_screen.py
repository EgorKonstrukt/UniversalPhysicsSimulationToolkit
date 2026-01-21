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
        self.root.configure(bg="#0f0f15")
        self.logo_path = "sprites/logo2.png"
        screen_w, screen_h = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        win_w, win_h = 480, 240
        x, y = (screen_w - win_w) // 2, (screen_h - win_h) // 2
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.logo_label = None

        if os.path.isfile(self.logo_path):
            try:
                img = Image.open(self.logo_path).convert("RGBA")
                img.thumbnail((128, 128), Image.LANCZOS)
                bg = Image.new("RGB", img.size, "#0f0f15")
                bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
                logo_img = ImageTk.PhotoImage(bg)
                self.logo_label = tk.Label(self.root, image=logo_img, bg="#0f0f15")
                self.logo_label.image = logo_img
                self.logo_label.pack(pady=(24, 8))
            except Exception:
                pass

        title_label = tk.Label(
            self.root,
            text="Universal Physics Simulation Toolkit",
            fg="#00ccff",
            bg="#0f0f15",
            font=("Segoe UI Semibold", 13),
            wraplength=440,
            justify="center"
        )
        title_label.pack()

        progress = ttk.Progressbar(self.root, mode="indeterminate", length=360, style="Splash.Horizontal.TProgressbar")
        progress.pack(pady=(16, 0))
        progress.start(12)

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Splash.Horizontal.TProgressbar", troughcolor="#1a1a22", background="#007acc", thickness=4)

        self.root.update_idletasks()
        self.root.update()

    def destroy(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass


class FreezeWatcher:
    def __init__(self, threshold_sec=1.0):
        self.threshold = threshold_sec
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