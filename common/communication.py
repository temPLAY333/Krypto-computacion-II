import logging
import asyncio
import socket

# Use the centralized logger instead of debug_utils
from common.logger import Logger

class Communication:
    def __init__(self, logger=None):
        self.commands = {}
        self.logger = logger or logging.getLogger(__name__)

    def register_command(self, command, handler):
        """Registra un comando y su manejador."""
        self.commands[command] = handler
    
    def unregister_command(self, command):
        """Desregistra un comando."""
        if command in self.commands:
            del self.commands[command]
    
    def define_all_commands(self, commands: dict):
        """Define all commands at once."""
        self.commands = commands

    def log(self, message):
        """Uses the log object if provided, otherwise falls back to print if logs are enabled."""
        if self.logger:
            self.logger.info(message)  # Assuming the log object has an info method
        else:
            print(message)

    def handle_sync_command(self, message):
        """Process a command message with better error handling"""
        try:
            # Skip empty messages
            if not message or not message.strip():
                return False
                
            # Log raw message for debugging
            self.logger.debug(f"Processing message: '{message}'")
            
            # Split into command and arguments
            parts = message.split('|')
            command = parts[0]
            args = parts[1:] if len(parts) > 1 else []
            
            # Handle the command
            if command in self.commands:
                self.logger.debug(f"Handling command: {command} with args: {args}")
                self.commands[command](*args)
                return True
            else:
                self.logger.warning(f"Unknown command: {command}")
                return False
        except Exception as e:
            self.logger.error(f"Error processing command: {e}")
            return False

    async def handle_async_command(self, message, writer):
        try:
            self.logger.debug(f"Handling command: {message}")
            # Use the centralized logger's method for message dumping
            Logger.dump_message_info(self.logger, message)
            
            # Parse command and arguments
            parts = message.split('|')
            if not parts:
                self.logger.error("Empty command received")
                return False
                
            command = parts[0].strip()
            args = parts[1:] if len(parts) > 1 else []
            
            # Find handler
            handler = self.commands.get(command)
            if handler:
                self.logger.debug(f"Found handler for command: {command} -> {handler.__name__}")
                try:
                    await handler(writer, *args)
                    self.logger.debug(f"Handler {handler.__name__} executed successfully")
                    return True
                except Exception as e:
                    self.logger.error(f"Error executing handler {handler.__name__}: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())
                    return False
            else:
                self.logger.warning(f"No handler found for command: {command}")
                self.logger.debug(f"Available commands: {list(self.commands.keys())}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error handling command: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def has_complete_message(self):
        """Check if buffer has a complete message without reading from socket"""
        return hasattr(self, 'buffer') and '\n' in self.buffer
    
    def get_next_message(self):
        """Get next complete message from buffer without reading from socket"""
        if not self.has_complete_message():
            return False, None
            
        message, self.buffer = self.buffer.split('\n', 1)
        return True, message

    def send_message(self, socket, message):
        """Send a message with proper termination"""
        try:
            # Ensure message ends with a newline to mark message boundary
            if not message.endswith('\n'):
                message += '\n'
            socket.sendall(message.encode('utf-8'))
            return True
        except Exception as e:
            self.logger.error(f"Send error: {e}")
            return False

    async def send_message_async(self, writer, message):
        """Send a message asynchronously with proper termination"""
        try:
            if writer:
                # Ensure message ends with a newline to mark message boundary
                if not message.endswith('\n'):
                    message += '\n'
                writer.write(message.encode('utf-8'))
                await writer.drain()
                return True
            else:
                self.logger.warning(f"Cannot send message - writer is None: {message}")
                return False
        except Exception as e:
            self.logger.error(f"Send error: {e}")
            return False

    def send_all_message(self, writers: list[socket.socket], message):
        """Envía un mensaje de manera sincrónica a todos los destinatarios."""
        for writer in writers:
            self.send_message(writer, message)

    async def send_all_message_async(self, writers, message):
        """Envía un mensaje de manera asincrónica a todos los destinatarios."""
        for writer in writers:
            await self.send_message_async(writer, message)
            
    def receive_message(self, socket):
        """Receive a complete message (ending with newline) from the socket"""
        try:
            if not hasattr(self, 'buffer'):
                self.buffer = ""
                
            # Try to receive data if we don't already have a complete message
            if '\n' not in self.buffer:
                data = socket.recv(4096)
                if not data:
                    return False, None
                    
                # Add to buffer
                decoded_data = data.decode('utf-8')
                self.buffer += decoded_data
                self.logger.debug(f"Added {len(decoded_data)} bytes to buffer. Buffer now contains {len(self.buffer)} bytes")
            
            # Check if we have a complete message
            if '\n' in self.buffer:
                # Split at first newline
                message, self.buffer = self.buffer.split('\n', 1)
                self.logger.debug(f"Extracted complete message: '{message}', remaining buffer: {len(self.buffer)} bytes")
                return True, message
            
            # We don't have a complete message yet, wait for more data
            self.logger.debug(f"No complete message yet, buffer contains {len(self.buffer)} bytes")
            return True, None  # Only return complete messages, not partial ones
        except Exception as e:
            self.logger.error(f"Receive error: {e}")
            return False, None
    
    def execute_command(self, data):
        """Execute a registered command with provided arguments"""
        try:
            if not data:
                return
            command, *args = data.split("|")
            if command in self.commands:
                self.commands[command](*args)
            else:
                self.log(f"Unknown command: {command}")
        except Exception as e:
            self.log(f"Error processing message: {e}")
    
    def close_connection(self, socket):
        """Close a socket connection safely"""
        try:
            socket.close()
            return True
        except Exception as e:
            self.log(f"Error closing connection: {e}")
            return False