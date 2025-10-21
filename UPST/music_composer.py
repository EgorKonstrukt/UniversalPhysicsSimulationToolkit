import threading
import time
import random
import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class DynamicPhase(Enum):
    EMERGING = "emerging"
    BUILDING = "building"
    SUSTAINING = "sustaining"
    TRANSFORMING = "transforming"
    DISSOLVING = "dissolving"


@dataclass
class SoundLayer:
    frequency: float
    amplitude: float
    waveform: str
    pan: float
    phase: float
    evolution_speed: float
    texture_type: str
    active: bool = True


@dataclass
class HarmonicField:
    root_freq: float
    harmonics: List[float]
    dissonance_factor: float
    spatial_spread: float
    evolution_rate: float


class InfiniteAmbientComposer:
    def __init__(self, synthesizer):
        self.synth = synthesizer
        self.is_playing = False
        self.current_phase = DynamicPhase.EMERGING
        self.phase_duration = 0
        self.phase_timer = 0

        self.sound_layers = []
        self.harmonic_fields = []
        self.texture_generators = []
        self.spatial_processors = []

        self.global_parameters = {
            'tempo': 60,
            'density': 0.3,
            'brightness': 0.2,
            'movement': 0.2,
            'depth': 0.9,
            'tension': 0.1,
            'flow': 0.5,
            'atmosphere': 0.7
        }

        self.evolution_patterns = {
            'wave': lambda t: 0.5 + 0.5 * math.sin(t * 0.1),
            'spiral': lambda t: 0.5 + 0.3 * math.sin(t * 0.07) * math.cos(t * 0.13),
            'drift': lambda t: 0.3 + 0.4 * (1 + math.sin(t * 0.05)) * 0.5,
            'pulse': lambda t: 0.2 + 0.6 * abs(math.sin(t * 0.03)),
            'flow': lambda t: 0.4 + 0.3 * math.sin(t * 0.08) + 0.2 * math.sin(t * 0.19)
        }

        self.frequency_ratios = [
            1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0,
            1.618, 2.618, 1.414, 2.828, 1.732, 3.464,
            1.259, 1.587, 1.888, 2.378, 2.996
        ]

        self.texture_types = [
            'drone', 'pad', 'shimmer', 'grain', 'sweep', 'morph',
            'breath', 'pulse', 'wave', 'mist', 'crystal', 'void'
        ]

        self.spatial_behaviors = [
            'static', 'orbit', 'float', 'spiral', 'pendulum', 'drift',
            'teleport', 'expand', 'contract', 'rotate', 'flutter'
        ]

    def initialize_composition(self):
        self.sound_layers = []
        self.harmonic_fields = []
        self.texture_generators = []

        base_freq = random.uniform(40, 120)

        for i in range(random.randint(3, 7)):
            self.create_harmonic_field(base_freq * random.choice(self.frequency_ratios))

        for i in range(random.randint(8, 16)):
            self.create_sound_layer()

        for i in range(random.randint(4, 8)):
            self.create_texture_generator()

    def create_harmonic_field(self, root_freq: float):
        harmonics = []
        for i in range(1, random.randint(8, 16)):
            ratio = random.choice(self.frequency_ratios)
            harmonics.append(root_freq * ratio)

        field = HarmonicField(
            root_freq=root_freq,
            harmonics=harmonics,
            dissonance_factor=random.uniform(0.0, 0.3),
            spatial_spread=random.uniform(0.2, 0.8),
            evolution_rate=random.uniform(0.001, 0.01)
        )

        self.harmonic_fields.append(field)

    def create_sound_layer(self):
        field = random.choice(self.harmonic_fields) if self.harmonic_fields else None
        base_freq = field.root_freq if field else random.uniform(60, 400)

        layer = SoundLayer(
            frequency=base_freq * random.choice(self.frequency_ratios),
            amplitude=random.uniform(0.1, 0.7),
            waveform=random.choice(['sine', 'triangle', 'sawtooth']),
            pan=random.uniform(-1.0, 1.0),
            phase=random.uniform(0, 2 * math.pi),
            evolution_speed=random.uniform(0.0005, 0.005),
            texture_type=random.choice(self.texture_types)
        )

        self.sound_layers.append(layer)

    def create_texture_generator(self):
        generator = {
            'type': random.choice(['granular', 'spectral', 'modal', 'stochastic']),
            'parameters': {
                'density': random.uniform(0.1, 0.6),
                'grain_size': random.uniform(0.05, 0.3),
                'scatter': random.uniform(0.0, 0.5),
                'evolution': random.uniform(0.001, 0.008)
            },
            'spatial_behavior': random.choice(self.spatial_behaviors),
            'active': True
        }

        self.texture_generators.append(generator)

    def evolve_phase(self, elapsed_time: float):
        phase_progress = self.phase_timer / self.phase_duration if self.phase_duration > 0 else 0

        if phase_progress >= 1.0 or self.phase_duration == 0:
            self.transition_to_next_phase()

        self.apply_phase_characteristics(phase_progress)
        self.evolve_global_parameters(elapsed_time)
        self.evolve_harmonic_fields(elapsed_time)
        self.evolve_sound_layers(elapsed_time)
        self.evolve_texture_generators(elapsed_time)

    def transition_to_next_phase(self):
        phases = list(DynamicPhase)
        current_idx = phases.index(self.current_phase)

        if random.random() < 0.7:
            next_idx = (current_idx + 1) % len(phases)
        else:
            next_idx = random.randint(0, len(phases) - 1)

        self.current_phase = phases[next_idx]
        self.phase_duration = random.uniform(30, 120)
        self.phase_timer = 0

        self.apply_phase_transition()

    def apply_phase_characteristics(self, progress: float):
        phase_curves = {
            DynamicPhase.EMERGING: lambda p: p * 0.3,
            DynamicPhase.BUILDING: lambda p: 0.3 + p * 0.4,
            DynamicPhase.SUSTAINING: lambda p: 0.6 + 0.2 * math.sin(p * math.pi * 4),
            DynamicPhase.TRANSFORMING: lambda p: 0.5 + 0.4 * math.sin(p * math.pi * 2),
            DynamicPhase.DISSOLVING: lambda p: 0.8 * (1 - p * 0.7)
        }

        intensity = phase_curves[self.current_phase](progress)

        self.global_parameters['density'] = max(0.1, min(0.9, intensity))
        self.global_parameters['movement'] = intensity * 0.6
        self.global_parameters['depth'] = 0.4 + intensity * 0.4

    def apply_phase_transition(self):
        if self.current_phase == DynamicPhase.EMERGING:
            self.spawn_new_layers()
        elif self.current_phase == DynamicPhase.BUILDING:
            self.enhance_harmonic_complexity()
        elif self.current_phase == DynamicPhase.TRANSFORMING:
            self.mutate_existing_elements()
        elif self.current_phase == DynamicPhase.DISSOLVING:
            self.fade_random_elements()

    def spawn_new_layers(self):
        for _ in range(random.randint(2, 5)):
            self.create_sound_layer()

        if random.random() < 0.3:
            base_freq = random.uniform(30, 200)
            self.create_harmonic_field(base_freq)

    def enhance_harmonic_complexity(self):
        for field in self.harmonic_fields:
            if random.random() < 0.4:
                new_harmonics = []
                for _ in range(random.randint(2, 6)):
                    ratio = random.choice(self.frequency_ratios)
                    new_harmonics.append(field.root_freq * ratio)
                field.harmonics.extend(new_harmonics)

    def mutate_existing_elements(self):
        for layer in self.sound_layers:
            if random.random() < 0.3:
                layer.frequency *= random.uniform(0.8, 1.25)
                layer.waveform = random.choice(['sine'])
                layer.texture_type = random.choice(self.texture_types)

        for generator in self.texture_generators:
            if random.random() < 0.4:
                generator['parameters']['density'] *= random.uniform(0.7, 1.4)
                generator['spatial_behavior'] = random.choice(self.spatial_behaviors)

    def fade_random_elements(self):
        active_layers = [l for l in self.sound_layers if l.active]
        if len(active_layers) > 3:
            for _ in range(random.randint(1, 3)):
                layer = random.choice(active_layers)
                layer.active = False
                active_layers.remove(layer)

    def evolve_global_parameters(self, elapsed_time: float):
        for param, value in self.global_parameters.items():
            pattern = random.choice(list(self.evolution_patterns.keys()))
            evolution_func = self.evolution_patterns[pattern]

            base_change = evolution_func(elapsed_time) * 0.02
            noise = random.uniform(-0.01, 0.01)

            new_value = value + base_change + noise
            self.global_parameters[param] = max(0.0, min(1.0, new_value))

    def evolve_harmonic_fields(self, elapsed_time: float):
        for field in self.harmonic_fields:
            field.root_freq += random.uniform(-0.1, 0.1)
            field.dissonance_factor += random.uniform(-0.005, 0.005)
            field.dissonance_factor = max(0.0, min(0.5, field.dissonance_factor))

            if random.random() < 0.001:
                field.spatial_spread = random.uniform(0.1, 0.9)

    def evolve_sound_layers(self, elapsed_time: float):
        for layer in self.sound_layers:
            if not layer.active:
                continue

            layer.phase += layer.evolution_speed

            freq_drift = math.sin(layer.phase) * 0.5
            layer.frequency += freq_drift

            amp_modulation = 0.5 + 0.5 * math.sin(layer.phase * 0.7)
            layer.amplitude *= amp_modulation
            layer.amplitude = max(0.05, min(0.8, layer.amplitude))

            if random.random() < 0.0005:
                layer.texture_type = random.choice(self.texture_types)
                layer.waveform = random.choice(['sine', 'triangle', 'sawtooth'])

    def evolve_texture_generators(self, elapsed_time: float):
        for generator in self.texture_generators:
            if not generator['active']:
                continue

            params = generator['parameters']
            for param, value in params.items():
                if param == 'evolution':
                    continue

                change = random.uniform(-0.01, 0.01)
                params[param] = max(0.0, min(1.0, value + change))

            if random.random() < 0.0008:
                generator['spatial_behavior'] = random.choice(self.spatial_behaviors)

    def generate_audio_frame(self, elapsed_time: float):
        frame_data = []

        for layer in self.sound_layers:
            if not layer.active:
                continue

            frequency = layer.frequency
            amplitude = layer.amplitude * self.global_parameters['density']

            texture_mod = self.apply_texture_modulation(layer, elapsed_time)
            spatial_pos = self.calculate_spatial_position(layer, elapsed_time)

            note_data = self.generate_layer_audio(layer, texture_mod, spatial_pos)
            frame_data.extend(note_data)

        for generator in self.texture_generators:
            if generator['active']:
                texture_data = self.generate_texture_audio(generator, elapsed_time)
                frame_data.extend(texture_data)

        return frame_data

    def apply_texture_modulation(self, layer: SoundLayer, elapsed_time: float):
        texture_mods = {
            'drone': lambda t: 1.0,
            'pad': lambda t: 0.8 + 0.2 * math.sin(t * 0.1),
            'shimmer': lambda t: 0.5 + 0.5 * abs(math.sin(t * 2.0)),
            'grain': lambda t: random.uniform(0.3, 1.0),
            'sweep': lambda t: 0.3 + 0.7 * (0.5 + 0.5 * math.sin(t * 0.05)),
            'morph': lambda t: 0.6 + 0.4 * math.sin(t * 0.3) * math.cos(t * 0.7),
            'breath': lambda t: 0.4 + 0.6 * (math.sin(t * 0.08) ** 2),
            'pulse': lambda t: 0.2 + 0.8 * abs(math.sin(t * 0.25)),
            'wave': lambda t: 0.5 + 0.5 * math.sin(t * 0.15),
            'mist': lambda t: 0.7 + 0.3 * random.uniform(-1, 1) * 0.1,
            'crystal': lambda t: 0.8 + 0.2 * math.sin(t * 1.5),
            'void': lambda t: 0.1 + 0.4 * math.sin(t * 0.02)
        }

        return texture_mods[layer.texture_type](elapsed_time)

    def calculate_spatial_position(self, layer: SoundLayer, elapsed_time: float):
        base_pan = layer.pan

        spatial_patterns = {
            'static': lambda t: base_pan,
            'orbit': lambda t: math.sin(t * 0.1) * 0.8,
            'float': lambda t: base_pan + 0.3 * math.sin(t * 0.03),
            'spiral': lambda t: math.sin(t * 0.08) * math.cos(t * 0.13) * 0.9,
            'pendulum': lambda t: math.sin(t * 0.06) * 0.7,
            'drift': lambda t: base_pan + 0.1 * math.sin(t * 0.02),
            'teleport': lambda t: random.uniform(-1, 1) if random.random() < 0.001 else base_pan,
            'expand': lambda t: base_pan * (1 + 0.3 * math.sin(t * 0.04)),
            'contract': lambda t: base_pan * (0.7 + 0.3 * math.sin(t * 0.07)),
            'rotate': lambda t: math.sin(t * 0.12) * 0.9,
            'flutter': lambda t: base_pan + 0.2 * math.sin(t * 0.8)
        }

        behavior = random.choice(self.spatial_behaviors)
        return max(-1.0, min(1.0, spatial_patterns[behavior](elapsed_time)))

    def generate_layer_audio(self, layer: SoundLayer, texture_mod: float, spatial_pos: float):
        duration = 0.1
        volume = layer.amplitude * texture_mod * self.global_parameters['atmosphere']

        waveform = layer.waveform
        if layer.texture_type in ['grain', 'shimmer']:
            waveform = random.choice(['sine', 'triangle'])

        frequency = layer.frequency
        if layer.texture_type == 'sweep':
            frequency *= (1 + 0.1 * math.sin(time.time() * 0.5))

        return [(layer.frequency, duration, waveform, volume, spatial_pos)]

    def generate_texture_audio(self, generator: Dict, elapsed_time: float):
        texture_data = []

        if generator['type'] == 'granular':
            for _ in range(random.randint(1, 4)):
                freq = random.uniform(60, 800)
                duration = generator['parameters']['grain_size']
                volume = generator['parameters']['density'] * 0.3
                texture_data.append((freq, duration, 'sine', volume, random.uniform(-1, 1)))

        elif generator['type'] == 'spectral':
            base_freq = random.uniform(100, 400)
            for i in range(random.randint(3, 8)):
                freq = base_freq * (i + 1)
                duration = 0.2
                volume = generator['parameters']['density'] * 0.4 / (i + 1)
                texture_data.append((freq, duration, 'triangle', volume, random.uniform(-0.5, 0.5)))

        elif generator['type'] == 'modal':
            for _ in range(random.randint(2, 6)):
                freq = random.choice([110, 165, 220, 330, 440, 660]) * random.uniform(0.98, 1.02)
                duration = random.uniform(0.5, 2.0)
                volume = generator['parameters']['density'] * 0.25
                texture_data.append((freq, duration, 'sine', volume, random.uniform(-0.8, 0.8)))

        elif generator['type'] == 'stochastic':
            if random.random() < generator['parameters']['density']:
                freq = random.uniform(40, 1000)
                duration = random.uniform(0.05, 0.5)
                volume = random.uniform(0.1, 0.4)
                texture_data.append((freq, duration, 'triangle', volume, random.uniform(-1, 1)))

        return texture_data

    def play_audio_data(self, audio_data: List[Tuple]):
        for freq, duration, waveform, volume, pan in audio_data:
            if volume > 0.01:
                self.synth.play_note(
                    self.freq_to_note(freq),
                    duration,
                    waveform=waveform,
                    volume=volume,
                    pan=pan
                )

    def freq_to_note(self, frequency: float) -> str:
        A4 = 440
        C0 = A4 * (2 ** (-4.75))

        if frequency <= 0:
            return "C4"

        h = round(12 * math.log2(frequency / C0))
        octave = h // 12
        n = h % 12

        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        note = note_names[n]

        return f"{note}{max(0, min(8, octave))}"

    def start_infinite_composition(self):
        if self.is_playing:
            return

        self.is_playing = True
        self.initialize_composition()

        def _infinite_loop():
            start_time = time.time()
            last_cleanup = start_time

            while self.is_playing:
                try:
                    elapsed_time = time.time() - start_time
                    self.phase_timer += 1

                    self.evolve_phase(elapsed_time)

                    audio_data = self.generate_audio_frame(elapsed_time)
                    self.play_audio_data(audio_data)

                    if elapsed_time - last_cleanup > 300:
                        self.cleanup_inactive_elements()
                        last_cleanup = elapsed_time

                    if elapsed_time > 1800:
                        self.reinitialize_composition()
                        start_time = time.time()
                        last_cleanup = start_time

                    time.sleep(0.1)

                except Exception as e:
                    print(f"Error in infinite composition: {e}")
                    time.sleep(1)

        threading.Thread(target=_infinite_loop, daemon=True).start()

    def cleanup_inactive_elements(self):
        self.sound_layers = [l for l in self.sound_layers if l.active]
        self.texture_generators = [g for g in self.texture_generators if g['active']]

        if len(self.sound_layers) < 5:
            for _ in range(random.randint(2, 4)):
                self.create_sound_layer()

    def reinitialize_composition(self):
        self.sound_layers = []
        self.harmonic_fields = []
        self.texture_generators = []
        self.initialize_composition()

    def stop_composition(self):
        self.is_playing = False

    def get_current_state(self) -> Dict:
        return {
            'phase': self.current_phase.value,
            'active_layers': len([l for l in self.sound_layers if l.active]),
            'harmonic_fields': len(self.harmonic_fields),
            'texture_generators': len([g for g in self.texture_generators if g['active']]),
            'global_parameters': self.global_parameters.copy()
        }

