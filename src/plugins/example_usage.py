"""
Пример использования новой системы плагинов с IoC контейнером
"""
from rodi import Container
from voice_assistant.interfaces.container import create_container, create_service_container
from voice_assistant.infrastructure.plugins.plugin_interface import ASRPlugin, NLUPlugin, TTSPlugin
from plugins.config import get_enabled_plugin_configs, get_default_plugin


async def example_usage():
    """Пример использования плагинов через IoC контейнер"""
    
    # Создаем контейнер с плагинами (используя конфигурацию по умолчанию)
    container = create_container()
    
    # Получаем сервисы через интерфейсы
    try:
        # ASR сервис
        asr_service = container.resolve(ASRPlugin)
        print(f"ASR Service: {type(asr_service).__name__}")
        
        # NLU сервис
        nlu_service = container.resolve(NLUPlugin)
        print(f"NLU Service: {type(nlu_service).__name__}")
        
        # TTS сервис
        tts_service = container.resolve(TTSPlugin)
        print(f"TTS Service: {type(tts_service).__name__}")
        
        # Пример использования NLU
        if nlu_service:
            result = await nlu_service.classify_intent("добавь молоко в список покупок")
            print(f"Intent: {result.name}, Confidence: {result.confidence}")
        
        # Пример использования TTS
        if tts_service:
            audio_data = await tts_service.synthesize("Привет, это тест синтеза речи")
            print(f"Generated audio: {len(audio_data)} bytes")
            
    except Exception as e:
        print(f"Error resolving services: {e}")


async def example_direct_component_access():
    """Пример прямого доступа к компонентам плагинов"""
    
    container = create_container()
    
    try:
        # Прямой доступ к sklearn Pipeline (если зарегистрирован)
        try:
            from sklearn.pipeline import Pipeline
            pipeline = container.resolve(Pipeline)
            print(f"ML Pipeline: {pipeline}")
        except Exception:
            print("sklearn Pipeline not available")
        
        # Прямой доступ к Vosk Model (если зарегистрирован)
        try:
            from vosk import Model
            vosk_model = container.resolve(Model)
            print(f"Vosk Model: {vosk_model}")
        except Exception:
            print("Vosk Model not available")
        
        # Прямой доступ к конфигурации
        try:
            nlu_config = container.resolve(dict, name="nlu_config")
            print(f"NLU Config: {nlu_config}")
        except Exception:
            print("NLU Config not available")
        
    except Exception as e:
        print(f"Error accessing components: {e}")


async def example_service_specific_container():
    """Пример создания контейнера для конкретного сервиса"""
    
    print("=== ASR Service Container ===")
    asr_container = create_service_container("asr_service")
    
    try:
        asr_service = asr_container.resolve(ASRPlugin)
        print(f"ASR Service: {type(asr_service).__name__}")
    except Exception as e:
        print(f"ASR Service not available: {e}")
    
    print("\n=== NLU Service Container ===")
    nlu_container = create_service_container("nlu_service")
    
    try:
        nlu_service = nlu_container.resolve(NLUPlugin)
        print(f"NLU Service: {type(nlu_service).__name__}")
    except Exception as e:
        print(f"NLU Service not available: {e}")


def example_configuration():
    """Пример работы с конфигурацией плагинов"""
    
    print("=== Plugin Configuration ===")
    
    # Получить все включенные плагины
    enabled_configs = get_enabled_plugin_configs()
    print(f"Enabled plugins: {list(enabled_configs.keys())}")
    
    # Получить плагины по умолчанию
    default_asr = get_default_plugin("asr")
    default_nlu = get_default_plugin("nlu")
    default_tts = get_default_plugin("tts")
    
    print(f"Default ASR: {default_asr}")
    print(f"Default NLU: {default_nlu}")
    print(f"Default TTS: {default_tts}")


if __name__ == "__main__":
    import asyncio
    
    print("=== Конфигурация плагинов ===")
    example_configuration()
    
    print("\n=== Пример использования плагинов ===")
    asyncio.run(example_usage())
    
    print("\n=== Пример прямого доступа к компонентам ===")
    asyncio.run(example_direct_component_access())
    
    print("\n=== Пример сервис-специфичных контейнеров ===")
    asyncio.run(example_service_specific_container())