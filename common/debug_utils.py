import logging

def dump_message_info(logger, message):
    """Dumps detailed information about a message for debugging purposes"""
    logger.debug(f"Message dump: {message}")
    
    try:
        parts = message.split('|')
        logger.debug(f"Message parts: {parts}")
        logger.debug(f"Command part: {parts[0]}")
        logger.debug(f"Arguments: {parts[1:] if len(parts) > 1 else 'None'}")
    except Exception as e:
        logger.error(f"Error parsing message: {e}")
