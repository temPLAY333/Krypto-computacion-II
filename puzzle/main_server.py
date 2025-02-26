import uuid
import socket
import asyncio
import multiprocessing
import logging

from common.social import LogMessages as Logs
from common.social import UserMainMessages as UM
from common.social import InterfaceMessages as IM
from common.social import MainServerMessages as SM
from common.communication import Communication

from puzzle.logic import KryptoLogic
from puzzle.server_factory import ServerFactory

# Configurar logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MainServer:
    def __init__(self, host='localhost', port=5000, max_servers=5):
        self.host = host
        self.port = port
        self.max_servers = max_servers

        # Puzzles y servidores
        self.puzzle_queue = asyncio.Queue()
        self.message_queue = multiprocessing.Queue()
        self.server_factory = ServerFactory(self.puzzle_queue, self.message_queue)
        self.server_communication = Communication(logging.getLogger("server_communication"))
        self.users_communication = Communication(logging.getLogger("users_communication"))

        self.processes = {}  # Diccionario {pid: process}
        self.servers = {}  # Diccionario {server_id: {"port": port, "name": name, "mode": mode}}

        # Siguiente puerto disponible
        self.next_port = port
        logging.info(f"MainServer initialized with host={host}, port={port}, max_servers={max_servers}")

    async def start_main_server(self):
        """Inicia el servidor principal para manejar jugadores y servidores clásicos."""
        await self.initialize_puzzles()
        logging.info("Puzzles iniciales creados.")

        try:
            # Try to use a single server that can handle both IPv4 and IPv6
            server = await asyncio.start_server(
                self.handle_new_player, 
                self.host, 
                self.port,
                reuse_address=True
            )
            
            logging.info(f"Servidor principal definido en {self.host}:{self.port}")
            addr = server.sockets[0].getsockname()
            logging.info(f"Escuchando en: {addr}")
        except Exception as e:
            logging.error(f"Error al iniciar el servidor: {e}")
            return

        await asyncio.gather(
            self.run_server(server, "Main"),
            self.listen_to_servers()
        )

    async def initialize_puzzles(self):
        """Inicializar la cola con puzzles iniciales."""
        for i in range(self.max_servers):
            await self.puzzle_queue.put(KryptoLogic.generar_puzzle())
        logging.info("Puzzles inicializados")

    """------------------------------------------- Manejo de Usuarios ------------------------------------------- """

    async def run_server(self, server, protocol):
        """Ejecuta el servidor principal."""
        # Registrar comandos de usuario
        self.users_communication.register_command(UM.TEST, self.test_message)
        self.users_communication.register_command(UM.LOGIN, self.handle_login)
        self.users_communication.register_command(UM.LIST_SERVERS, self.send_server_list)
        self.users_communication.register_command(UM.CHOOSE_SERVER, self.handle_server_choice)
        self.users_communication.register_command(UM.CREATE_SERVER, self.create_new_server)
        
        try:
            async with server:
                logging.info(f"Servidor principal ejecutándose en {protocol}, {self.host}:{self.port}...")
                await server.serve_forever()
                logging.info(f"Servidor principal cerrado en {protocol}.")
        except Exception as e:
            logging.error(f"Error al ejecutar server.serve_forever() en {protocol}: {e}")

    async def handle_new_player(self, reader, writer):
        """Maneja la conexión con un nuevo jugador."""
        addr = writer.get_extra_info('peername')
        logging.info(f"Nueva conexión recibida desde {addr}")

        while True:
            try:
                data = await reader.read(100)
                if not data:
                    logging.info(f"Conexión cerrada por {addr}")
                    break
                message = data.decode()
                logging.info(f"Mensaje recibido de {addr}: {message}")
                await self.users_communication.handle_async_message(message, writer)
            except Exception as e:
                logging.error(f"Error manejando la conexión con {addr}: {e}")
                break
    
    async def test_message(self, writer):
        """Envía un mensaje de prueba al cliente."""
        logging.info("Enviando mensaje de prueba al cliente")
        await self.users_communication.send_message_async(writer, UM.TEST)

    async def handle_login(self, writer, username):
        """Maneja el login del jugador."""
        player_id = str(uuid.uuid4())
        logging.info(f"Jugador conectado: {username} (ID: {player_id})")
        await self.users_communication.send_message_async(writer, IM.LOGIN_SUCCESS)

    async def send_server_list(self, writer):
        """Envía la lista de servidores disponibles al jugador."""
        logging.info("Enviando lista de servidores...")
        if not self.servers:
            await self.users_communication.send_message_async(writer, IM.NO_SERVERS)
            return

        server_list = "\nAvailable servers:\n"
        for server_id, details in self.servers.items():
            server_list += (
                f"ID: {server_id}, Name: {details['name']}, Mode: {details['mode']}\n"
            )

        await self.users_communication.send_message_async(writer, server_list)

    async def handle_server_choice(self, writer, server_id):
        """Permite al jugador unirse a un servidor existente."""
        logging.info(f"Manejando elección de servidor: {server_id}")
        if server_id in self.servers:
            port = self.servers[server_id]["port"]
            await self.users_communication.send_message_async(writer, UM.OK + f"|'{self.servers[server_id]['name']}'|{port}.\n")
        else:
            await self.users_communication.send_message_async(writer, IM.SERVER_JOIN_FAIL)

    async def create_new_server(self, writer, name, mode):
        """Crea un nuevo servidor y lo registra."""
        logging.info(f"Creando nuevo servidor: {name}, modo: {mode}")
        try:
            server_id = str(uuid.uuid4())[:4]
            pid = self.server_factory.create_server(name, mode)
            self.servers[server_id] = {"pid": pid, "name": name, "mode": mode}
            await self.users_communication.send_message_async(writer, f"Server created successfully with ID: {server_id}. Share this ID with others.\n")
        except Exception as e:
            await self.users_communication.send_message_async(writer, "Error creating server. Please try again.\n")
            logging.error(f"Error creando servidor: {e}")

    """------------------------------------------- Manejo de Servidores de Juego ------------------------------------------- """
    
    async def listen_to_servers(self):
        """Escucha los servidores clásicos y actualiza la cola de puzzles."""
        logging.info("Iniciando listen_to_servers...")
        self.server_communication.register_command(SM.OK, self.handle_puzzle)
        self.server_communication.register_command(SM.KILL, self.terminate_process)
        self.server_communication.register_command(SM.ERROR, self.handle_error)
        
        while True:
            try:
                if not self.message_queue.empty():
                    message = self.message_queue.get()
                    # Pass the message to handle_async_message
                    await self.server_communication.handle_async_message(message)
                else:
                    # Add a small sleep to prevent CPU thrashing
                    await asyncio.sleep(0.1)
            except Exception as e:
                logging.error(f"Error en listen_to_servers: {e}")
    
    async def handle_puzzle(self, pid):
        """Maneja un nuevo puzzle recibido de un servidor."""
        logging.info(f"Pedido de nuevo puzzle recibido de servidor con ID {pid}")
        puzzle = KryptoLogic.generar_puzzle()
        await self.puzzle_queue.put(puzzle)

    async def terminate_process(self, pid):
        """Termina un proceso de servidor."""
        if pid in self.processes:
            self.processes[pid].terminate()
            del self.processes[pid]
            logging.info(f"Servidor con ID {pid} terminado.")
    
    async def handle_error(self, pid, error):
        """Maneja un error en un servidor."""
        logging.error(f"Error en el servidor con ID {pid}: {error}")

if __name__ == "__main__":
    main_server = MainServer()
    asyncio.run(main_server.start_main_server())