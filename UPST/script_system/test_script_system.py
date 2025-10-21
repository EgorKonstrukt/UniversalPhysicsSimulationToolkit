#!/usr/bin/env python3

import sys
import traceback


def test_imports():
    """Тест импорта всех модулей системы скриптинга"""
    print("=== Тестирование импортов ===")
    
    modules = [
        'script_engine',
        'script_object', 
        'idle_integration',
        'script_ui_manager',
        'script_save_integration',
        'advanced_script_manager',
        'game_systems_integration',
        'script_system_main'
    ]
    
    success_count = 0
    
    for module in modules:
        try:
            __import__(module)
            print(f"✓ {module}")
            success_count += 1
        except ImportError as e:
            print(f"✗ {module}: {e}")
        except Exception as e:
            print(f"✗ {module}: Unexpected error - {e}")
    
    print(f"\nИмпорт модулей: {success_count}/{len(modules)} успешно")
    return success_count == len(modules)

def test_script_engine():
    """Тест базового движка скриптинга"""
    print("\n=== Тестирование ScriptEngine ===")
    
    try:
        from script_engine import ScriptEngine, ScriptContext
        
        # Создаем мок-объекты для тестирования
        class MockManager:
            def __init__(self):
                pass
                
        mock_manager = MockManager()
        
        # Создаем движок
        engine = ScriptEngine(
            physics_manager=mock_manager,
            ui_manager=mock_manager,
            camera=mock_manager,
            spawner=mock_manager,
            sound_manager=mock_manager,
            synthesizer=mock_manager,
            gizmos=mock_manager,
            debug=mock_manager,
            save_load_manager=mock_manager,
            input_handler=mock_manager,
            console=mock_manager
        )
        
        # Тест выполнения простого кода
        result = engine.execute_script("test", "x = 2 + 2\nprint(f'Result: {x}')")
        
        if result['success']:
            print("✓ Выполнение простого скрипта")
        else:
            print(f"✗ Ошибка выполнения: {result.get('error')}")
            
        # Тест синтаксической ошибки
        result = engine.execute_script("test_error", "invalid syntax here")
        
        if not result['success']:
            print("✓ Обработка синтаксических ошибок")
        else:
            print("✗ Синтаксические ошибки не обрабатываются")
            
        engine.shutdown()
        print("✓ ScriptEngine работает корректно")
        return True
        
    except Exception as e:
        print(f"✗ ScriptEngine error: {e}")
        traceback.print_exc()
        return False

def test_script_object():
    """Тест скрипт-объектов"""
    print("\n=== Тестирование ScriptObject ===")
    
    try:
        from script_object import ScriptObject, ScriptObjectManager
        from script_engine import ScriptEngine
        
        # Создаем мок-движок
        class MockEngine:
            def execute_script(self, script_id, code, async_exec=False):
                return {'success': True, 'output': 'Test output', 'execution_time': 0.001}
            def get_script_status(self, script_id):
                return {'status': 'completed'}
            def stop_script(self, script_id):
                return True
                
        mock_engine = MockEngine()
        
        # Создаем скрипт-объект
        script_obj = ScriptObject(
            position=(100, 100),
            name="Test Script",
            code="print('Hello World')",
            script_engine=mock_engine
        )
        
        # Тест сериализации
        data = script_obj.to_dict()
        restored_obj = ScriptObject.from_dict(data, mock_engine)
        
        if restored_obj.name == script_obj.name:
            print("✓ Сериализация скрипт-объектов")
        else:
            print("✗ Ошибка сериализации")
            
        # Тест выполнения
        result = script_obj.execute()
        if result['success']:
            print("✓ Выполнение скрипт-объектов")
        else:
            print("✗ Ошибка выполнения скрипт-объекта")
            
        print("✓ ScriptObject работает корректно")
        return True
        
    except Exception as e:
        print(f"✗ ScriptObject error: {e}")
        traceback.print_exc()
        return False

def test_idle_integration():
    """Тест интеграции IDLE"""
    print("\n=== Тестирование IDLE Integration ===")
    
    try:
        from idle_integration import IDLEBridge, IDLEIntegrationManager
        
        class MockEngine:
            def execute_script(self, script_id, code, async_exec=False):
                return {'success': True, 'output': 'IDLE test output'}
                
        mock_engine = MockEngine()
        
        integration = IDLEIntegrationManager(mock_engine, None)
        
        bridge = IDLEBridge(mock_engine)
        startup_script = bridge.create_idle_startup_script()
        
        if 'UPSTGameBridge' in startup_script:
            print("✓ Создание стартового скрипта IDLE")
        else:
            print("✗ Ошибка создания стартового скрипта")
            
        bridge.cleanup()
        print("✓ IDLE Integration работает корректно")
        return True
        
    except Exception as e:
        print(f"✗ IDLE Integration error: {e}")
        traceback.print_exc()
        return False

def test_save_system():
    """Тест системы сохранений"""
    print("\n=== Тестирование Save System ===")
    
    try:
        from script_save_integration import ScriptSaveManager, ScriptSaveData
        from script_object import ScriptObjectManager
        
        class MockEngine:
            def __init__(self):
                self.running_scripts = {}
                self.script_outputs = {}
                self.global_namespace = {}
                
        class MockIntegration:
            def __init__(self):
                self.integration_enabled = True
                self.executed_codes = []
            def is_idle_running(self):
                return False
                
        mock_engine = MockEngine()
        mock_integration = MockIntegration()
        
        object_manager = ScriptObjectManager(mock_engine)
        
        save_manager = ScriptSaveManager(object_manager, mock_engine, mock_integration)
        
        result = save_manager.save_scripts_data()
        
        if result['success']:
            print("✓ Сохранение данных скриптов")
        else:
            print(f"✗ Ошибка сохранения: {result.get('error')}")
            
        result = save_manager.load_scripts_data(result['data'])
        
        if result['success']:
            print("✓ Загрузка данных скриптов")
        else:
            print(f"✗ Ошибка загрузки: {result.get('error')}")
            
        print("✓ Save System работает корректно")
        return True
        
    except Exception as e:
        print(f"✗ Save System error: {e}")
        traceback.print_exc()
        return False

def test_game_integration():
    """Тест интеграции с игровыми системами"""
    print("\n=== Тестирование Game Integration ===")
    
    try:
        from game_systems_integration import GameSystemsIntegration, GizmosAPI, SpawnerAPI
        
        class MockSystem:
            def __init__(self):
                pass
                
        mock_system = MockSystem()
        
        integration = GameSystemsIntegration(
            physics_manager=mock_system,
            ui_manager=mock_system,
            camera=mock_system,
            spawner=mock_system,
            sound_manager=mock_system,
            synthesizer=mock_system,
            gizmos=mock_system,
            debug=mock_system,
            save_load_manager=mock_system,
            input_handler=mock_system,
            console=mock_system
        )
        
        class MockContext:
            def __init__(self):
                self.__dict__ = {}
                
        mock_context = MockContext()
        enhanced_context = integration.create_enhanced_context(mock_context)
        
        required_functions = [
            'draw_line', 'draw_circle', 'spawn_circle', 'play_note',
            'get_all_bodies', 'set_gravity', 'log_info'
        ]
        
        missing_functions = []
        for func in required_functions:
            if func not in enhanced_context:
                missing_functions.append(func)
                
        if not missing_functions:
            print("✓ Создание расширенного контекста")
        else:
            print(f"✗ Отсутствуют функции: {missing_functions}")
            
        print("✓ Game Integration работает корректно")
        return True
        
    except Exception as e:
        print(f"✗ Game Integration error: {e}")
        traceback.print_exc()
        return False

def test_advanced_manager():
    """Тест расширенного менеджера"""
    print("\n=== Тестирование Advanced Manager ===")
    
    try:
        from UPST.script_system.advanced_script_manager import AdvancedScriptManager, ScriptScheduler, ScriptEventSystem
        
        class MockEngine:
            def execute_script(self, script_id, code, async_exec=False):
                return {'success': True, 'output': 'Test', 'execution_time': 0.001}
            def update(self, dt):
                pass
                
        class MockObjectManager:
            def get_all_script_objects(self):
                return []
                
        mock_engine = MockEngine()
        mock_object_manager = MockObjectManager()
        
        manager = AdvancedScriptManager(mock_engine, mock_object_manager)
        
        event_fired = False
        def test_callback(event):
            nonlocal event_fired
            event_fired = True
            
        manager.event_system.subscribe('test_event', test_callback)
        manager.event_system.emit('test_event', {'data': 'test'})
        
        if event_fired:
            print("✓ Система событий")
        else:
            print("✗ Ошибка системы событий")
            
        template_code = manager.create_script_from_template('basic_animation')
        
        if 'math' in template_code and 'time' in template_code:
            print("✓ Система шаблонов")
        else:
            print("✗ Ошибка системы шаблонов")
            
        manager.shutdown()
        print("✓ Advanced Manager работает корректно")
        return True
        
    except Exception as e:
        print(f"✗ Advanced Manager error: {e}")
        traceback.print_exc()
        return False

def main():
    """Основная функция тестирования"""
    print("UPST Python Scripting System - Тестирование")
    print("=" * 50)
    
    tests = [
        ("Импорт модулей", test_imports),
        ("Script Engine", test_script_engine),
        ("Script Object", test_script_object),
        ("IDLE Integration", test_idle_integration),
        ("Save System", test_save_system),
        ("Game Integration", test_game_integration),
        ("Advanced Manager", test_advanced_manager)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {test_name}: Критическая ошибка - {e}")
    
    print("\n" + "=" * 50)
    print(f"РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты пройдены успешно!")
        print("Система скриптинга готова к использованию.")
    else:
        print("⚠️  Некоторые тесты не пройдены.")
        print("Проверьте ошибки выше и убедитесь, что все зависимости установлены.")
    
    print("\nДля запуска игры с системой скриптинга:")
    print("python UPST.py")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

