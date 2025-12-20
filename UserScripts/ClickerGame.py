import math,random,time
RESOURCE_TYPES=["energy","nanites","exotic_matter","stellar_cores","quantum_data"]
BASE_CLICK_VALUE={"energy":0.0}
BASE_PASSIVE_RATE={"energy":1.0,"nanites":0.1,"exotic_matter":0.01,"stellar_cores":0.0,"quantum_data":0.0}
DYSON_SPHERE_TIER_COSTS=[1e6,1e9,1e12,1e15]
DYSON_SEGMENT_COST={"energy":1000,"nanites":100,"exotic_matter":10}
MAX_DYSON_SEGMENTS=1000000
DYSON_ENERGY_BASE=0.01
UPGRADE_DEFS=[{"id":"collector_adv","name":"Thermal Harvester","base_cost":500,"cost_mult":1.5,"type":"collector","tier":1,"output":{"energy":30.0}},{"id":"collector_quantum","name":"Quantum Fluctuation Tap","base_cost":5000,"cost_mult":1.6,"type":"collector","tier":2,"output":{"energy":200.0}},{"id":"nanite_swarm","name":"Nanite Swarm","base_cost":100,"cost_mult":1.45,"type":"passive","value":0.5,"resource":"nanites"},{"id":"matter_refinery","name":"Exotic Matter Refinery","base_cost":1000,"cost_mult":1.5,"type":"passive","value":0.3,"resource":"exotic_matter"},{"id":"stellar_forge","name":"Stellar Forge","base_cost":10000,"cost_mult":1.6,"type":"passive","value":0.1,"resource":"stellar_cores"},{"id":"data_miner","name":"Quantum Data Miner","base_cost":100000,"cost_mult":1.7,"type":"passive","value":0.02,"resource":"quantum_data"},{"id":"efficiency_core","name":"Efficiency Core","base_cost":2000,"cost_mult":1.9,"type":"mult","value":0.1},{"id":"resonance_matrix","name":"Resonance Matrix","base_cost":20000,"cost_mult":2.0,"type":"mult","value":0.25},{"id":"entropy_inverter","name":"Entropy Inverter","base_cost":200000,"cost_mult":2.1,"type":"mult","value":0.5},{"id":"overclock_pulse","name":"Overclock Pulse","base_cost":100000,"cost_mult":2.3,"type":"special","value":True},{"id":"harvest_field","name":"Harvest Field","base_cost":400000,"cost_mult":2.5,"type":"special","value":True},{"id":"nanite_link","name":"Nanite Link","base_cost":5000,"cost_mult":1.8,"type":"synergy","req":["nanite_swarm","collector_basic"],"value":0.2,"resource":"nanites"},{"id":"stellar_conduit","name":"Stellar Conduit","base_cost":150000,"cost_mult":2.0,"type":"synergy","req":["matter_refinery","stellar_forge"],"value":0.3,"resource":"stellar_cores"},{"id":"quantum_catalyst","name":"Quantum Catalyst","base_cost":2_000_000,"cost_mult":2.2,"type":"synergy","req":["collector_quantum","resonance_matrix","data_miner"],"value":0.4,"mult":True},{"id":"fabricator_alpha","name":"Matter Fabricator α","base_cost":1_000_000,"cost_mult":2.25,"type":"craft","value":{"input":{"nanites":20,"exotic_matter":5},"output":{"stellar_cores":1.0}}},{"id":"fabricator_omega","name":"Quantum Fabricator Ω","base_cost":4_000_000,"cost_mult":2.3,"type":"craft","value":{"input":{"stellar_cores":2,"quantum_data":1},"output":{"exotic_matter":50.0}}},{"id":"auto_nanite","name":"Nanite Constructor","base_cost":50000,"cost_mult":1.7,"type":"auto","value":{"resource":"nanites","rate":10.0}},{"id":"auto_exotic","name":"Exotic Synthesizer","base_cost":500000,"cost_mult":1.8,"type":"auto","value":{"resource":"exotic_matter","rate":3.0}},{"id":"tech_dyson","name":"Dyson Blueprint","base_cost":10_000_000,"cost_mult":2.0,"type":"research","value":"dyson_construction"},{"id":"tech_multiverse","name":"Parallel Universe Gate","base_cost":100_000_000,"cost_mult":2.5,"type":"research","value":"multiverse_access"},{"id":"trade_hub","name":"Interstellar Trade Hub","base_cost":30_000_000,"cost_mult":3.0,"type":"export","value":0.5}]
CRAFT_DEFS={u['id']:u for u in UPGRADE_DEFS if u['type']=='craft'}
AUTO_DEFS={u['id']:u for u in UPGRADE_DEFS if u['type']=='auto'}
RESEARCH_DEFS={u['id']:u for u in UPGRADE_DEFS if u['type']=='research'}
COLLECTOR_DEFS={u['id']:u for u in UPGRADE_DEFS if u['type']=='collector'}
PARTICLE_COLORS={"energy":[(255,255,100),(255,240,80),(255,230,60)],"nanites":[(100,200,255),(150,220,255),(80,180,255)],"exotic_matter":[(200,180,255),(220,200,255),(180,160,255)],"stellar_cores":[(255,100,100),(255,150,100),(255,80,80)],"quantum_data":[(80,255,200),(100,255,220),(60,230,180)]}
HARVEST_FIELD_LIFETIME=5.0
EVENT_DURATION=30.0
EVENTS=[{"name":"Solar Surge","mult":1.5,"duration":EVENT_DURATION,"resource":"energy"},{"name":"Nanite Bloom","mult":2.0,"duration":EVENT_DURATION,"resource":"nanites"},{"name":"Matter Storm","mult":3.0,"duration":EVENT_DURATION,"resource":"exotic_matter"},{"name":"Temporal Echo","mult":1.3,"duration":EVENT_DURATION,"resource":"quantum_data"}]
MARKET_BASE_PRICE={"energy":1,"nanites":5,"exotic_matter":50,"stellar_cores":500,"quantum_data":10000}
MARKET_VOLATILITY=0.3
MAX_MARKET_ITEMS=5
ACHIEVEMENTS=[{"id":"ach1","name":"Dyson Pioneer","cond":lambda s:s['dyson_progress']>=0.1},{"id":"ach2","name":"Multiverse Architect","cond":lambda s:s['prestige_level']>=1},{"id":"ach3","name":"Quantum Sovereign","cond":lambda s:s['quantum_data']>=10}]

def ensure_state_keys(s):
    defaults={'energy':0.0,'nanites':0.0,'exotic_matter':0.0,'stellar_cores':0.0,'quantum_data':0.0,'click_values':{r:BASE_CLICK_VALUE.get(r,0) for r in RESOURCE_TYPES},'passive_rates':{r:BASE_PASSIVE_RATE.get(r,0) for r in RESOURCE_TYPES},'mult':1.0,'prestige_level':0,'total_earned':0.0,'upgrade_levels':{u['id']:0 for u in UPGRADE_DEFS},'particles':[],'last_click':0.0,'harvest_fields':[],'overclock_until':0.0,'market_prices':{r:MARKET_BASE_PRICE[r] for r in RESOURCE_TYPES},'event_active':None,'event_end':0.0,'last_event':0.0,'achievements_unlocked':set(),'auto_jobs':[],'research_unlocked':set(),'market_access':False,'dyson_progress':0.0,'dyson_tier':0,'collector_jobs':[],'dyson_energy':0.0,'basic_collectors':0}
    for k,v in defaults.items():
        if k not in s:s[k]=v

def start():
    self.upgrade_defs=UPGRADE_DEFS
    if 'initialized' not in self.state:
        self.state.update({'energy':0.0,'nanites':0.0,'exotic_matter':0.0,'stellar_cores':0.0,'quantum_data':0.0,'click_values':{r:BASE_CLICK_VALUE.get(r,0) for r in RESOURCE_TYPES},'passive_rates':{r:BASE_PASSIVE_RATE.get(r,0) for r in RESOURCE_TYPES},'mult':1.0,'prestige_level':0,'total_earned':0.0,'upgrade_levels':{u['id']:0 for u in self.upgrade_defs},'particles':[],'last_click':0.0,'harvest_fields':[],'overclock_until':0.0,'market_prices':{r:MARKET_BASE_PRICE[r] for r in RESOURCE_TYPES},'event_active':None,'event_end':0.0,'last_event':0.0,'achievements_unlocked':set(),'auto_jobs':[],'research_unlocked':set(),'market_access':False,'dyson_progress':0.0,'dyson_tier':0,'collector_jobs':[],'dyson_energy':0.0,'basic_collectors':0,'initialized':True})
    recalc_stats()

def recalc_stats():
    s=self.state
    pb=1.0+s['prestige_level']*0.15
    s['click_values']={r:BASE_CLICK_VALUE.get(r,0)*pb for r in RESOURCE_TYPES}
    s['passive_rates']={r:BASE_PASSIVE_RATE.get(r,0)*pb for r in RESOURCE_TYPES}
    s['mult']=1.0
    s['auto_jobs']=[]
    s['collector_jobs']=[]
    for d in self.upgrade_defs:
        l=s['upgrade_levels'].get(d['id'],0)
        if not l:continue
        v=d.get('value')
        if d['type']=='passive':
            s['passive_rates'][d['resource']]+=v*l*pb
        elif d['type']=='mult':
            s['mult']+=v*l
        elif d['type']=='synergy':
            if 'resource' in d:
                s['passive_rates'][d['resource']]+=v*l
            elif d.get('mult'):
                s['mult']+=v*l
        elif d['type']=='auto':
            for _ in range(l):s['auto_jobs'].append(d['value'])
        elif d['type']=='collector':
            for _ in range(l):s['collector_jobs'].append(d)
        elif d['type']=='research':
            s['research_unlocked'].add(d['value'])
            if d['value']=='market':s['market_access']=True
    for _ in range(s['basic_collectors']):
        s['collector_jobs'].append({"output":{"energy":1.0},"type":"collector"})

def buy_upgrade(d):
    s=self.state
    l=s['upgrade_levels'][d['id']]
    c=d['base_cost']*(d['cost_mult']**l)
    if s['energy']<c:return
    s['energy']-=c
    s['upgrade_levels'][d['id']]=l+1
    recalc_stats()

def prestige():
    s=self.state
    if s['total_earned']<1e9 or s['dyson_progress']<1.0:return
    s['prestige_level']+=1
    for r in RESOURCE_TYPES:s[r]=0.0
    s['total_earned']=0.0
    s['dyson_progress']=0.0
    s['dyson_tier']=0
    s['dyson_energy']=0.0
    s['basic_collectors']=0
    s['upgrade_levels']={u['id']:0 for u in self.upgrade_defs}
    recalc_stats()

def craft(did):
    s=self.state
    d=CRAFT_DEFS[did]
    rcp=d['value']
    for res,amt in rcp['input'].items():
        if s[res]<amt*s['upgrade_levels'][did]:return
    for res,amt in rcp['input'].items():
        s[res]-=amt*s['upgrade_levels'][did]
    for res,amt in rcp['output'].items():
        s[res]+=amt*s['upgrade_levels'][did]

def trigger_random_event():
    s=self.state
    now=time.time()
    if s['event_active'] or now-s['last_event']<60:return
    s['event_active']=random.choice(EVENTS)
    s['event_end']=now+s['event_active']['duration']
    s['last_event']=now

def check_achievements():
    s=self.state
    for ach in ACHIEVEMENTS:
        if ach['id'] not in s['achievements_unlocked'] and ach['cond'](s):
            s['achievements_unlocked'].add(ach['id'])

def on_click_main():
    s=self.state
    if time.time()-s['last_click']<0.05:return
    s['last_click']=time.time()
    now=time.time()
    cost_e=100*(1.1**s['basic_collectors'])
    cost_n=10*(1.1**s['basic_collectors'])
    if s['energy']<cost_e or s['nanites']<cost_n:return
    s['energy']-=cost_e
    s['nanites']-=cost_n
    s['basic_collectors']+=1
    pos=self.app.camera.get_cursor_world_position()
    spawn_particles(pos,"nanites",s['basic_collectors'])
    if 'dyson_construction' in s['research_unlocked'] and random.random()<0.2:
        build_dyson_segment()
    trigger_random_event()
    check_achievements()
    recalc_stats()

def spawn_particles(pos,rtype,gain):
    cnt=min(30,max(5,int(math.log10(max(gain,1))*5)))
    for _ in range(cnt):
        a=random.uniform(0,2*math.pi)
        spd=random.uniform(60,120)
        vel=[math.cos(a)*spd,math.sin(a)*spd]
        life=random.uniform(0.8,1.2)
        sz=random.uniform(3,8)
        col=random.choice(PARTICLE_COLORS[rtype])
        self.state['particles'].append(('circle',list(pos),vel,col,life,sz,life))
    self.state['particles'].append(('text',list(pos),f"+{gain:,.1f}",1.0,[random.uniform(-40,40),-80]))

def update_market():
    s=self.state
    for r in RESOURCE_TYPES:
        vol=random.uniform(-MARKET_VOLATILITY,MARKET_VOLATILITY)
        s['market_prices'][r]=max(0.1,s['market_prices'][r]*(1.0+vol))

def sell_resource(res,amt):
    s=self.state
    if not s['market_access'] or s[res]<amt:return
    s[res]-=amt
    earn=amt*s['market_prices'][res]
    s['energy']+=earn
    s['total_earned']+=earn

def build_dyson_segment():
    s=self.state
    if 'dyson_construction' not in s['research_unlocked']:return
    t=s['dyson_tier']
    cm=10**(3*t)
    cost={res:base*cm for res,base in DYSON_SEGMENT_COST.items()}
    if any(s[res]<amt for res,amt in cost.items()):return
    for res,amt in cost.items():s[res]-=amt
    s['dyson_progress']=min(1.0,s['dyson_progress']+1.0/MAX_DYSON_SEGMENTS)
    if s['dyson_progress']>=1.0:
        s['dyson_tier']=min(3,s['dyson_tier']+1)
        s['dyson_progress']=0.0

def update(dt):
    s=self.state
    ensure_state_keys(s)
    now=time.time()
    if now-s['last_event']>10:trigger_random_event()
    m=s['mult']*(2.0 if now<s['overclock_until'] else 1.0)
    for rtype in RESOURCE_TYPES:
        rate=s['passive_rates'][rtype]*m
        if s['event_active'] and s['event_active']['resource']==rtype:
            rate*=s['event_active']['mult']
        s[rtype]+=rate*dt
        if rtype!="energy":s['total_earned']+=rate*dt
    for job in s['auto_jobs']:
        res=job['resource']
        rate=job['rate']*m
        if s['event_active'] and s['event_active']['resource']==res:
            rate*=s['event_active']['mult']
        s[res]+=rate*dt
        s['total_earned']+=rate*dt
    for job in s['collector_jobs']:
        for res,rate in job['output'].items():
            base_gain=rate*dt
            if base_gain==0:continue
            gain=base_gain*m
            if s['event_active'] and s['event_active']['resource']==res:
                gain*=s['event_active']['mult']
            s[res]+=gain
            s['total_earned']+=gain
    if s['dyson_tier']>0 or s['dyson_progress']>0:
        total_segs=s['dyson_tier']*MAX_DYSON_SEGMENTS+s['dyson_progress']*MAX_DYSON_SEGMENTS
        bps=DYSON_ENERGY_BASE*(10**s['dyson_tier'])
        dyson_pwr=total_segs*bps*dt*m
        if s['event_active'] and s['event_active']['resource']=='energy':
            dyson_pwr*=s['event_active']['mult']
        s['energy']+=dyson_pwr
        s['dyson_energy']+=dyson_pwr
        s['total_earned']+=dyson_pwr
    s['mouse_pos']=self.app.camera.get_cursor_world_position()
    new_particles=[]
    for p in s['particles']:
        typ=p[0]
        if typ=='circle':
            _,pos,vel,col,life,sz,decay=p
            vel[1]+=150*dt
            pos[0]+=vel[0]*dt
            pos[1]+=vel[1]*dt
            life-=dt
            if life>0:new_particles.append((typ,pos,vel,col,life,sz,decay))
        elif typ=='text':
            _,pos,txt,life,vel=p
            vel[1]+=30*dt
            pos[0]+=vel[0]*dt
            pos[1]+=vel[1]*dt
            life-=dt
            if life>0:new_particles.append((typ,pos,txt,life,vel))
    s['particles']=new_particles
    s['harvest_fields']=[z for z in s['harvest_fields'] if z['expire']>now]
    for zone in s['harvest_fields']:
        dist=math.hypot(s['mouse_pos'][0]-zone['pos'][0],s['mouse_pos'][1]-zone['pos'][1])
        if dist<100:
            gain=0.5*dt*m
            if s['event_active'] and s['event_active']['resource']=='nanites':
                gain*=s['event_active']['mult']
            s['nanites']+=gain
            s['total_earned']+=gain
    if random.random()<dt/5.0:update_market()
    draw_ui()

def draw_ui():
    s=self.state
    w,h=1000,1000
    y_off=10
    for r in RESOURCE_TYPES:
        val=s[r]
        col=(255,255,100) if r=="energy" else (100,200,255) if r=="nanites" else (200,180,255) if r=="exotic_matter" else (255,100,100) if r=="stellar_cores" else (80,255,200)
        Gizmos.draw_text((10,y_off),f"{r.replace('_',' ').title()}: {val:,.2f}",color=col,world_space=True,font_world_space=True,font_size=24)
        y_off+=25
    Gizmos.draw_text((10,y_off),f"Basic Collectors: {s['basic_collectors']}",color=(100,200,255),world_space=True,font_world_space=True,font_size=24)
    y_off+=25
    Gizmos.draw_text((10,y_off),f"Multiplier: x{s['mult']:.2f}",color=(255,255,100),world_space=True,font_world_space=True,font_size=24)
    y_off+=25
    Gizmos.draw_text((10,y_off),f"Dyson Sphere: Tier {s['dyson_tier']} — {s['dyson_progress']*100:.1f}%",color=(255,215,0),world_space=True,font_world_space=True,font_size=22)
    y_off+=25
    if s['dyson_energy']>0:
        Gizmos.draw_text((10,y_off),f"Sphere Output: {s['dyson_energy']:.1f} energy/s",color=(255,215,0),world_space=True,font_world_space=True,font_size=22)
        y_off+=25
    if s['event_active']:
        ev=s['event_active']
        ev_time=max(0,s['event_end']-time.time())
        Gizmos.draw_text((10,y_off),f"EVENT: {ev['name']} (+{ev['mult']:.1f}x {ev['resource']}) - {ev_time:.1f}s",color=(255,150,255),world_space=True,font_world_space=True,font_size=22)
        y_off+=25
    if s['overclock_until']>time.time():
        Gizmos.draw_text((10,y_off),"⚡ OVERCLOCK ACTIVE",color=(255,100,100),world_space=True,font_world_space=True,font_size=22)
        y_off+=25
    y_off+=10
    btn_center=(w//2,h//2)
    cost_e=100*(1.1**s['basic_collectors'])
    cost_n=10*(1.1**s['basic_collectors'])
    btn_txt=f"BUILD SOLAR COLLECTOR\nCost: {cost_e:,.0f}⚡ {cost_n:,.0f}N"
    Gizmos.draw_button(btn_center,btn_txt,on_click_main,width=200,height=200,color=(255,255,255),background_color=(40,40,60,200),pressed_background_color=(80,80,120,200),world_space=True,font_world_space=True,font_size=24)
    if 'dyson_construction' in s['research_unlocked']:
        t=s['dyson_tier']
        cm=10**(3*t)
        cost={res:base*cm for res,base in DYSON_SEGMENT_COST.items()}
        cost_str=', '.join([f"{v:,.0f} {k}" for k,v in cost.items()])
        Gizmos.draw_button((btn_center[0],btn_center[1]+250),f"BUILD DYSON SEGMENT\n({cost_str})",build_dyson_segment,width=220,height=60,color=(255,215,0),background_color=(60,40,0,200))
    shop_x=w-250
    shop_y=50
    for i,d in enumerate(self.upgrade_defs):
        l=s['upgrade_levels'][d['id']]
        c=d['base_cost']*(d['cost_mult']**l)
        buyable=s['energy']>=c
        bonus=d.get('value')
        if isinstance(bonus,(int,float)):
            bonus*=(1+s['prestige_level']*0.15)
        if d['type']=='collector':
            out_str=', '.join([f"{rate:.1f} {res}/s" for res,rate in d['output'].items()])
            desc=f"Output: {out_str}"
        elif d['type']=='passive':
            desc=f"+{bonus:.1f} {d['resource']}/s"
        elif d['type']=='mult':
            desc=f"+{bonus*100:.0f}% multiplier"
        elif d['type']=='synergy':
            if 'resource' in d:
                desc=f"↑ {d['resource']} rate by {bonus:.1f}/s"
            else:
                desc=f"↑ Global mult by {bonus*100:.0f}%"
        elif d['type']=='craft':
            inp=', '.join([f"{amt:.1f} {r}" for r,amt in d['value']['input'].items()])
            out=', '.join([f"{amt:.1f} {r}" for r,amt in d['value']['output'].items()])
            desc=f"CRAFT: {inp} → {out}"
            if l>0:
                Gizmos.draw_button((shop_x+120,shop_y+i*130+100),"CRAFT",lambda did=d['id']:craft(did),width=90,height=25,color=(100,255,100),background_color=(20,60,20,200))
        elif d['type']=='auto':
            rate=d['value']['rate']*(1+s['prestige_level']*0.15)
            desc=f"Auto-produce {rate:.1f} {d['value']['resource']}/s"
        elif d['type']=='research':
            desc=f"Unlock: {d['value'].replace('_',' ').title()}"
        elif d['type']=='export':
            desc=f"Trade hub: +{d['value']*100*(1+s['prestige_level']*0.15):.0f}% income"
        else:
            desc="Special effect"
        btn_y=shop_y+i*130
        col=(200,200,200) if buyable else (100,100,100)
        if d['type']=='synergy':
            req_met=all(s['upgrade_levels'].get(req,0)>0 for req in d.get('req',[]))
            if not req_met:
                col=(70,70,70)
                desc+="\n(Requires: "+", ".join(d['req'])+")"
        Gizmos.draw_button((shop_x,btn_y),f"{d['name']} Lv{l}\nCost: {c:,.0f}\n{desc}",lambda defn=d:buy_upgrade(defn),width=220,height=130,color=col,background_color=(30,30,40,220),world_space=True,font_world_space=True,font_size=18)
    if s['total_earned']>=1e9 and s['dyson_progress']>=1.0:
        btn_y=shop_y+len(self.upgrade_defs)*130
        Gizmos.draw_button((shop_x,btn_y),"CREATE\nPARALLEL UNIVERSE",prestige,width=220,height=60,color=(255,255,100),background_color=(80,40,120,220),world_space=True,font_world_space=True)
    if s['market_access']:
        market_y=shop_y+(len(self.upgrade_defs)+1)*130
        for i,(res,price) in enumerate(s['market_prices'].items()):
            if s[res]>0:
                btn_y=market_y+i*60
                Gizmos.draw_button((shop_x,btn_y),f"Sell {res.replace('_',' ').title()}\n({s[res]:,.1f} @ {price:,.1f})",lambda r=res:sell_resource(r,min(s[r],MAX_MARKET_ITEMS)),width=220,height=50,color=(255,200,100),background_color=(50,40,20,200))
    for p in s['particles']:
        if p[0]=='circle':
            _,pos,_,col,life,sz,decay=p
            alpha=min(255,int(255*(life/decay)))
            rsize=max(1,int(sz*(life/decay)))
            Gizmos.draw_circle(pos,rsize,col+(alpha,),world_space=True)
        elif p[0]=='text':
            _,pos,txt,life,_=p
            alpha=min(255,int(255*life))
            Gizmos.draw_text((pos[0],pos[1]),txt,color=(255,255,255,alpha),world_space=True,font_world_space=True,font_size=24)
    for zone in s['harvest_fields']:
        Gizmos.draw_circle(zone['pos'],100,(100,255,100,60),world_space=True)
    if s['dyson_tier']>0 or s['dyson_progress']>0:
        star_pos=(0,0)
        radius=150+s['dyson_tier']*80
        segs=int(MAX_DYSON_SEGMENTS*s['dyson_progress'])
        for i in range(segs):
            a=2*math.pi*i/MAX_DYSON_SEGMENTS
            x=star_pos[0]+math.cos(a)*radius
            y=star_pos[1]+math.sin(a)*radius
            Gizmos.draw_circle((x,y),8,(255,215,0,200),world_space=True)

def save_state():
    s=self.state
    return {'energy':s['energy'],'nanites':s['nanites'],'exotic_matter':s['exotic_matter'],'stellar_cores':s['stellar_cores'],'quantum_data':s['quantum_data'],'prestige_level':s['prestige_level'],'total_earned':s['total_earned'],'upgrade_levels':s['upgrade_levels'],'market_prices':s['market_prices'],'research_unlocked':list(s['research_unlocked']),'achievements_unlocked':list(s['achievements_unlocked']),'market_access':s['market_access'],'dyson_progress':s['dyson_progress'],'dyson_tier':s['dyson_tier'],'dyson_energy':s['dyson_energy'],'basic_collectors':s['basic_collectors']}

def load_state(data):
    self.upgrade_defs=UPGRADE_DEFS
    s=self.state
    s.update({'initialized':True,'energy':data.get('energy',0.0),'nanites':data.get('nanites',0.0),'exotic_matter':data.get('exotic_matter',0.0),'stellar_cores':data.get('stellar_cores',0.0),'quantum_data':data.get('quantum_data',0.0),'prestige_level':data.get('prestige_level',0),'total_earned':data.get('total_earned',0.0),'upgrade_levels':data.get('upgrade_levels',{u['id']:0 for u in self.upgrade_defs}),'market_prices':data.get('market_prices',{r:MARKET_BASE_PRICE[r] for r in RESOURCE_TYPES}),'research_unlocked':set(data.get('research_unlocked',[])),'achievements_unlocked':set(data.get('achievements_unlocked',[])),'market_access':data.get('market_access',False),'dyson_progress':data.get('dyson_progress',0.0),'dyson_tier':data.get('dyson_tier',0),'dyson_energy':data.get('dyson_energy',0.0),'basic_collectors':data.get('basic_collectors',0)})
    ensure_state_keys(s)
    recalc_stats()