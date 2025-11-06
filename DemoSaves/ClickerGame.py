import math, random, time

RESOURCE_TYPES = ["crystals", "plasma", "stardust"]
BASE_CLICK_VALUE = {"crystals": 1.0}
BASE_PASSIVE_RATE = {"plasma": 0.1, "stardust": 0.01}

UPGRADE_DEFS = [
    {"id":"click1","name":"Resonant Claws","base_cost":10,"cost_mult":1.4,"type":"click","value":1.0,"resource":"crystals"},
    {"id":"click2","name":"Plasma Talons","base_cost":100,"cost_mult":1.5,"type":"click","value":5.0,"resource":"crystals"},
    {"id":"click3","name":"Singularity Claws","base_cost":1000,"cost_mult":1.6,"type":"click","value":25.0,"resource":"crystals"},
    {"id":"passive1","name":"Crystal Extractor","base_cost":50,"cost_mult":1.45,"type":"passive","value":0.5,"resource":"crystals"},
    {"id":"passive2","name":"Plasma Forge","base_cost":500,"cost_mult":1.5,"type":"passive","value":5.0,"resource":"plasma"},
    {"id":"passive3","name":"Stardust Condenser","base_cost":5000,"cost_mult":1.6,"type":"passive","value":3.0,"resource":"stardust"},
    {"id":"mult1","name":"Resonance Field","base_cost":1000,"cost_mult":1.9,"type":"mult","value":0.1},
    {"id":"mult2","name":"Harmonic Lens","base_cost":10000,"cost_mult":2.0,"type":"mult","value":0.25},
    {"id":"mult3","name":"Quantum Echo","base_cost":100000,"cost_mult":2.1,"type":"mult","value":0.5},
    {"id":"special1","name":"Overclock Burst","base_cost":50000,"cost_mult":2.3,"type":"special","value":True},
    {"id":"special2","name":"Harvest Zone","base_cost":200000,"cost_mult":2.5,"type":"special","value":True},
    {"id":"synergy1","name":"Matter Link","base_cost":2500,"cost_mult":1.8,"type":"synergy","req":["passive1","passive2"],"value":0.2,"resource":"crystals"},
    {"id":"synergy2","name":"Cosmic Conduit","base_cost":75000,"cost_mult":2.0,"type":"synergy","req":["passive2","passive3"],"value":0.3,"resource":"plasma"},
    {"id":"synergy3","name":"Void Catalyst","base_cost":1_000_000,"cost_mult":2.2,"type":"synergy","req":["click3","mult2","passive3"],"value":0.4,"mult":True}
]

PARTICLE_COLORS = {
    "crystals": [(100,200,255), (150,220,255), (80,180,255)],
    "plasma": [(255,100,100), (255,150,100), (255,80,80)],
    "stardust": [(200,180,255), (220,200,255), (180,160,255)]
}
HARVEST_ZONE_LIFETIME = 5.0

def ensure_state_keys(s):
    defaults = {
        'crystals':0.0,'plasma':0.0,'stardust':0.0,
        'click_values':{r:BASE_CLICK_VALUE.get(r,0) for r in RESOURCE_TYPES},
        'passive_rates':{r:BASE_PASSIVE_RATE.get(r,0) for r in RESOURCE_TYPES},
        'mult':1.0,'prestige_level':0,'total_earned':0.0,
        'upgrade_levels':{u['id']:0 for u in UPGRADE_DEFS},
        'particles':[],'last_click':0.0,'harvest_zones':[],'overclock_until':0.0
    }
    for k,v in defaults.items():
        if k not in s: s[k] = v

def start():
    self.upgrade_defs = UPGRADE_DEFS
    if 'initialized' not in self.state:
        self.state.update({
            'crystals':0.0,'plasma':0.0,'stardust':0.0,
            'click_values':{r:BASE_CLICK_VALUE.get(r,0) for r in RESOURCE_TYPES},
            'passive_rates':{r:BASE_PASSIVE_RATE.get(r,0) for r in RESOURCE_TYPES},
            'mult':1.0,'prestige_level':0,'total_earned':0.0,
            'upgrade_levels':{u['id']:0 for u in self.upgrade_defs},
            'particles':[],'last_click':0.0,
            'harvest_zones':[],'overclock_until':0.0,
            'initialized':True
        })
    recalc_stats()

def recalc_stats():
    s = self.state
    prestige_bonus = 1.0 + s['prestige_level'] * 0.15
    s['click_values'] = {r: BASE_CLICK_VALUE.get(r,0) * prestige_bonus for r in RESOURCE_TYPES}
    s['passive_rates'] = {r: BASE_PASSIVE_RATE.get(r,0) * prestige_bonus for r in RESOURCE_TYPES}
    s['mult'] = 1.0
    for defn in self.upgrade_defs:
        level = s['upgrade_levels'].get(defn['id'], 0)
        if not level: continue
        value = defn['value'] * prestige_bonus
        if defn['type'] == 'click':
            s['click_values'][defn['resource']] += value * level
        elif defn['type'] == 'passive':
            s['passive_rates'][defn['resource']] += value * level
        elif defn['type'] == 'mult':
            s['mult'] += value * level
        elif defn['type'] == 'synergy':
            if 'resource' in defn:
                s['passive_rates'][defn['resource']] += value * level
            elif defn.get('mult'):
                s['mult'] += value * level

def buy_upgrade(defn):
    s = self.state
    level = s['upgrade_levels'][defn['id']]
    cost = defn['base_cost'] * (defn['cost_mult'] ** level)
    if s['crystals'] < cost: return
    s['crystals'] -= cost
    s['upgrade_levels'][defn['id']] = level + 1
    recalc_stats()

def prestige():
    s = self.state
    if s['total_earned'] < 10_000_000.0: return
    s['prestige_level'] += 1
    for r in RESOURCE_TYPES: s[r] = 0.0
    s['total_earned'] = 0.0
    s['upgrade_levels'] = {u['id']:0 for u in self.upgrade_defs}
    recalc_stats()

def on_click_main():
    s = self.state
    if time.time() - s['last_click'] < 0.05: return
    s['last_click'] = time.time()
    now = time.time()
    mult = s['mult'] * (2.0 if now < s['overclock_until'] else 1.0)
    base_gain = s['click_values']['crystals']
    gain = base_gain * mult
    s['crystals'] += gain
    s['total_earned'] += gain
    pos = self.app.camera.get_cursor_world_position()
    spawn_particles(pos, "crystals", gain)
    if s['upgrade_levels'].get('special2', 0):
        s['harvest_zones'].append({'pos':list(pos), 'expire':now + HARVEST_ZONE_LIFETIME})
    elif s['upgrade_levels'].get('special1', 0) and random.random() < 0.1:
        s['overclock_until'] = now + 3.0

def spawn_particles(pos, rtype, gain):
    count = min(30, max(5, int(math.log10(max(gain,1)) * 5)))
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(60, 120)
        vel = [math.cos(angle) * speed, math.sin(angle) * speed]
        life = random.uniform(0.8, 1.2)
        size = random.uniform(3, 8)
        color = random.choice(PARTICLE_COLORS[rtype])
        self.state['particles'].append(('circle', list(pos), vel, color, life, size, life))
    self.state['particles'].append(('text', list(pos), f"+{gain:,.1f}", 1.0, [random.uniform(-40, 40), -80]))

def update(dt):
    s = self.state
    ensure_state_keys(s)
    now = time.time()
    mult = s['mult'] * (2.0 if now < s['overclock_until'] else 1.0)
    for rtype in RESOURCE_TYPES:
        rate = s['passive_rates'][rtype] * mult
        s[rtype] += rate * dt
        if rtype != "crystals": s['total_earned'] += rate * dt
    s['mouse_pos'] = self.app.camera.get_cursor_world_position()
    new_particles = []
    for p in s['particles']:
        typ = p[0]
        if typ == 'circle':
            _, pos, vel, color, life, size, decay = p
            vel[1] += 150 * dt
            pos[0] += vel[0] * dt
            pos[1] += vel[1] * dt
            life -= dt
            if life > 0: new_particles.append((typ, pos, vel, color, life, size, decay))
        elif typ == 'text':
            _, pos, text, life, vel = p
            vel[1] += 30 * dt
            pos[0] += vel[0] * dt
            pos[1] += vel[1] * dt
            life -= dt
            if life > 0: new_particles.append((typ, pos, text, life, vel))
    s['particles'] = new_particles
    s['harvest_zones'] = [z for z in s['harvest_zones'] if z['expire'] > now]
    for zone in s['harvest_zones']:
        dist = math.hypot(s['mouse_pos'][0] - zone['pos'][0], s['mouse_pos'][1] - zone['pos'][1])
        if dist < 100:
            s['plasma'] += 0.5 * dt * s['mult']
            s['total_earned'] += 0.5 * dt * s['mult']
    draw_ui()

def draw_ui():
    s = self.state
    w, h = 1000, 1000
    y_off = 10
    for r in RESOURCE_TYPES:
        val = s[r]
        col = (100,200,255) if r=="crystals" else (255,100,100) if r=="plasma" else (200,180,255)
        Gizmos.draw_text((10, y_off), f"{r.capitalize()}: {val:,.1f}", color=col, world_space=True, font_world_space=True, font_size=24)
        y_off += 25
    Gizmos.draw_text((10, y_off), f"Multiplier: x{s['mult']:.2f}", color=(255,255,100), world_space=True, font_world_space=True, font_size=24)
    y_off += 25
    Gizmos.draw_text((10, y_off), f"Prestige: {s['prestige_level']} (Req: {max(0,10_000_000-s['total_earned']):,.0f})", color=(255,200,255), world_space=True, font_world_space=True, font_size=24)
    y_off += 30
    if s['overclock_until'] > time.time():
        Gizmos.draw_text((10, y_off), "⚡ OVERCLOCK ACTIVE", color=(255,100,100), world_space=True, font_world_space=True, font_size=22)
        y_off += 25
    btn_center = (w//2, h//2)
    Gizmos.draw_button(btn_center, "HARVEST", on_click_main, width=200, height=200, color=(255,255,255), background_color=(40,40,60,200), pressed_background_color=(80,80,120,200), world_space=True, font_world_space=True, font_size=24)
    shop_x = w - 250
    shop_y = 50
    for i, defn in enumerate(self.upgrade_defs):
        level = s['upgrade_levels'][defn['id']]
        cost = defn['base_cost'] * (defn['cost_mult'] ** level)
        buyable = s['crystals'] >= cost
        bonus = defn['value'] * (1 + s['prestige_level'] * 0.15)
        if defn['type'] == 'click':
            desc = f"+{bonus:.1f} {defn['resource']} per click"
        elif defn['type'] == 'passive':
            desc = f"+{bonus:.1f} {defn['resource']}/s"
        elif defn['type'] == 'mult':
            desc = f"+{bonus*100:.0f}% multiplier"
        elif defn['type'] == 'synergy':
            if 'resource' in defn:
                desc = f"↑ {defn['resource']} rate by {bonus:.1f}/s"
            else:
                desc = f"↑ Global mult by {bonus*100:.0f}%"
        else:
            desc = "Special effect"
        btn_y = shop_y + i * 120
        color = (200,200,200) if buyable else (100,100,100)
        if defn['type'] == 'synergy':
            req_met = all(s['upgrade_levels'].get(req,0) > 0 for req in defn.get('req',[]))
            if not req_met:
                color = (70,70,70)
                desc += "\n(Lock: " + ", ".join(defn['req']) + ")"
        Gizmos.draw_button((shop_x, btn_y), f"{defn['name']} Lv{level}\nCost: {cost:,.0f}\n{desc}", lambda d=defn: buy_upgrade(d), width=220, height=120, color=color, background_color=(30,30,40,220), world_space=True, font_world_space=True, font_size=18)
    if s['total_earned'] >= 10_000_000.0:
        Gizmos.draw_button((shop_x, shop_y + len(self.upgrade_defs) * 120), "ASCEND\nRESET & AMPLIFY", prestige, width=220, height=50, color=(255,255,100), background_color=(80,40,120,220), world_space=True, font_world_space=True)
    for p in s['particles']:
        if p[0] == 'circle':
            _, pos, _, color, life, size, decay = p
            alpha = min(255, int(255 * (life / decay)))
            rsize = max(1, int(size * (life / decay)))
            Gizmos.draw_circle(pos, rsize, color + (alpha,), world_space=True)
        elif p[0] == 'text':
            _, pos, text, life, _ = p
            alpha = min(255, int(255 * life))
            Gizmos.draw_text((pos[0], pos[1]), text, color=(255,255,255,alpha), world_space=True, font_world_space=True, font_size=24)
    for zone in s['harvest_zones']:
        Gizmos.draw_circle(zone['pos'], 100, (100,255,100,60), world_space=True)

def save_state():
    return {
        'crystals': self.state['crystals'],
        'plasma': self.state['plasma'],
        'stardust': self.state['stardust'],
        'prestige_level': self.state['prestige_level'],
        'total_earned': self.state['total_earned'],
        'upgrade_levels': self.state['upgrade_levels']
    }

def load_state(data):
    self.upgrade_defs = UPGRADE_DEFS
    self.state.update({
        'initialized': True,
        'crystals': data.get('crystals', 0.0),
        'plasma': data.get('plasma', 0.0),
        'stardust': data.get('stardust', 0.0),
        'prestige_level': data.get('prestige_level', 0),
        'total_earned': data.get('total_earned', 0.0),
        'upgrade_levels': data.get('upgrade_levels', {u['id']:0 for u in self.upgrade_defs}),
    })
    ensure_state_keys(self.state)
    recalc_stats()