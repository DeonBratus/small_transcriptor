import logging
import sys
from typing import Optional

def setup_logging(level: str = "INFO", service_name: str = "ai-judge") -> logging.Logger:
    """Настройка логирования для сервиса"""
    
    # Создаем логгер
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Удаляем существующие обработчики
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Создаем форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Файловый обработчик
    file_handler = logging.FileHandler(f'/app/logs/{service_name}.log')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

def log_error(logger: logging.Logger, error: Exception, context: str = "") -> None:
    """Логирование ошибок с контекстом"""
    error_msg = f"Error in {context}: {str(error)}" if context else str(error)
    logger.error(error_msg, exc_info=True)

def log_info(logger: logging.Logger, message: str, context: str = "") -> None:
    """Логирование информационных сообщений"""
    info_msg = f"{context}: {message}" if context else message
    logger.info(info_msg)
