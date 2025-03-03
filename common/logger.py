import logging
import sys
import os

class Logger:
    """
    Centralized logging functionality for the Krypto application.
    Combines logging configuration and message formatting.
    """
    
    # Standard log colors (ANSI escape codes)
    COLORS = {
        'RESET': '\033[0m',
        'BLACK': '\033[30m',
        'RED': '\033[31m',
        'GREEN': '\033[32m',
        'YELLOW': '\033[33m',
        'BLUE': '\033[34m',
        'MAGENTA': '\033[35m',
        'CYAN': '\033[36m',
        'WHITE': '\033[37m',
        'BOLD': '\033[1m',
        'UNDERLINE': '\033[4m',
    }
    
    # Column widths for aligned logging
    SENDER_WIDTH = 25
    MESSAGE_WIDTH = 50
    
    @staticmethod
    def configure(debug=False):
        """
        Configure logging for the application
        
        Args:
            debug (bool): Whether to enable debug logging
        """
        # Set the root logger level based on debug flag
        level = logging.DEBUG if debug else logging.INFO
        
        # Clear existing handlers to avoid duplicate logs
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        # Format with timestamp (no year, no milliseconds) and module name
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%m-%d %H:%M:%S'  # This format removes year and milliseconds
        )
        console_handler.setFormatter(formatter)
        
        # Add the handler to the root logger
        root.setLevel(level)
        root.addHandler(console_handler)
        
        return root
    
    @staticmethod
    def get(name, debug=False):
        """
        Get a properly configured logger for a specific component
        
        Args:
            name (str): Name of the component (appears in logs)
            debug (bool): Enable debug mode
            
        Returns:
            logging.Logger: Configured logger
        """
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG if debug else logging.INFO)
        return logger
    
    @staticmethod
    def log_incoming(logger, source, message):
        """
        Log an incoming message
        
        Args:
            logger: Logger to use
            source: Source of the message
            message: Message content
        """
        if isinstance(logger, logging.Logger):
            logger.debug(f"<< FROM {source}: {message}")
        else:
            # If a logging module was passed instead of a logger
            logging.getLogger("LogHelper").debug(f"<< FROM {source}: {message}")
    
    @staticmethod
    def log_outgoing(logger, destination, message):
        """
        Log an outgoing message
        
        Args:
            logger: Logger to use
            destination: Destination of the message
            message: Message content
        """
        if isinstance(logger, logging.Logger):
            logger.debug(f">> TO {destination}: {message}")
        else:
            # If a logging module was passed instead of a logger
            logging.getLogger("LogHelper").debug(f">> TO {destination}: {message}")
    
    @staticmethod
    def log_system(logger, message):
        """
        Log a system message
        
        Args:
            logger: Logger to use
            message: Message content
        """
        if isinstance(logger, logging.Logger):
            logger.info(f"SYSTEM: {message}")
        else:
            # If a logging module was passed instead of a logger
            logging.getLogger("LogHelper").info(f"SYSTEM: {message}")
    
    @staticmethod
    def dump_message_info(logger, message):
        """
        Dump detailed information about a message for debugging
        
        Args:
            logger: Logger to use
            message: Message to analyze
        """
        logger.debug(f"Message dump: {message}")
        
        try:
            parts = message.split('|')
            logger.debug(f"Message parts: {parts}")
            logger.debug(f"Command part: {parts[0]}")
            logger.debug(f"Arguments: {parts[1:] if len(parts) > 1 else 'None'}")
        except Exception as e:
            logger.error(f"Error parsing message: {e}")
