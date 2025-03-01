import asyncio
import socket

class Communication:
    def __init__(self, log=None):
        self.commands = {}
        self.log_object = log  # Store the log object

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
        if self.log_object:
            self.log_object.info(message)  # Assuming the log object has an info method
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

    async def handle_async_command(self, data : str, writer):
        """Recibe un mensaje de manera asincrónica y ejecuta el comando correspondiente."""
        try:
            if not data:
                return
            command, *args = data.split("|")
            if command in self.commands:
                await self.commands[command](writer, *args)
            else:
                self.log(f"Unknown command: {command}")
        except Exception as e:
            self.log(f"Error processing message: {e}")

    def send_message(self, writer : socket.socket, message):
        """Envía un mensaje de manera sincrónica a un destinatario específico."""
        try:
            writer.sendall(message.encode())
        except Exception as e:
            self.log(f"Error sending message: {e}")

    async def send_message_async(self, writer, message):
        """Envía un mensaje de manera asincrónica a un destinatario específico."""
        try:
            writer.write(message.encode())
            await writer.drain()
        except Exception as e:
            self.log(f"Error sending message: {e}")

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