import logging

# Column width for aligned logging
SENDER_WIDTH = 25
MESSAGE_WIDTH = 50

"""Helper functions for consistent logging across the application."""

def log_incoming(logger, addr, message):
    """Log incoming message with consistent format"""
    trimmed_message = message[:150] + "..." if len(message) > 150 else message
    logger.debug(f"<< FROM {addr}: {trimmed_message}")

def log_outgoing(logger, addr, message):
    """Log outgoing message with consistent format"""
    trimmed_message = message[:150] + "..." if len(message) > 150 else message
    logger.debug(f">> TO {addr}: {trimmed_message}")

def log_system(logger, component, message):
    """Log system event with consistent formatting"""
    component_str = f"⚙ {component}"
    logger.info(f"{component_str:<{SENDER_WIDTH}} | {message}")
