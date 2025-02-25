import uuid
import asyncio
import multiprocessing

from common.social import LogMessages as Logs
from common.social import UserMainMessages as UM
from common.social import InterfaceMessages as IM
from common.social import MainServerMessages as SM
from puzzle.logic import KryptoLogic
from puzzle.server_factory import ServerFactory
from common.communication import Communication

class MainServer:
    def __init__(self, host='localhost', port=5000, max_servers=5):
        self.host = host
        self.port = port
        self.max_servers = max_servers

        # Puzzles y servidores
        self.puzzle_queue = asyncio.Queue()
        self.message_queue = multiprocessing.Queue()
        self.server_factory = ServerFactory(self.puzzle_queue, self.message_queue)
        self.server_communication = Communication(log_enabled=True)
        self.users_communication = Communication(log_enabled=True)

        self.processes = {}  # Diccionario {pid: process}
        self.servers = {}  # Diccionario {server_id: {"port": port, "name": name, "mode": mode}}

        # Siguiente puerto disponible
        self.next_port = port

    async def start_main_server(self):
        """Inicia el servidor principal para manejar jugadores y servidores clásicos."""
        await self.initialize_puzzles()
        print("Puzzles iniciales creados.")

        try:
            server = await asyncio.start_server(self.handle_new_player, self.host, self.port)
            print("Servidor principal definido.")
        except Exception as e:
            print(f"Error al iniciar el servidor: {e}")
            return

        await asyncio.gather(
            self.run_server(server),
            self.listen_to_servers()
        )

    async def initialize_puzzles(self):
        """Inicializar la cola con puzzles iniciales."""
        for i in range(self.max_servers):
            await self.puzzle_queue.put(KryptoLogic.generar_puzzle())

    """------------------------------------------- Manejo de Usuarios ------------------------------------------- """

    async def run_server(self, server):
        """Ejecuta el servidor principal."""
        self.users_communication.register_command(UM.LOGIN, self.handle_login)
        self.users_communication.register_command(UM.SERVER_LIST, self.send_server_list)
        self.users_communication.register_command(UM.SERVER_CHOICE, self.handle_server_choice)
        self.users_communication.register_command(UM.CREATE_SERVER, self.create_new_server)

        try:
            async with server:
                print("Servidor principal ejecutándose...")
                await server.serve_forever()
                print("Servidor principal cerrado.")
        except Exception as e:
            print(f"Error al ejecutar server.serve_forever(): {e}")

    async def handle_new_player(self, reader, writer):
        """Maneja la conexión con un nuevo jugador."""
        print("Nueva conexión recibida")

        while True:
            data = await reader.read(100).decode()
            await self.users_communication.handle_async_message(data, writer)

    async def handle_login(self, reader, writer, username):
        """Maneja el login del jugador."""
        player_id = str(uuid.uuid4())
        print(f"Jugador conectado: {username} (ID: {player_id})")
        await self.users_communication.send_message_async(writer, IM.LOGIN_SUCCESS)

    async def send_server_list(self, reader, writer):
        """Envía la lista de servidores disponibles al jugador."""
        print("Enviando lista de servidores...")
        if not self.servers:
            await self.users_communication.send_message_async(writer, IM.NO_SERVERS)
            return

        server_list = "\nAvailable servers:\n"
        for server_id, details in self.servers.items():
            server_list += (
                f"ID: {server_id}, Name: {details['name']}, Mode: {details['mode']}\n"
            )

        await self.users_communication.send_message_async(writer, server_list)

    async def handle_server_choice(self, reader, writer, server_id):
        """Permite al jugador unirse a un servidor existente."""
        print(f"Manejando elección de servidor: {server_id}")
        if server_id in self.servers:
            port = self.servers[server_id]["port"]
            await self.users_communication.send_message_async(writer, f"Success|'{self.servers[server_id]['name']}'|{port}.\n")
        else:
            await self.users_communication.send_message_async(writer, "Invalid server ID. Please try again.\n")

    async def create_new_server(self, reader, writer, name, mode):
        """Crea un nuevo servidor y lo registra."""
        print(f"Creando nuevo servidor: {name}, modo: {mode}")
        try:
            server_id = str(uuid.uuid4())[:4]
            pid = self.server_factory.create_server(name, mode)
            self.servers[server_id] = {"pid": pid, "name": name, "mode": mode}
            await self.users_communication.send_message_async(writer, f"Server created successfully with ID: {server_id}. Share this ID with others.\n")
        except Exception as e:
            await self.users_communication.send_message_async(writer, "Error creating server. Please try again.\n")
            print(f"Error creando servidor: {e}")

    """------------------------------------------- Manejo de Servidores de Juego ------------------------------------------- """
    
    async def listen_to_servers(self):
        """Escucha los servidores clásicos y actualiza la cola de puzzles."""
        print("Iniciando listen_to_servers...")
        self.server_communication.register_command(SM.OK, self.handle_puzzle)
        self.server_communication.register_command(SM.KILL, self.terminate_process)
        self.server_communication.register_command(SM.ERROR, self.handle_error)
        
        while True:
            if not self.message_queue.empty():
                message = self.message_queue.get()
                await self.server_communication.handle_async_message()
    
    async def handle_puzzle(self, pid):
        """Maneja un nuevo puzzle recibido de un servidor."""
        print(f"Pedido de nuevo puzzle recibido de servidor con ID {pid}")
        puzzle = KryptoLogic.generar_puzzle()
        await self.puzzle_queue.put(puzzle)

    async def terminate_process(self, pid):
        """Termina un proceso de servidor."""
        if pid in self.processes:
            self.processes[pid].terminate()
            del self.processes[pid]
            print(f"Servidor con ID {pid} terminado.")
    
    async def handle_error(self, pid, error):
        """Maneja un error en un servidor."""
        print(f"Error en el servidor con ID {pid}: {error}")

if __name__ == "__main__":
    main_server = MainServer()
    asyncio.run(main_server.start_main_server())