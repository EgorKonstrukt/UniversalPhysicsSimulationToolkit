from UPST.script_system.script_engine import ScriptEngine
from UPST.script_system.script_object import ScriptObjectManager
from UPST.script_system.idle_integration import IDLEIntegrationManager
from UPST.script_system.script_ui_manager import ScriptUIManager
from UPST.script_system.script_save_integration import ScriptSaveManager, ScriptSaveIntegration
from UPST.script_system.advanced_script_manager import AdvancedScriptManager
from UPST.script_system.game_systems_integration import GameSystemsIntegration
import pygame


class ScriptSystemManager:
    def __init__(self, application):
        self.application = application
        
        self.game_systems_integration = GameSystemsIntegration(
            physics_manager=application.physics_manager,
            ui_manager=application.ui_manager,
            camera=application.camera,
            spawner=application.spawner,
            sound_manager=application.sound_manager,
            synthesizer=application.synthesizer,
            gizmos=application.gizmos_manager,
            debug=application.debug_manager,
            save_load_manager=application.save_load_manager,
            input_handler=application.input_handler,
            console=application.ui_manager.console_window
        )
        
        self.script_engine = ScriptEngine(
            physics_manager=application.physics_manager,
            ui_manager=application.ui_manager,
            camera=application.camera,
            spawner=application.spawner,
            sound_manager=application.sound_manager,
            synthesizer=application.synthesizer,
            gizmos=application.gizmos_manager,
            debug=application.debug_manager,
            save_load_manager=application.save_load_manager,
            input_handler=application.input_handler,
            console=application.ui_manager.console_window
        )
        
        enhanced_context = self.game_systems_integration.create_enhanced_context(
            self.script_engine.context
        )
        self.script_engine.global_namespace.update(enhanced_context)
        
        self.script_object_manager = ScriptObjectManager(self.script_engine)
        
        self.idle_integration = IDLEIntegrationManager(
            self.script_engine, 
            application.ui_manager
        )
        self.idle_integration.initialize()
        
        self.advanced_script_manager = AdvancedScriptManager(
            self.script_engine,
            self.script_object_manager
        )
        
        self.script_save_manager = ScriptSaveManager(
            self.script_object_manager,
            self.script_engine,
            self.idle_integration
        )
        
        self.save_integration = ScriptSaveIntegration(
            application.save_load_manager,
            self.script_save_manager
        )
        
        self.script_ui_manager = ScriptUIManager(
            application.ui_manager,
            self.script_object_manager,
            self.idle_integration
        )
        
        self._setup_event_handlers()
        
        self._load_example_scripts()
        
        print("Script System initialized successfully!")
        
    def _setup_event_handlers(self):
        self.advanced_script_manager.event_system.subscribe(
            'mouse_click', self._on_mouse_click
        )
        
        self.advanced_script_manager.event_system.subscribe(
            'key_press', self._on_key_press
        )
        
    def _on_mouse_click(self, event):
        mouse_pos = pygame.mouse.get_pos()
        world_pos = self.application.camera.screen_to_world(mouse_pos)
        
        selected = self.script_object_manager.select_object_at_position(world_pos)
        if selected:
            print(f"Selected script object: {selected.name}")
            
    def _on_key_press(self, event):
        key = event['data'].get('key')
        
        if key == pygame.K_F5:
            self.script_object_manager.execute_all_auto_run()
        elif key == pygame.K_F6:
            self.idle_integration.launch_idle()
        elif key == pygame.K_F7:
            if self.script_ui_manager.script_editor.is_visible():
                self.script_ui_manager.script_editor.hide()
            else:
                self.script_ui_manager.script_editor.show()
                
    def _load_example_scripts(self):
        examples = [
            {
                'name': 'Circle Spawner',
                'position': (100, 100),
                'code': '''
# Spawn circles in a pattern
import math
import time

for i in range(5):
    angle = i * (2 * math.pi / 5)
    x = 100 * math.cos(angle)
    y = 100 * math.sin(angle)
    
    spawn_circle((x, y), radius=20, color=(255, 100, 100, 255))
    play_note(f"C{4+i//2}", 0.2)
    time.sleep(0.1)

log_info("Circle pattern created!")
''',
                'auto_run': False
            },
            {
                'name': 'Physics Demo',
                'position': (-100, 100),
                'code': '''
# Physics demonstration
bodies = get_all_bodies()
log_info(f"Found {len(bodies)} bodies")

# Apply upward impulse to all bodies
for body in bodies:
    body.apply_impulse_at_world_point((0, -500), body.position)

# Create explosion at mouse position
mouse_pos = get_mouse_world_pos()
create_explosion(mouse_pos, 1000, 200)

# Draw explosion visualization
draw_circle(mouse_pos, 200, 'red', False, 3, True, 2.0)
draw_text("BOOM!", (mouse_pos[0], mouse_pos[1] - 50), 'yellow', 24, True, 2.0)
''',
                'auto_run': False
            },
            {
                'name': 'Music Generator',
                'position': (0, -100),
                'code': '''
# Generate a random melody
import random

scales = {
    'major': [0, 2, 4, 5, 7, 9, 11],
    'minor': [0, 2, 3, 5, 7, 8, 10],
    'pentatonic': [0, 2, 4, 7, 9]
}

scale = scales['pentatonic']
base_note = 60  # Middle C

melody = []
for i in range(8):
    note_offset = random.choice(scale)
    octave_offset = random.choice([0, 12, 24])
    frequency = 440 * (2 ** ((base_note + note_offset + octave_offset - 69) / 12))
    melody.append(frequency)

# Play the melody
for freq in melody:
    play_frequency(freq, 0.3, waveform='sine')
    time.sleep(0.35)

log_info("Random melody played!")
''',
                'auto_run': False
            },
            {
                'name': 'Visual Art',
                'position': (200, -100),
                'code': '''
# Create visual art with gizmos
import math

center = (0, 0)
layers = 5
points_per_layer = 12

for layer in range(layers):
    radius = 50 + layer * 30
    color_hue = layer * 60  # Different colors for each layer
    
    # Convert HSV to RGB (simplified)
    if color_hue < 60:
        color = 'red'
    elif color_hue < 120:
        color = 'yellow'
    elif color_hue < 180:
        color = 'green'
    elif color_hue < 240:
        color = 'cyan'
    elif color_hue < 300:
        color = 'blue'
    else:
        color = 'magenta'
    
    # Draw points in a circle
    for i in range(points_per_layer):
        angle = i * (2 * math.pi / points_per_layer)
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        
        # Draw line from center to point
        draw_line(center, (x, y), color, 2, True, 10.0)
        
        # Draw small circle at point
        draw_circle((x, y), 5, color, True, 1, True, 10.0)

# Draw center
draw_circle(center, 10, 'white', True, 1, True, 10.0)
draw_text("Art Generator", (center[0], center[1] - 200), 'white', 20, True, 10.0)

log_info("Visual art created!")
''',
                'auto_run': False
            }
        ]
        
        for example in examples:
            script_obj = self.script_object_manager.create_script_object(**example)
            print(f"Created example script: {script_obj.name}")
            
    def handle_event(self, event):
        self.script_ui_manager.handle_event(event)
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.advanced_script_manager.event_system.emit('mouse_click', {
                'button': event.button,
                'pos': event.pos
            })
        elif event.type == pygame.KEYDOWN:
            self.advanced_script_manager.event_system.emit('key_press', {
                'key': event.key
            })
            
    def update(self, dt):
        self.script_object_manager.update(dt)
        self.script_engine.update(dt)
        self.advanced_script_manager.update(dt)
        self.script_save_manager.update(dt)
        self.script_ui_manager.update(dt)
        
    def draw(self, screen):
        self.script_object_manager.draw_all(
            screen, 
            self.application.camera, 
            self.application.font
        )
        self.script_ui_manager.draw(screen)
        
    def shutdown(self):
        self.advanced_script_manager.shutdown()
        self.idle_integration.shutdown()
        self.save_integration.restore_original_methods()
        
        print("Script System shutdown complete!")


def integrate_script_system(application):
    """
    Helper function to integrate the script system into an existing application.
    
    Args:
        application: The main application instance with required components
    
    Returns:
        ScriptSystemManager: The initialized script system manager
    """
    
    required_components = [
        'physics_manager', 'ui_manager', 'camera', 'spawner',
        'sound_manager', 'synthesizer', 'gizmos_manager',
        'debug_manager', 'save_load_manager', 'input_handler'
    ]
    
    for component in required_components:
        if not hasattr(application, component):
            raise AttributeError(f"Application missing required component: {component}")
            
    script_system = ScriptSystemManager(application)
    
    application.script_system = script_system
    
    return script_system


EXAMPLE_SCRIPTS = {
    'hello_world': '''
# Hello World Script
log_info("Hello from the script system!")
draw_text("Hello World!", (0, 0), 'white', 24, True, 3.0)
play_note('C4', 1.0)
''',
    
    'interactive_demo': '''
# Interactive Demo Script
mouse_pos = get_mouse_world_pos()
log_info(f"Mouse position: {mouse_pos}")

# Spawn object at mouse position
body = spawn_circle(mouse_pos, radius=25, color=(100, 255, 100, 255))

# Play sound based on position
frequency = 440 + (mouse_pos[0] / 10)
play_frequency(frequency, 0.5)

# Draw indicator
draw_arrow((0, 0), mouse_pos, 'yellow', 3, 15, True, 2.0)
''',
    
    'physics_playground': '''
# Physics Playground Script
import random

# Create a chain of connected objects
start_pos = (-200, 0)
end_pos = (200, 0)
chain = spawn_chain(start_pos, end_pos, segments=8, segment_mass=2.0)

# Add some random forces
for body in chain:
    force_x = random.uniform(-100, 100)
    force_y = random.uniform(-200, 0)
    body.apply_impulse_at_world_point((force_x, force_y), body.position)

# Create gravity well at center
create_gravity_well((0, -100), 500, 150)

# Visualize gravity well
draw_circle((0, -100), 150, 'purple', False, 2, True, 5.0)
draw_text("Gravity Well", (0, -200), 'purple', 16, True, 5.0)

log_info("Physics playground created!")
''',
    
    'audio_visualizer': '''
# Audio Visualizer Script
import math

# Create visual representation of sound
frequencies = [220, 261.63, 329.63, 392, 440, 523.25, 659.25, 783.99]
note_names = ['A3', 'C4', 'E4', 'G4', 'A4', 'C5', 'E5', 'G5']

for i, (freq, note) in enumerate(zip(frequencies, note_names)):
    # Calculate position
    angle = i * (2 * math.pi / len(frequencies))
    radius = 100
    x = radius * math.cos(angle)
    y = radius * math.sin(angle)
    
    # Draw frequency bar
    bar_height = freq / 10
    draw_line((x, y), (x, y - bar_height), 'cyan', 5, True, 3.0)
    
    # Draw note label
    draw_text(note, (x, y + 20), 'white', 12, True, 3.0)
    
    # Play note
    play_note(note, 0.3)
    time.sleep(0.1)

# Draw center circle
draw_circle((0, 0), 10, 'white', True, 1, True, 3.0)
draw_text("Audio Visualizer", (0, -150), 'cyan', 20, True, 3.0)

log_info("Audio visualization complete!")
'''
}

