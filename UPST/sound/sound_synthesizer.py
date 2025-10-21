import numpy as np
import pygame
import threading
import time
from scipy import signal
import math
from UPST.modules.profiler import profile
from UPST.debug.debug_manager import Debug
from UPST.gizmos.gizmos_manager import Gizmos

class SoundSynthesizer:
    _instance = None
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    def __init__(self, sample_rate=44100, buffer_size=4024):
        if getattr(self, '_initialized', False):
            return
        pygame.mixer.pre_init(sample_rate, -16, 2, buffer_size)
        pygame.mixer.init()
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.volume = 0.5
        self.effects = {
            'vibrato_rate': 5.0,
            'vibrato_depth': 0.002,
            'tremolo_rate': 5.0,
            'tremolo_depth': 0.5,
            'reverb_amount': 0.3,
            'delay_time': 0.3,
            'delay_feedback': 0.4,
            'chorus_rate': 1.5,
            'chorus_depth': 0.003,
            'distortion_amount': 0.0
        }
        self.filter_settings = {'type': 'lowpass', 'cutoff': 2000, 'resonance': 1.0}
        self.lfo = {'rate': 2.0, 'depth': 1.1, 'target': 'cutoff'}
        self.active_voices = []
        self._initialized = True

    def set_volume(self, vol):
        Debug.log("Setted volume: "+ str(vol))
        self.volume = max(0.0, min(1.0, vol))

    def set_filter(self, filter_type='lowpass', cutoff=2000, resonance=1.0):
        self.filter_settings.update({'type': filter_type, 'cutoff': cutoff, 'resonance': resonance})

    def set_lfo(self, rate=2.0, depth=0.1, target='cutoff'):
        self.lfo.update({'rate': rate, 'depth': depth, 'target': target})

    def _safe_int16_conversion(self, samples):
        samples = np.asarray(samples, dtype=np.float64)
        samples = np.clip(samples, -32768, 32767)
        return samples.astype(np.int16)

    def _apply_panning(self, samples, pan=0.0):
        if samples.ndim == 1:
            samples = np.column_stack((samples, samples))
        pan = max(-1.0, min(1.0, pan))
        left_gain = math.sqrt((1.0 - pan) / 2.0)
        right_gain = math.sqrt((1.0 + pan) / 2.0)
        samples[:, 0] *= left_gain
        samples[:, 1] *= right_gain
        return samples

    @profile("SS_generate_wave", "synthesizer")
    def _generate_wave(self, freq, duration, waveform='sine', detune=0.0):
        freq *= 2 ** (detune / 1200)
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        if waveform == 'sine':
            return np.sin(2 * np.pi * freq * t)
        if waveform == 'square':
            return np.sign(np.sin(2 * np.pi * freq * t))
        if waveform == 'sawtooth':
            return 2 * (t * freq - np.floor(0.5 + t * freq))
        if waveform == 'triangle':
            return 2 * np.abs(2 * (t * freq - np.floor(0.5 + t * freq))) - 1
        if waveform == 'noise':
            return np.random.uniform(-1, 1, len(t))
        if waveform == 'pulse':
            duty = 0.5
            return np.where((t * freq) % 1 < duty, 1, -1)
        raise ValueError(f"Unknown waveform: {waveform}")

    @profile("SS_apply_adsr", "synthesizer")
    def _apply_adsr(self, wave, attack=0.01, decay=0.1, sustain=0.7, release=0.1):
        n = len(wave)
        sr = self.sample_rate
        a_n = int(sr * attack)
        d_n = int(sr * decay)
        r_n = int(sr * release)
        s_n = max(0, n - (a_n + d_n + r_n))
        total = a_n + d_n + r_n
        if total > n:
            scale = n / total
            a_n = int(a_n * scale)
            d_n = int(d_n * scale)
            r_n = n - (a_n + d_n)
        env = np.ones(n)
        if a_n:
            env[:a_n] = np.linspace(0, 1, a_n)
        if d_n:
            env[a_n:a_n + d_n] = np.linspace(1, sustain, d_n)
        if s_n:
            env[a_n + d_n:a_n + d_n + s_n] = sustain
        if r_n:
            env[-r_n:] = np.linspace(sustain, 0, r_n)
        return wave * env

    @profile("SS_apply_filter", "synthesizer")
    def _apply_filter(self, wave):
        if self.filter_settings['type'] == 'none':
            return wave
        nyquist = self.sample_rate / 2
        cutoff = max(0.01, min(0.99, self.filter_settings['cutoff'] / nyquist))
        try:
            t = self.filter_settings['type']
            if t == 'lowpass':
                b, a = signal.butter(4, cutoff, btype='low')
            elif t == 'highpass':
                b, a = signal.butter(4, cutoff, btype='high')
            elif t == 'bandpass':
                low, high = cutoff * 0.5, cutoff * 1.5
                b, a = signal.butter(4, [low, high], btype='band')
            else:
                return wave
            return signal.filtfilt(b, a, wave)
        except:
            return wave

    @profile("SS_apply_lfo", "synthesizer")
    def _apply_lfo(self, wave):
        t = np.linspace(0, len(wave) / self.sample_rate, len(wave), False)
        lfo = np.sin(2 * np.pi * self.lfo['rate'] * t) * self.lfo['depth']
        if self.lfo['target'] == 'volume':
            return wave * (1 + lfo)
        return wave

    @profile("SS_apply_effects", "synthesizer")
    def _apply_effects(self, wave):
        t = np.linspace(0, len(wave) / self.sample_rate, len(wave), False)
        trem = 1 + np.sin(2 * np.pi * self.effects['tremolo_rate'] * t) * self.effects['tremolo_depth']
        wave *= trem
        if self.effects['distortion_amount'] > 0:
            drive = 1 + self.effects['distortion_amount'] * 10
            wave = np.tanh(wave * drive) / drive
        if self.effects['chorus_rate'] > 0:
            delay_s = int(self.sample_rate * 0.01)
            mod = (np.sin(2 * np.pi * self.effects['chorus_rate'] * t) * self.effects['chorus_depth'] * delay_s).astype(int)
            c = np.zeros_like(wave)
            for i in range(len(wave)):
                j = i - delay_s + mod[i]
                if 0 <= j < len(wave):
                    c[i] = wave[j]
            wave = 0.7 * wave + 0.3 * c
        if self.effects['reverb_amount'] > 0:
            delays = [0.03, 0.05, 0.07, 0.09]
            rv = wave.copy()
            for d in delays:
                ds = int(self.sample_rate * d)
                if ds < len(wave):
                    tmp = np.zeros_like(wave)
                    tmp[ds:] = wave[:-ds]
                    rv += tmp * self.effects['reverb_amount'] * 0.3
            wave = rv
        if self.effects['delay_time'] > 0:
            ds = int(self.sample_rate * self.effects['delay_time'])
            if ds < len(wave):
                tmp = np.zeros_like(wave)
                tmp[ds:] = wave[:-ds]
                wave += tmp * self.effects['delay_feedback']
        return wave

    def _fade(self, data):
        length = len(data)
        f = int(self.sample_rate * 0.005)
        if f * 2 > length:
            f = length // 2
        env = np.ones(length)
        env[:f] = np.linspace(0, 1, f)
        env[-f:] = np.linspace(1, 0, f)
        return data * env[:, None]

    def play_frequency(self, freq, duration=1.0, waveform='sine', adsr=(0.01, 0.1, 0.7, 0.1), volume=None, detune=0.0,
                       apply_effects=True, pan=0.0):
        wave = self._generate_wave(freq, duration, waveform, detune)
        wave = self._apply_adsr(wave, *adsr)
        if apply_effects:
            wave = self._apply_filter(wave)
            wave = self._apply_lfo(wave)
            wave = self._apply_effects(wave)
        if np.max(np.abs(wave)) > 0:
            wave /= np.max(np.abs(wave))
        vol = self.volume if volume is None else max(0.0, min(1.0, volume))
        wave *= vol
        samples = self._safe_int16_conversion(wave * 32767)
        stereo = np.column_stack((samples, samples)).astype(np.float64)
        stereo = self._apply_panning(stereo, pan)
        stereo = self._fade(stereo)
        out = self._safe_int16_conversion(stereo)
        sound = pygame.sndarray.make_sound(out)

        self._visualize_wave_on_screen(wave, duration, freq=freq, waveform=waveform, volume=vol, pan=pan)

        return sound.play()

    def _visualize_wave_on_screen(self, wave, duration, freq=None, waveform='sine', volume=None, pan=0.0):
        if not Gizmos:
            return

        screen_width = 800
        screen_height = 600
        surf = pygame.display.get_surface()
        if surf:
            screen_width, screen_height = surf.get_size()

        margin_top = 40
        wave_height = 100
        wave_width = min(screen_width - 100, 600)
        x_offset = (screen_width - wave_width) // 2
        y_center = margin_top + wave_height // 2

        num_points = min(len(wave), 300)
        if num_points < 2:
            return

        indices = np.linspace(0, len(wave) - 1, num_points, dtype=int)
        reduced_wave = wave[indices]
        x_step = wave_width / (num_points - 1)

        for i in range(num_points - 1):
            x1 = x_offset + i * x_step
            x2 = x_offset + (i + 1) * x_step
            y1 = y_center - reduced_wave[i] * (wave_height * 0.45)
            y2 = y_center - reduced_wave[i + 1] * (wave_height * 0.45)
            Gizmos.draw_line(
                (x1, y1),
                (x2, y2),
                color='cyan',
                thickness=2,
                duration=duration,
                world_space=False
            )

        info_y = margin_top + wave_height + 10
        label_color = 'white'
        bg_color = (0, 0, 0, 180)

        if freq is not None:
            Gizmos.draw_text(
                (x_offset, info_y),
                f"Freq: {freq:.2f} Hz",
                color=label_color,
                background_color=bg_color,
                duration=duration,
                world_space=False,
                font_size=16
            )
            info_y += 22

        Gizmos.draw_text(
            (x_offset, info_y),
            f"Waveform: {waveform}",
            color=label_color,
            background_color=bg_color,
            duration=duration,
            world_space=False,
            font_size=16
        )
        info_y += 22

        vol_display = self.volume if volume is None else volume
        Gizmos.draw_text(
            (x_offset, info_y),
            f"Volume: {vol_display:.2f}",
            color=label_color,
            background_color=bg_color,
            duration=duration,
            world_space=False,
            font_size=16
        )
        info_y += 22

        Gizmos.draw_text(
            (x_offset, info_y),
            f"Pan: {pan:.2f}",
            color=label_color,
            background_color=bg_color,
            duration=duration,
            world_space=False,
            font_size=16
        )
        info_y += 22

        Gizmos.draw_text(
            (x_offset, info_y),
            f"Duration: {duration:.2f}s",
            color=label_color,
            background_color=bg_color,
            duration=duration,
            world_space=False,
            font_size=16
        )

    def play_drum(self, drum_type, volume=None, pan=0.0):
        wave = self._generate_drum_sample(drum_type)
        if np.max(np.abs(wave)) > 0:
            wave /= np.max(np.abs(wave))
        vol = self.volume if volume is None else max(0.0, min(1.0, volume))
        wave *= vol
        samples = self._safe_int16_conversion(wave * 32767)
        stereo = np.column_stack((samples, samples)).astype(np.float64)
        stereo = self._apply_panning(stereo, pan)
        stereo = self._fade(stereo)
        out = self._safe_int16_conversion(stereo)
        sound = pygame.sndarray.make_sound(out)
        return sound.play()

    NOTE_FREQUENCIES = {
        'C0': 16.35, 'C#0': 17.32, 'D0': 18.35, 'D#0': 19.45, 'E0': 20.60, 'F0': 21.83, 'F#0': 23.12, 'G0': 24.50,
        'G#0': 25.96, 'A0': 27.50, 'A#0': 29.14, 'B0': 30.87,
        'C1': 32.70, 'C#1': 34.65, 'D1': 36.71, 'D#1': 38.89, 'E1': 41.20, 'F1': 43.65, 'F#1': 46.25, 'G1': 49.00,
        'G#1': 51.91, 'A1': 55.00, 'A#1': 58.27, 'B1': 61.74,
        'C2': 65.41, 'C#2': 69.30, 'D2': 73.42, 'D#2': 77.78, 'E2': 82.41, 'F2': 87.31, 'F#2': 92.50, 'G2': 98.00,
        'G#2': 103.83, 'A2': 110.00, 'A#2': 116.54, 'B2': 123.47,
        'C3': 130.81, 'C#3': 138.59, 'D3': 146.83, 'D#3': 155.56, 'E3': 164.81, 'F3': 174.61, 'F#3': 185.00,
        'G3': 196.00, 'G#3': 207.65, 'A3': 220.00, 'A#3': 233.08, 'B3': 246.94,
        'C4': 261.63, 'C#4': 277.18, 'D4': 293.66, 'D#4': 311.13, 'E4': 329.63, 'F4': 349.23, 'F#4': 369.99,
        'G4': 392.00, 'G#4': 415.30, 'A4': 440.00, 'A#4': 466.16, 'B4': 493.88,
        'C5': 523.25, 'C#5': 554.37, 'D5': 587.33, 'D#5': 622.25, 'E5': 659.25, 'F5': 698.46, 'F#5': 739.99,
        'G5': 783.99, 'G#5': 830.61, 'A5': 880.00, 'A#5': 932.33, 'B5': 987.77,
        'C6': 1046.50, 'C#6': 1108.73, 'D6': 1174.66, 'D#6': 1244.51, 'E6': 1318.51, 'F6': 1396.91, 'F#6': 1479.98,
        'G6': 1567.98, 'G#6': 1661.22, 'A6': 1760.00, 'A#6': 1864.66, 'B6': 1975.53,
        'C7': 2093.00, 'C#7': 2217.46, 'D7': 2349.32, 'D#7': 2489.02, 'E7': 2637.02, 'F7': 2793.83, 'F#7': 2959.96,
        'G7': 3135.96, 'G#7': 3322.44, 'A7': 3520.00, 'A#7': 3729.31, 'B7': 3951.07,
        'C8': 4186.01, 'C#8': 4434.92, 'D8': 4698.64, 'D#8': 4978.03, 'E8': 5274.04, 'F8': 5587.65, 'F#8': 5919.91,
        'G8': 6271.93, 'G#8': 6644.88, 'A8': 7040.00, 'A#8': 7458.62, 'B8': 7902.13,
    }

    def play_note(self, note, duration=1.0, volume=None, pan=0.0, **kwargs):
        freq = self.NOTE_FREQUENCIES.get(note)
        if freq is None:
            raise ValueError(f"Note {note} not defined.")
        return self.play_frequency(freq, duration, volume=volume, pan=pan, **kwargs)

    def play_chord(self, notes, duration=1.0, waveform='sine', volume=None, pan=0.0):
        def _play_chord():
            channels = []
            for note in notes:
                ch = self.play_note(note, duration, waveform=waveform, volume=volume, pan=pan)
                channels.append(ch)
            return channels
        return _play_chord()

    def play_arpeggio(self, notes, note_duration=0.25, waveform='sine', volume=None, pan=0.0):
        def _arp():
            for note in notes:
                ch = self.play_note(note, note_duration, waveform=waveform, volume=volume, pan=pan)
                time.sleep(note_duration)
        threading.Thread(target=_arp, daemon=True).start()

    def play_sequence(self, notes, durations, waveform='sine', adsr=(0.01, 0.1, 0.7, 0.1), volumes=None, pan=0.0):
        def _seq():
            for i, (n, d) in enumerate(zip(notes, durations)):
                vol = None
                if volumes is not None and i < len(volumes):
                    vol = volumes[i]
                ch = self.play_note(n, duration=d, waveform=waveform, adsr=adsr, volume=vol, pan=pan)
                time.sleep(d)
        threading.Thread(target=_seq, daemon=True).start()

    def play_drum_pattern(self, pattern, bpm=120):
        def _drum_pattern():
            step_duration = 60.0 / (bpm * 4)
            steps = {}
            for drum_type, step in pattern:
                if step not in steps:
                    steps[step] = []
                steps[step].append(drum_type)
            for step in range(16):
                if step in steps:
                    for drum_type in steps[step]:
                        self.play_drum(drum_type)
                time.sleep(step_duration)
        threading.Thread(target=_drum_pattern, daemon=True).start()

    def create_scale(self, root='C4', scale_type='major'):
        scales = {
            'major': [0, 2, 4, 5, 7, 9, 11],
            'minor': [0, 2, 3, 5, 7, 8, 10],
            'pentatonic': [0, 2, 4, 7, 9],
            'blues': [0, 3, 5, 6, 7, 10],
            'dorian': [0, 2, 3, 5, 7, 9, 10],
            'mixolydian': [0, 2, 4, 5, 7, 9, 10]
        }
        if scale_type not in scales:
            raise ValueError(f"Unknown scale type: {scale_type}")
        root_freq = self.NOTE_FREQUENCIES.get(root)
        if root_freq is None:
            raise ValueError(f"Unknown root note: {root}")
        scale_freqs = []
        intervals = scales[scale_type]
        for interval in intervals:
            freq = root_freq * (2 ** (interval / 12))
            scale_freqs.append(freq)
        return scale_freqs

synthesizer = SoundSynthesizer()