"""
Logging configuration for Redis test application.
"""

import logging
import sys
from pathlib import Path


class RedisTestLogger:
    """Centralized logging configuration for the Redis test application."""

    def __init__(self, log_level: str = "INFO", log_file: str = None):
        self.log_level = getattr(logging, log_level.upper())
        self.log_file = log_file
        self.logger = None
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging configuration with both console and file handlers."""
        # Create logger
        self.logger = logging.getLogger("redis_test")
        self.logger.setLevel(self.log_level)

        # Clear any existing handlers
        self.logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s"
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # File handler (if specified)
        if self.log_file:
            # Create logs directory if it doesn't exist
            log_path = Path(self.log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(self.log_file)
            file_handler.setLevel(self.log_level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        # Prevent propagation to root logger
        self.logger.propagate = False

        # Setup redis-py library loggers to capture internal debug logs
        # redis-py uses several specific logger names
        redis_loggers = [
            "redis",  # Main redis logger
            "redis.credentials",  # Credentials-related logging
            "push_response",  # Push responses (maintenance notifications, etc.)
            "redis.maint_notifications",  # Maintenance notifications
        ]
        for logger_name in redis_loggers:
            redis_logger = logging.getLogger(logger_name)
            redis_logger.setLevel(self.log_level)
            redis_logger.handlers.clear()
            redis_logger.addHandler(console_handler)
            if self.log_file:
                redis_logger.addHandler(file_handler)
            redis_logger.propagate = False

    def get_logger(self) -> logging.Logger:
        """Get the configured logger instance."""
        return self.logger

    def log_error_with_traceback(self, message: str, exception: Exception = None):
        """Log error with full traceback."""
        if exception:
            self.logger.error(f"{message}: {str(exception)}", exc_info=True)
        else:
            self.logger.error(message, exc_info=True)

    def log_operation_result(
        self, operation: str, success: bool, duration: float, error: str = None
    ):
        """Log operation result with standardized format."""
        status = "SUCCESS" if success else "FAILED"
        message = (
            f"Operation: {operation} | Status: {status} | Duration: {duration:.4f}s"
        )

        if success:
            self.logger.debug(message)
        else:
            message += f" | Error: {error}" if error else ""
            self.logger.error(message)

    def log_connection_event(self, event_type: str, details: dict):
        """Log connection-related events."""
        message = f"Connection {event_type}: {details}"
        if event_type in ["FAILED", "LOST", "ERROR"]:
            self.logger.error(message)
        else:
            self.logger.info(message)


# Global logger instance
_logger_instance = None


def get_logger() -> logging.Logger:
    """Get the global logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = RedisTestLogger()
    return _logger_instance.get_logger()


def setup_logging(log_level: str = "INFO", log_file: str = None) -> RedisTestLogger:
    """Setup global logging configuration."""
    global _logger_instance
    _logger_instance = RedisTestLogger(log_level, log_file)
    return _logger_instance


def log_error_with_traceback(message: str, exception: Exception = None):
    """Convenience function to log errors with traceback."""
    global _logger_instance
    if _logger_instance:
        _logger_instance.log_error_with_traceback(message, exception)
    else:
        logging.error(
            f"{message}: {str(exception) if exception else ''}", exc_info=True
        )
