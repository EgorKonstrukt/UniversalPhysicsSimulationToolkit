def start():
    self.composer = InfiniteAmbientComposer(owner)
    self.composer.start_infinite_composition()

def update(dt):
    if hasattr(self, 'composer'):
        self.composer.update(dt)

class InfiniteAmbientComposer:
    PHASE_COLORS = {
        "emerging": (100, 150, 255, 200),
        "building": (100, 255, 150, 200),
        "sustaining": (255, 255, 100, 200),
        "transforming": (255, 150, 100, 200),
        "dissolving": (180, 100, 255, 200)
    }
    TEXTURE_COLORS = {
        'drone': (200, 200, 200),
        'pad': (180, 220, 255),
        'shimmer': (255, 255, 200),
        'grain': (220, 200, 180),
        'sweep': (255, 180, 180),
        'morph': (200, 180, 255),
        'breath': (180, 255, 220),
        'pulse': (255, 180, 220),
        'wave': (180, 220, 255),
        'mist': (200, 200, 220),
        'crystal': (200, 255, 255),
        'void': (100, 100, 120)
    }
    WAVEFORM_COLORS = {'sine': (255, 255, 255), 'triangle': (180, 255, 180), 'sawtooth': (255, 180, 180)}

    def __init__(self, owner):
        self.owner = owner
        self.synth = synthesizer
        self.is_playing = True
        self.current_phase = "emerging"
        self.phase_duration = 0
        self.phase_timer = 0
        self.sound_layers = []
        self.harmonic_fields = []
        self.texture_generators = []
        self.global_parameters = {'tempo':60,'density':0.3,'brightness':0.2,'movement':0.2,'depth':0.9,'tension':0.1,'flow':0.5,'atmosphere':0.7}
        self.evolution_patterns = {'wave':lambda t:0.5+0.5*math.sin(t*0.1),'spiral':lambda t:0.5+0.3*math.sin(t*0.07)*math.cos(t*0.13),'drift':lambda t:0.3+0.4*(1+math.sin(t*0.05))*0.5,'pulse':lambda t:0.2+0.6*abs(math.sin(t*0.03)),'flow':lambda t:0.4+0.3*math.sin(t*0.08)+0.2*math.sin(t*0.19)}
        self.frequency_ratios = [1.0,1.5,2.0,3.0,4.0,5.0,6.0,7.0,8.0,1.618,2.618,1.414,2.828,1.732,3.464,1.259,1.587,1.888,2.378,2.996]
        self.texture_types = ['drone','pad','shimmer','grain','sweep','morph','breath','pulse','wave','mist','crystal','void']
        self.spatial_behaviors = ['static','orbit','float','spiral','pendulum','drift','teleport','expand','contract','rotate','flutter']
        self.start_time = time.time()
        self.last_visual_update = 0
        self.last_audio_update = 0
        self.last_cleanup = self.start_time

    def initialize_composition(self):
        self.sound_layers = []; self.harmonic_fields = []; self.texture_generators = []
        base_freq = random.uniform(40,120)
        for _ in range(random.randint(3,7)): self.create_harmonic_field(base_freq*random.choice(self.frequency_ratios))
        for _ in range(random.randint(8,16)): self.create_sound_layer()
        for _ in range(random.randint(4,8)): self.create_texture_generator()

    def create_harmonic_field(self, root_freq):
        harmonics = [root_freq*random.choice(self.frequency_ratios) for _ in range(random.randint(8,16))]
        self.harmonic_fields.append(type('HarmonicField',(object,),{'root_freq':root_freq,'harmonics':harmonics,'dissonance_factor':random.uniform(0.0,0.3),'spatial_spread':random.uniform(0.2,0.8),'evolution_rate':random.uniform(0.001,0.01)})())

    def create_sound_layer(self):
        field = random.choice(self.harmonic_fields) if self.harmonic_fields else None
        base_freq = field.root_freq if field else random.uniform(60,400)
        self.sound_layers.append(type('SoundLayer',(object,),{
            'frequency':base_freq*random.choice(self.frequency_ratios),
            'amplitude':random.uniform(0.1,0.7),
            'waveform':random.choice(['sine','triangle','sawtooth']),
            'pan':random.uniform(-1.0,1.0),
            'phase':random.uniform(0,2*math.pi),
            'evolution_speed':random.uniform(0.0005,0.005),
            'texture_type':random.choice(self.texture_types),
            'active':True})())

    def create_texture_generator(self):
        self.texture_generators.append({
            'type':random.choice(['granular','spectral','modal','stochastic']),
            'parameters':{'density':random.uniform(0.1,0.6),'grain_size':random.uniform(0.05,0.3),'scatter':random.uniform(0.0,0.5),'evolution':random.uniform(0.001,0.008)},
            'spatial_behavior':random.choice(self.spatial_behaviors),
            'active':True})

    def start_infinite_composition(self):
        self.start_time = time.time()
        self.last_cleanup = self.start_time
        self.initialize_composition()

    def update(self, dt):
        if not self.is_playing: return
        elapsed = time.time() - self.start_time
        self.phase_timer += dt
        self.evolve_phase(elapsed)
        self._visualize()
        if elapsed - self.last_audio_update >= 0.1:
            self.last_audio_update = elapsed
            audio_data = self.generate_audio_frame(elapsed)
            self.play_audio_data(audio_data)
        if elapsed - self.last_cleanup > 300:
            self.cleanup_inactive_elements()
            self.last_cleanup = elapsed
        if elapsed > 1800:
            self.reinitialize_composition()
            self.start_time = time.time()
            self.last_cleanup = self.start_time

    def transition_to_next_phase(self):
        phases = ["emerging","building","sustaining","transforming","dissolving"]
        current_idx = phases.index(self.current_phase)
        next_idx = (current_idx+1)%len(phases) if random.random()<0.7 else random.randint(0,len(phases)-1)
        self.current_phase=phases[next_idx]
        self.phase_duration=random.uniform(30,120)
        self.phase_timer=0
        self.apply_phase_transition()

    def apply_phase_characteristics(self, progress):
        curves = {"emerging":lambda p:p*0.3,"building":lambda p:0.3+p*0.4,"sustaining":lambda p:0.6+0.2*math.sin(p*math.pi*4),"transforming":lambda p:0.5+0.4*math.sin(p*math.pi*2),"dissolving":lambda p:0.8*(1-p*0.7)}
        intensity = curves[self.current_phase](progress)
        self.global_parameters['density']=max(0.1,min(0.9,intensity))
        self.global_parameters['movement']=intensity*0.6
        self.global_parameters['depth']=0.4+intensity*0.4

    def evolve_phase(self, elapsed_time):
        phase_progress = self.phase_timer/self.phase_duration if self.phase_duration>0 else 0
        if phase_progress>=1.0 or self.phase_duration==0: self.transition_to_next_phase()
        self.apply_phase_characteristics(phase_progress)
        self.evolve_global_parameters(elapsed_time)
        self.evolve_harmonic_fields(elapsed_time)
        self.evolve_sound_layers(elapsed_time)
        self.evolve_texture_generators(elapsed_time)

    def apply_phase_transition(self):
        if self.current_phase=="emerging": self.spawn_new_layers()
        elif self.current_phase=="building": self.enhance_harmonic_complexity()
        elif self.current_phase=="transforming": self.mutate_existing_elements()
        elif self.current_phase=="dissolving": self.fade_random_elements()

    def spawn_new_layers(self):
        for _ in range(random.randint(2,5)): self.create_sound_layer()
        if random.random()<0.3: self.create_harmonic_field(random.uniform(30,200))

    def enhance_harmonic_complexity(self):
        for field in self.harmonic_fields:
            if random.random()<0.4:
                new_h = [field.root_freq*random.choice(self.frequency_ratios) for _ in range(random.randint(2,6))]
                field.harmonics.extend(new_h)

    def mutate_existing_elements(self):
        for layer in self.sound_layers:
            if random.random()<0.3:
                layer.frequency*=random.uniform(0.8,1.25)
                layer.waveform='sine'
                layer.texture_type=random.choice(self.texture_types)
        for g in self.texture_generators:
            if random.random()<0.4:
                g['parameters']['density']*=random.uniform(0.7,1.4)
                g['spatial_behavior']=random.choice(self.spatial_behaviors)

    def fade_random_elements(self):
        active = [l for l in self.sound_layers if l.active]
        if len(active)>3:
            for _ in range(random.randint(1,3)):
                l=random.choice(active); l.active=False; active.remove(l)

    def evolve_global_parameters(self, t):
        for p,v in self.global_parameters.items():
            f=random.choice(list(self.evolution_patterns.values()))
            self.global_parameters[p]=max(0.0,min(1.0,v+f(t)*0.02+random.uniform(-0.01,0.01)))

    def evolve_harmonic_fields(self, t):
        for f in self.harmonic_fields:
            f.root_freq+=random.uniform(-0.1,0.1)
            f.dissonance_factor=max(0.0,min(0.5,f.dissonance_factor+random.uniform(-0.005,0.005)))
            if random.random()<0.001: f.spatial_spread=random.uniform(0.1,0.9)

    def evolve_sound_layers(self, t):
        for l in self.sound_layers:
            if not l.active: continue
            l.phase+=l.evolution_speed
            l.frequency+=math.sin(l.phase)*0.5
            amp=0.5+0.5*math.sin(l.phase*0.7)
            l.amplitude=max(0.05,min(0.8,l.amplitude*amp))
            if random.random()<0.0005:
                l.texture_type=random.choice(self.texture_types)
                l.waveform=random.choice(['sine','triangle','sawtooth'])

    def evolve_texture_generators(self, t):
        for g in self.texture_generators:
            if not g['active']: continue
            for k,v in g['parameters'].items():
                if k!='evolution': g['parameters'][k]=max(0.0,min(1.0,v+random.uniform(-0.01,0.01)))
            if random.random()<0.0008: g['spatial_behavior']=random.choice(self.spatial_behaviors)

    def generate_audio_frame(self, t):
        data=[]
        for l in self.sound_layers:
            if not l.active: continue
            amp=l.amplitude*self.global_parameters['density']
            tm=self.apply_texture_modulation(l,t)
            sp=self.calculate_spatial_position(l,t)
            data.extend(self.generate_layer_audio(l,tm,sp))
        for g in self.texture_generators:
            if g['active']: data.extend(self.generate_texture_audio(g,t))
        return data

    def apply_texture_modulation(self, l, t):
        mods={'drone':lambda _:1.0,'pad':lambda t:0.8+0.2*math.sin(t*0.1),'shimmer':lambda t:0.5+0.5*abs(math.sin(t*2.0)),'grain':lambda _:random.uniform(0.3,1.0),'sweep':lambda t:0.3+0.7*(0.5+0.5*math.sin(t*0.05)),'morph':lambda t:0.6+0.4*math.sin(t*0.3)*math.cos(t*0.7),'breath':lambda t:0.4+0.6*(math.sin(t*0.08)**2),'pulse':lambda t:0.2+0.8*abs(math.sin(t*0.25)),'wave':lambda t:0.5+0.5*math.sin(t*0.15),'mist':lambda _:0.7+0.3*random.uniform(-1,1)*0.1,'crystal':lambda t:0.8+0.2*math.sin(t*1.5),'void':lambda t:0.1+0.4*math.sin(t*0.02)}
        return mods[l.texture_type](t)

    def calculate_spatial_position(self, l, t):
        base=l.pan
        pat={'static':lambda _:base,'orbit':lambda t:math.sin(t*0.1)*0.8,'float':lambda t:base+0.3*math.sin(t*0.03),'spiral':lambda t:math.sin(t*0.08)*math.cos(t*0.13)*0.9,'pendulum':lambda t:math.sin(t*0.06)*0.7,'drift':lambda t:base+0.1*math.sin(t*0.02),'teleport':lambda t:random.uniform(-1,1) if random.random()<0.001 else base,'expand':lambda t:base*(1+0.3*math.sin(t*0.04)),'contract':lambda t:base*(0.7+0.3*math.sin(t*0.07)),'rotate':lambda t:math.sin(t*0.12)*0.9,'flutter':lambda t:base+0.2*math.sin(t*0.8)}
        b=random.choice(self.spatial_behaviors)
        return max(-1.0,min(1.0,pat[b](t)))

    def generate_layer_audio(self, l, tm, sp):
        dur=0.1
        vol=l.amplitude*tm*self.global_parameters['atmosphere']
        w=l.waveform
        if l.texture_type in ['grain','shimmer']: w=random.choice(['sine','triangle'])
        f=l.frequency
        if l.texture_type=='sweep': f*=1+0.1*math.sin(time.time()*0.5)
        return [(f,dur,w,vol,sp)]

    def generate_texture_audio(self, g, t):
        d=[]
        tp=g['type']; p=g['parameters']
        if tp=='granular':
            for _ in range(random.randint(1,4)): d.append((random.uniform(60,800),p['grain_size'],'sine',p['density']*0.3,random.uniform(-1,1)))
        elif tp=='spectral':
            bf=random.uniform(100,400)
            for i in range(random.randint(3,8)): d.append((bf*(i+1),0.2,'triangle',p['density']*0.4/(i+1),random.uniform(-0.5,0.5)))
        elif tp=='modal':
            for _ in range(random.randint(2,6)): d.append((random.choice([110,165,220,330,440,660])*random.uniform(0.98,1.02),random.uniform(0.5,2.0),'sine',p['density']*0.25,random.uniform(-0.8,0.8)))
        elif tp=='stochastic' and random.random()<p['density']:
            d.append((random.uniform(40,1000),random.uniform(0.05,0.5),'triangle',random.uniform(0.1,0.4),random.uniform(-1,1)))
        return d

    def play_audio_data(self, data):
        for f,dur,w,vol,pan in data:
            if vol>0.01: self.synth.play_note(self.freq_to_note(f),dur,waveform=w,volume=vol,pan=pan)

    def freq_to_note(self, f):
        if f<=0: return "C4"
        A4=440; C0=A4*(2**(-4.75))
        h=round(12*math.log2(f/C0))
        octave=h//12; n=h%12
        notes=["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
        return f"{notes[n]}{max(0,min(8,octave))}"

    def _draw_progress_ring(self, center, radius, progress, color, segments=64):
        if progress <= 0: return
        angle_step = 2 * math.pi / segments
        full_segments = int(segments * progress)
        for i in range(full_segments):
            start_angle = i * angle_step
            end_angle = (i + 1) * angle_step
            start = (center[0] + radius * math.cos(start_angle), center[1] + radius * math.sin(start_angle))
            end = (center[0] + radius * math.cos(end_angle), center[1] + radius * math.sin(end_angle))
            Gizmos.draw_line(start, end, color=color, thickness=4)

    MAX_HARMONICS_PER_FIELD = 16
    MAX_SOUND_LAYERS_VISUALIZED = 24
    MAX_TEXTURE_GENERATORS_VISUALIZED = 12

    def _visualize(self):
        now = time.time()
        if now - self.last_visual_update < 0.05: return
        self.last_visual_update = now
        elapsed = now - self.start_time
        center = self.owner.position if hasattr(self.owner, 'position') else (0, 0)
        base_x, base_y = center[0] - 400, center[1]
        radius = 80 + 60 * self.global_parameters['depth']
        phase_color = self.PHASE_COLORS.get(self.current_phase, (255, 255, 255, 200))
        progress = min(1.0, self.phase_timer / self.phase_duration) if self.phase_duration > 0 else 0.0

        Gizmos.draw_circle(center, radius, color=phase_color, filled=False, thickness=3)
        self._draw_progress_ring(center, radius + 3, progress, phase_color)
        Gizmos.draw_text((center[0], center[1] - radius - 40), f"Phase: {self.current_phase.title()}", font_size=16, color=phase_color[:3])
        Gizmos.draw_text((center[0], center[1] - radius - 20), f"Progress: {progress:.1%}", font_size=14, color=(200, 200, 200))

        for i, field in enumerate(self.harmonic_fields):
            harmonics_subset = field.harmonics[:self.MAX_HARMONICS_PER_FIELD]
            if not harmonics_subset: continue
            angle_step = 2 * math.pi / len(harmonics_subset)
            field_radius = radius + 30 + i * 25
            base_color = tuple(int(c * (0.4 + 0.6 * field.dissonance_factor)) for c in phase_color[:3])
            Gizmos.draw_circle(center, field_radius, color=base_color + (120,), filled=False, thickness=1)
            max_harm = max(harmonics_subset)
            for j, harmonic in enumerate(harmonics_subset):
                angle = j * angle_step
                x = center[0] + field_radius * math.cos(angle)
                y = center[1] + field_radius * math.sin(angle)
                freq_color = tuple(int(c * (0.6 + 0.4 * (harmonic / max_harm))) for c in base_color)
                size = 2 + 4 * (harmonic / max_harm)
                Gizmos.draw_point((x, y), color=freq_color, size=size)
                if j % 8 == 0:
                    note = self.freq_to_note(harmonic)
                    Gizmos.draw_text((x, y - 10), note, font_size=10, color=freq_color)

        visible_layers = [l for l in self.sound_layers if l.active][:self.MAX_SOUND_LAYERS_VISUALIZED]
        layer_y = base_y + 200
        for idx, layer in enumerate(visible_layers):
            x = base_x + (idx % 12) * 20
            y = layer_y + (idx // 12) * 100 + 80 * (layer.pan + 1)
            color = self.TEXTURE_COLORS.get(layer.texture_type, (200, 200, 200))
            waveform_color = self.WAVEFORM_COLORS.get(layer.waveform, (255, 255, 255))
            size = 3 + 7 * layer.amplitude
            Gizmos.draw_point((x, y), color=color, size=size)
            arrow_len = 10 + 20 * layer.amplitude
            end_x = x + arrow_len * math.cos(layer.phase)
            end_y = y + arrow_len * math.sin(layer.phase)
            Gizmos.draw_arrow((x, y), (end_x, end_y), color=waveform_color, thickness=2)
            if idx % 6 == 0:
                note = self.freq_to_note(layer.frequency)
                Gizmos.draw_text((x, y - 15), f"{note} ({layer.texture_type[:4]})", font_size=10, color=color)

        visible_gens = [g for g in self.texture_generators if g['active']][:self.MAX_TEXTURE_GENERATORS_VISUALIZED]
        gen_y = base_y + 350
        for idx, gen in enumerate(visible_gens):
            x = base_x + idx * 30
            y = gen_y
            color_map = {'granular':(200,100,100),'spectral':(100,200,100),'modal':(100,100,200),'stochastic':(200,200,100)}
            color = color_map.get(gen['type'], (150,150,150))
            pulse = 8 + 4 * math.sin(elapsed * 5 + idx)
            Gizmos.draw_rect((x, y), pulse, pulse, color=color, filled=True)
            Gizmos.draw_text((x, y + 10), gen['type'][:4], font_size=10, color=(255, 255, 255))

        param_y = base_y + 500
        for i, (param, value) in enumerate(self.global_parameters.items()):
            bar_x = base_x + i * 70
            bar_y = param_y
            bar_w, bar_h = 60, 100
            fill_h = int(bar_h * value)
            Gizmos.draw_rect((bar_x + bar_w//2, bar_y + bar_h//2), bar_w, bar_h, color=(50, 50, 50), filled=True)
            Gizmos.draw_rect((bar_x + bar_w//2, bar_y + bar_h - fill_h//2), bar_w - 4, fill_h, color=(100, 200, 255), filled=True)
            Gizmos.draw_text((bar_x + bar_w//2, bar_y - 15), param[:4], font_size=12, color=(200, 200, 200))
            Gizmos.draw_text((bar_x + bar_w//2, bar_y + bar_h + 5), f"{value:.2f}", font_size=12, color=(200, 200, 200))
    def cleanup_inactive_elements(self):
        self.sound_layers=[l for l in self.sound_layers if l.active]
        self.texture_generators=[g for g in self.texture_generators if g['active']]
        if len(self.sound_layers)<5:
            for _ in range(random.randint(2,4)): self.create_sound_layer()

    def reinitialize_composition(self):
        self.sound_layers=[]; self.harmonic_fields=[]; self.texture_generators=[]; self.initialize_composition()