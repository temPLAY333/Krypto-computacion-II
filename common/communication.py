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

    def handle_sync_command(self, data: str):
        """Recibe un mensaje de manera sincrónica y ejecuta el comando correspondiente."""
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

    def send_message(self, writer : socket.socket, message):
        """Envía un mensaje de manera sincrónica a un destinatario específico."""
        try:
            writer.sendall(message.encode())
        except Exception as e:
            self.log(f"Error sending message: {e}")

    async def send_message_async(self, writer, message):
        if writer:
            writer.write(message.encode())
            await writer.drain()
        else:
            self.logger.warning(f"Cannot send message - writer is None: {message}")

    def send_all_message(self, writers: list[socket.socket], message):
        """Envía un mensaje de manera sincrónica a todos los destinatarios."""
        for writer in writers:
            self.send_message(writer, message)

    async def send_all_message_async(self, writers, message):
        """Envía un mensaje de manera asincrónica a todos los destinatarios."""
        for writer in writers:
            await self.send_message_async(writer, message)
            
    def receive_message(self, socket):
        """Receives and parses a message, returning success status, command, and arguments"""
        try:
            data = socket.recv(1024).decode()
            if not data:
                return False, None
            
            return True, data
        except Exception as e:
            self.log(f"Error receiving message: {e}")
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