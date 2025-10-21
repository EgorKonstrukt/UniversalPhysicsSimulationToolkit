import time
import threading
import collections
import pygame
import pygame_gui
import psutil
# import pynvml


class GameSystemMonitor:

    def __init__(self, manager, process_name, max_samples=120, refresh_rate=0.5):
        self.manager = manager
        self.process_name = process_name
        self.max_samples = max_samples
        self.refresh_rate = refresh_rate
        self.running = True
        self.data = {
            'cpu': collections.deque(maxlen=max_samples),
            'ram': collections.deque(maxlen=max_samples),
            'gpu_util': collections.deque(maxlen=max_samples),
            'gpu_mem': collections.deque(maxlen=max_samples),
            'net_sent': collections.deque(maxlen=max_samples),
            'net_recv': collections.deque(maxlen=max_samples),
        }
        self.surface_size = (500, 200)
        self.graph_surface = pygame.Surface(self.surface_size, pygame.SRCALPHA)
        self.font = pygame.font.SysFont("Consolas", 14)
        # self._init_gpu()
        # self._find_process()
        # self._start_thread()

