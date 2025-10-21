import asyncio
import threading
import time
import queue
import uuid
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import traceback
import weakref
import json
import os


class ScriptPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class ScriptStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class ScriptTask:
    id: str
    script_id: str
    code: str
    priority: ScriptPriority = ScriptPriority.NORMAL
    status: ScriptStatus = ScriptStatus.PENDING
    created_time: float = field(default_factory=time.time)
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress: float = 0.0
    max_execution_time: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 0
    dependencies: List[str] = field(default_factory=list)
    callback: Optional[Callable] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())


class ScriptScheduler:
    def __init__(self, script_engine):
        self.script_engine = script_engine
        self.tasks = {}
        self.task_queue = queue.PriorityQueue()
        self.running_tasks = {}
        self.completed_tasks = {}
        
        self.max_concurrent_tasks = 10
        self.worker_threads = []
        self.shutdown_event = threading.Event()
        
        self._start_workers()
        
    def _start_workers(self):
        for i in range(min(4, self.max_concurrent_tasks)):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self.worker_threads.append(worker)
            
    def _worker_loop(self):
        while not self.shutdown_event.is_set():
            try:
                priority_item = self.task_queue.get(timeout=1.0)
                priority, task_id = priority_item
                
                if task_id not in self.tasks:
                    continue
                    
                task = self.tasks[task_id]
                
                if len(self.running_tasks) >= self.max_concurrent_tasks:
                    self.task_queue.put(priority_item)
                    time.sleep(0.1)
                    continue
                    
                if not self._check_dependencies(task):
                    self.task_queue.put(priority_item)
                    time.sleep(0.1)
                    continue
                    
                self._execute_task(task)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Worker error: {e}")
                
    def _check_dependencies(self, task: ScriptTask) -> bool:
        for dep_id in task.dependencies:
            if dep_id in self.running_tasks:
                return False
            if dep_id in self.tasks and self.tasks[dep_id].status != ScriptStatus.COMPLETED:
                return False
        return True
        
    def _execute_task(self, task: ScriptTask):
        try:
            task.status = ScriptStatus.RUNNING
            task.start_time = time.time()
            self.running_tasks[task.id] = task
            
            result = self.script_engine.execute_script(
                task.script_id, 
                task.code, 
                async_execution=False
            )
            
            task.result = result
            task.end_time = time.time()
            
            if result.get('success', False):
                task.status = ScriptStatus.COMPLETED
            else:
                task.status = ScriptStatus.FAILED
                task.error = result.get('error', 'Unknown error')
                
            if task.status == ScriptStatus.FAILED and task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = ScriptStatus.PENDING
                self.schedule_task(task)
                
        except Exception as e:
            task.status = ScriptStatus.FAILED
            task.error = str(e)
            task.end_time = time.time()
            
        finally:
            if task.id in self.running_tasks:
                del self.running_tasks[task.id]
            self.completed_tasks[task.id] = task
            
            if task.callback:
                try:
                    task.callback(task)
                except Exception as e:
                    print(f"Task callback error: {e}")
                    
    def schedule_task(self, task: ScriptTask) -> str:
        self.tasks[task.id] = task
        
        priority_value = 5 - task.priority.value
        self.task_queue.put((priority_value, task.id))
        
        return task.id
        
    def cancel_task(self, task_id: str) -> bool:
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status in [ScriptStatus.PENDING, ScriptStatus.PAUSED]:
                task.status = ScriptStatus.CANCELLED
                return True
        return False
        
    def get_task_status(self, task_id: str) -> Optional[ScriptTask]:
        return self.tasks.get(task_id) or self.completed_tasks.get(task_id)
        
    def get_running_tasks(self) -> List[ScriptTask]:
        return list(self.running_tasks.values())
        
    def get_pending_tasks(self) -> List[ScriptTask]:
        return [task for task in self.tasks.values() if task.status == ScriptStatus.PENDING]
        
    def shutdown(self):
        self.shutdown_event.set()
        for worker in self.worker_threads:
            worker.join(timeout=5.0)


class ScriptEventSystem:
    def __init__(self):
        self.listeners = {}
        self.event_history = []
        self.max_history = 1000
        
    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)
        
    def unsubscribe(self, event_type: str, callback: Callable):
        if event_type in self.listeners:
            try:
                self.listeners[event_type].remove(callback)
            except ValueError:
                pass
                
    def emit(self, event_type: str, data: Any = None):
        event = {
            'type': event_type,
            'data': data,
            'timestamp': time.time()
        }
        
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
            
        if event_type in self.listeners:
            for callback in self.listeners[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Event callback error: {e}")
                    
    def get_recent_events(self, event_type: str = None, limit: int = 100) -> List[Dict]:
        events = self.event_history
        if event_type:
            events = [e for e in events if e['type'] == event_type]
        return events[-limit:]


class ScriptPerformanceMonitor:
    def __init__(self):
        self.execution_stats = {}
        self.performance_history = []
        self.max_history = 1000
        
    def record_execution(self, script_id: str, execution_time: float, 
                        memory_usage: float = 0, success: bool = True):
        if script_id not in self.execution_stats:
            self.execution_stats[script_id] = {
                'total_executions': 0,
                'total_time': 0,
                'avg_time': 0,
                'min_time': float('inf'),
                'max_time': 0,
                'success_count': 0,
                'failure_count': 0,
                'last_execution': 0
            }
            
        stats = self.execution_stats[script_id]
        stats['total_executions'] += 1
        stats['total_time'] += execution_time
        stats['avg_time'] = stats['total_time'] / stats['total_executions']
        stats['min_time'] = min(stats['min_time'], execution_time)
        stats['max_time'] = max(stats['max_time'], execution_time)
        stats['last_execution'] = time.time()
        
        if success:
            stats['success_count'] += 1
        else:
            stats['failure_count'] += 1
            
        history_entry = {
            'script_id': script_id,
            'execution_time': execution_time,
            'memory_usage': memory_usage,
            'success': success,
            'timestamp': time.time()
        }
        
        self.performance_history.append(history_entry)
        if len(self.performance_history) > self.max_history:
            self.performance_history.pop(0)
            
    def get_stats(self, script_id: str) -> Optional[Dict]:
        return self.execution_stats.get(script_id)
        
    def get_top_performers(self, metric: str = 'avg_time', limit: int = 10) -> List[Dict]:
        items = []
        for script_id, stats in self.execution_stats.items():
            if metric in stats:
                items.append({
                    'script_id': script_id,
                    'value': stats[metric],
                    'stats': stats
                })
                
        items.sort(key=lambda x: x['value'])
        return items[:limit]


class AdvancedScriptManager:
    def __init__(self, script_engine, script_object_manager):
        self.script_engine = script_engine
        self.script_object_manager = script_object_manager
        
        self.scheduler = ScriptScheduler(script_engine)
        self.event_system = ScriptEventSystem()
        self.performance_monitor = ScriptPerformanceMonitor()
        
        self.script_templates = {}
        self.script_libraries = {}
        self.global_variables = {}
        
        self.auto_execution_rules = []
        self.script_dependencies = {}
        
        self._setup_event_handlers()
        self._load_builtin_templates()
        
    def _setup_event_handlers(self):
        # Subscribe to script execution events
        self.event_system.subscribe('script_executed', self._on_script_executed)
        self.event_system.subscribe('script_failed', self._on_script_failed)
        
    def _on_script_executed(self, event):
        data = event['data']
        script_id = data.get('script_id')
        execution_time = data.get('execution_time', 0)
        
        if script_id:
            self.performance_monitor.record_execution(
                script_id, execution_time, success=True
            )
            
    def _on_script_failed(self, event):
        data = event['data']
        script_id = data.get('script_id')
        execution_time = data.get('execution_time', 0)
        
        if script_id:
            self.performance_monitor.record_execution(
                script_id, execution_time, success=False
            )
            
    def _load_builtin_templates(self):
        self.script_templates = {
            'basic_animation': '''
# Basic Animation Template
import math
import time

start_time = time.time()
duration = 5.0  # seconds

while time.time() - start_time < duration:
    t = (time.time() - start_time) / duration
    
    # Animate a circle in a circle pattern
    radius = 100
    x = radius * math.cos(t * 2 * math.pi)
    y = radius * math.sin(t * 2 * math.pi)
    
    draw_circle((x, y), 10, 'red')
    
    time.sleep(0.016)  # ~60 FPS
''',
            
            'physics_interaction': '''
# Physics Interaction Template
bodies = get_bodies()

for body in bodies:
    # Apply upward force to all bodies
    body.force = (0, -1000)
    
log(f"Applied forces to {len(bodies)} bodies")
''',
            
            'sound_sequence': '''
# Sound Sequence Template
notes = ['C4', 'D4', 'E4', 'F4', 'G4', 'A4', 'B4', 'C5']
duration = 0.5

for note in notes:
    play_note(note, duration)
    time.sleep(duration)
    
log("Sound sequence completed")
''',
            
            'data_visualization': '''
# Data Visualization Template
import random

# Generate sample data
data = [random.randint(1, 100) for _ in range(10)]

# Draw bar chart
bar_width = 20
bar_spacing = 25
start_x = -200

for i, value in enumerate(data):
    x = start_x + i * bar_spacing
    height = value * 2
    
    # Draw bar
    draw_line((x, 0), (x, height), 'blue', bar_width)
    
    # Draw value label
    draw_text(str(value), (x, height + 10), 'white')
    
log(f"Visualized {len(data)} data points")
'''
        }
        
    def create_script_from_template(self, template_name: str, 
                                  parameters: Dict[str, Any] = None) -> str:
        if template_name not in self.script_templates:
            raise ValueError(f"Template '{template_name}' not found")
            
        template_code = self.script_templates[template_name]
        
        if parameters:
            for key, value in parameters.items():
                placeholder = f"{{{key}}}"
                template_code = template_code.replace(placeholder, str(value))
                
        return template_code
        
    def schedule_script_execution(self, script_id: str, code: str, 
                                priority: ScriptPriority = ScriptPriority.NORMAL,
                                delay: float = 0, 
                                dependencies: List[str] = None,
                                max_retries: int = 0,
                                callback: Callable = None) -> str:
        
        task = ScriptTask(
            id=str(uuid.uuid4()),
            script_id=script_id,
            code=code,
            priority=priority,
            max_retries=max_retries,
            dependencies=dependencies or [],
            callback=callback
        )
        
        if delay > 0:
            def delayed_schedule():
                time.sleep(delay)
                self.scheduler.schedule_task(task)
                
            threading.Thread(target=delayed_schedule, daemon=True).start()
        else:
            self.scheduler.schedule_task(task)
            
        return task.id
        
    def execute_script_with_monitoring(self, script_id: str, code: str) -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            result = self.script_engine.execute_script(script_id, code, False)
            execution_time = time.time() - start_time
            
            self.event_system.emit('script_executed', {
                'script_id': script_id,
                'execution_time': execution_time,
                'result': result
            })
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            self.event_system.emit('script_failed', {
                'script_id': script_id,
                'execution_time': execution_time,
                'error': str(e)
            })
            
            raise
            
    def add_auto_execution_rule(self, condition: Callable, script_code: str, 
                              cooldown: float = 1.0):
        rule = {
            'id': str(uuid.uuid4()),
            'condition': condition,
            'script_code': script_code,
            'cooldown': cooldown,
            'last_executed': 0
        }
        self.auto_execution_rules.append(rule)
        return rule['id']
        
    def remove_auto_execution_rule(self, rule_id: str):
        self.auto_execution_rules = [
            rule for rule in self.auto_execution_rules 
            if rule['id'] != rule_id
        ]
        
    def update(self, dt):
        current_time = time.time()
        
        for rule in self.auto_execution_rules:
            if current_time - rule['last_executed'] >= rule['cooldown']:
                try:
                    if rule['condition']():
                        self.execute_script_with_monitoring(
                            f"auto_rule_{rule['id']}", 
                            rule['script_code']
                        )
                        rule['last_executed'] = current_time
                except Exception as e:
                    print(f"Auto-execution rule error: {e}")
                    
    def get_performance_report(self) -> Dict[str, Any]:
        return {
            'total_scripts': len(self.performance_monitor.execution_stats),
            'total_executions': sum(
                stats['total_executions'] 
                for stats in self.performance_monitor.execution_stats.values()
            ),
            'top_performers': self.performance_monitor.get_top_performers(),
            'recent_events': self.event_system.get_recent_events(limit=50),
            'running_tasks': len(self.scheduler.get_running_tasks()),
            'pending_tasks': len(self.scheduler.get_pending_tasks())
        }
        
    def export_script_library(self, filepath: str):
        library_data = {
            'templates': self.script_templates,
            'libraries': self.script_libraries,
            'global_variables': self.global_variables,
            'performance_stats': self.performance_monitor.execution_stats,
            'export_time': time.time()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(library_data, f, indent=2, ensure_ascii=False)
            
    def import_script_library(self, filepath: str):
        with open(filepath, 'r', encoding='utf-8') as f:
            library_data = json.load(f)
            
        if 'templates' in library_data:
            self.script_templates.update(library_data['templates'])
            
        if 'libraries' in library_data:
            self.script_libraries.update(library_data['libraries'])
            
        if 'global_variables' in library_data:
            self.global_variables.update(library_data['global_variables'])
            
    def shutdown(self):
        self.scheduler.shutdown()

