import asyncio

class Communication:
    def __init__(self, log_enabled=True):
        self.commands = {}
        self.log_enabled = log_enabled

    def register_command(self, command, handler):
        """Registra un comando y su manejador."""
        self.commands[command] = handler
    
    def unregister_command(self, command):
        """Desregistra un comando."""
        if command in self.commands:
            del self.commands[command]

    def log(self, message):
        """Imprime un mensaje de log si los logs están habilitados."""
        if self.log_enabled:
            print(message)

    def handle_sync_command(self, data):
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
            self.log(f"Error receiving message: {e}")

    async def handle_async_message(self, data, reader, writer):
        """Recibe un mensaje de manera asincrónica y ejecuta el comando correspondiente."""
        try:
            if not data:
                return
            command, *args = data.split("|")
            if command in self.commands:
                await self.commands[command](reader, writer, *args)
            else:
                self.log(f"Unknown command: {command}")
        except Exception as e:
            self.log(f"Error receiving message: {e}")

    def send_message_sync(self, writer, message):
        """Envía un mensaje de manera sincrónica a un destinatario específico."""
        try:
            writer.send(message.encode())
        except Exception as e:
            self.log(f"Error sending message: {e}")

    async def send_message_async(self, writer, message):
        """Envía un mensaje de manera asincrónica a un destinatario específico."""
        try:
            writer.write(message.encode())
            await writer.drain()
        except Exception as e:
            self.log(f"Error sending message: {e}")

    def send_all_message_sync(self, writers, message):
        """Envía un mensaje de manera sincrónica a todos los destinatarios."""
        for writer in writers:
            self.send_message_sync(writer, message)

    async def send_all_message_async(self, writers, message):
        """Envía un mensaje de manera asincrónica a todos los destinatarios."""
        for writer in writers:
            await self.send_message_async(writer, message)