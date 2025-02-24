import asyncio
import re

from common.social import Messages
from client.player import Player

class User:
    def __init__(self, server_host='localhost', server_port=5000):
        self.server_host = server_host
        self.server_port = server_port
        self.username = None
        self.reader = None
        self.writer = None

    async def connect_to_server(self):
        """Establece la conexión con el servidor principal."""
        try:
            self.reader, self.writer = await asyncio.open_connection(self.server_host, self.server_port)
            print(Messages.GREETING)
        except Exception as e:
            print(f"Connection error: {e}")
            return False
        return True

    async def login(self):
        """Realiza el proceso de login del jugador."""
        try:
            username = input(Messages.ASK_USERNAME)
            if not re.match("^[a-zA-Z0-9]{8,20}$", username):
                print(Messages.INVALID_USERNAME)
                return False
            self.writer.write(username.encode())
            await self.writer.drain()
            response = await self.reader.read(1024)

            if response.decode() == Messages.LOGIN_SUCCESS:
                self.username = username
                print(Messages.LOGIN_SUCCESS)
                return True
            else:
                print(Messages.LOGIN_ERROR)
                return False
        except Exception as e:
            print(f"Error during login: {e}")
            return False

    async def main_menu(self):
        """Muestra el menú principal y maneja las opciones del jugador."""
        while True:
            print(Messages.MAIN_MENU)
            option = input().strip()

            if option == "1":
                await self.view_server_list()
            elif option == "2":
                await self.join_server()
            elif option == "3":
                await self.create_server()
            elif option == "exit":
                await self.exit_game()
                break
            else:
                print(Messages.INVALID_OPTION)

    async def view_server_list(self):
        """Solicita y muestra la lista de servidores al jugador."""
        self.writer.write(b"1")
        await self.writer.drain()
        response = await self.reader.read(4096)
        print(response.decode())

    async def join_server(self):
        """Permite al jugador unirse a un servidor existente."""
        server_id = input(Messages.ASK_SERVER_ID)
        self.writer.write(f"2|{server_id}".encode())
        await self.writer.drain()
        response = await self.reader.read(1024)

        if response.decode().startswith("Success"):
            _, name, classic_port = response.decode().split("|")
            try:
                classic_reader, classic_writer = await asyncio.open_connection('localhost', int(classic_port))

                message = await classic_reader.read(1024)
                if message.decode() == Messages.SERVER_FULL:
                    raise Exception()

                print(Messages.SERVER_JOIN_SUCCESS)
                print(f"Joining Server {name} ...")

                player = Player(self.username, classic_reader, classic_writer)
                print(message.decode())
                await player.play()

            except Exception as e:
                print(f"Connection error: {e}")
        else:
            print(Messages.SERVER_JOIN_FAIL)

    async def create_server(self):
        """Permite al jugador crear un servidor nuevo."""
        name = input(Messages.CREATE_SERVER_NAME)
        mode = input(Messages.CREATE_SERVER_MODE).lower()

        if mode not in ["classic", "competitive"]:
            print(Messages.CREATE_SERVER_ERROR)
            return

        self.writer.write(f"3|{name}|{mode}".encode())
        await self.writer.drain()
        response = await self.reader.read(1024)
        print(response.decode())

    async def exit_game(self):
        """Cierra la conexión con el servidor."""
        self.writer.close()
        await self.writer.wait_closed()

# Ejecución del cliente
if __name__ == "__main__":
    player = User()
    asyncio.run(player.connect_to_server())
    asyncio.run(player.login())
    if player.username:
        asyncio.run(player.main_menu()) 
