
import sys
import uuid
import asyncio
import multiprocessing

from common.social import Messages
from puzzle.logic import KryptoLogic
from puzzle.server_classic import ServerClassic 
from puzzle.server_competitive import ServerCompetitive

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

class MainServer:
    def __init__(self, host='localhost', port=5000, max_servers=5):
        self.host = host
        self.port = port
        self.max_servers = max_servers

        # Puzzles y servidores
        self.puzzle_queue = asyncio.Queue()
        self.process_pipes = {}  # Diccionario {pid: pipe del proceso}
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

    async def run_server(self, server):
        """Ejecuta el servidor principal."""
        try:
            async with server:
                print("Servidor principal ejecutándose...")
                await server.serve_forever()
                print("Servidor principal cerrado.")
        except Exception as e:
            print(f"Error al ejecutar server.serve_forever(): {e}")


    async def initialize_puzzles(self):
        """Inicializar la cola con puzzles iniciales."""
        for i in range(self.max_servers):
            await self.puzzle_queue.put(KryptoLogic.generar_puzzle())
    
    async def listen_to_servers(self, test=False):
        """Escucha los servidores clásicos y actualiza la cola de puzzles."""
        print("Iniciando listen_to_servers...")
        while True:
            for pid, pipe in list(self.process_pipes.items()):
                if pipe.poll():
                    mensaje = pipe.recv()
                    if mensaje == Messages.OK:
                        puzzle = KryptoLogic.generar_puzzle()
                        self.puzzle_queue.put(puzzle)
                        print(f"Nuevo puzzle recibido: {puzzle}")
                    elif mensaje == Messages.KILL:
                        # Matar al proceso que mando este mensaje
                        pipe.close()
                        self.processes[pid].terminate()
                        del self.process_pipes[pid]
                        del self.processes[pid]
                        print(f"Servidor con ID {pid} terminado.")
                    elif mensaje == Messages.ERROR:
                        print(f"Error en el servidor con ID {pid}.")
                    else:
                        print(f"Error en el mensaje del proceso {self.processes[pid]}")
            if test:
                break

    async def handle_new_player(self, reader, writer):
        """Maneja la conexión con un nuevo jugador."""
        print("Nueva conexión recibida")
        try:
            data = await reader.read(1024)
            username = data.decode().strip()
            player_id = str(uuid.uuid4())
            print(f"Jugador conectado: {username} (ID: {player_id})")
            writer.write(Messages.LOGIN_SUCCESS.encode())
            await writer.drain()
        except Exception as e:
            print(f"Error en la conexión con el jugador: {e}")
            writer.write(Messages.LOGIN_ERROR.encode())
            await writer.drain()
        
        await self.handle_main_menu(reader, writer)

    async def handle_main_menu(self, reader, writer, test=False):
        """Maneja el menú principal del jugador."""
        print("Manejando el menú principal del jugador...")
        while True:
            data = await reader.read(1024)
            option, *args = data.decode().strip().split("|")
            if option == "1":  # Ver lista de servidores
                await self.send_server_list(writer)
            elif option == "2":  # Elegir un servidor
                await self.handle_server_choice(*args, writer)
            elif option == "3":  # Crear un servidor
                await self.create_new_server(*args, writer)
            elif option == "exit":  # Salir
                writer.write(b"Goodbye!")
                await writer.drain()
                break
            else:
                writer.write(b"Invalid option. Please try again.\n")
                await writer.drain()
            if test:
                break

    async def send_server_list(self, writer):
        """Envía la lista de servidores disponibles al jugador."""
        print("Enviando lista de servidores...")
        if not self.servers:
            writer.write(Messages.NO_SERVERS.encode())
            await writer.drain()
            return

        server_list = "\nAvailable servers:\n"
        for server_id, details in self.servers.items():
            server_list += (
                f"ID: {server_id}, Name: {details['name']}, Mode: {details['mode']}\n"
            )

        writer.write(server_list.encode())
        await writer.drain()

    async def handle_server_choice(self, server_id, writer):
        """Permite al jugador unirse a un servidor existente."""
        print(f"Manejando elección de servidor: {server_id}")
        if server_id in self.servers:
            port = self.servers[server_id]["port"]
            writer.write(f"Success|'{self.servers[server_id]['name']}'|{port}.\n".encode())
        else:
            writer.write(b"Invalid server ID. Please try again.\n")
        await writer.drain()

    async def create_new_server(self, name, mode, writer):
        """Crea un nuevo servidor y lo registra."""
        print(f"Creando nuevo servidor: {name}, modo: {mode}")
        try:
            # Crear el servidor clásico
            server_id = str(uuid.uuid4())[:4]
            if mode == "classic":
                port = await self.create_classic_server(name)
            else:
                port = await self.create_competitive_server(name)
            self.servers[server_id] = {"port": port, "name": name, "mode": mode}

            writer.write(
                f"Server created successfully with ID: {server_id}. Share this ID with others.\n".encode()
            )
            await writer.drain()
            
        except Exception as e:
            writer.write(b"Error creating server. Please try again.\n")
            await writer.drain()
            print(f"Error creando servidor: {e}")

    async def create_classic_server(self, name):
        """Crea un nuevo proceso ServerClassic y lo registra."""
        port = self.next_port
        self.next_port += 1

        # Crear un pipe para comunicarse con el proceso ServerClassic
        parent_pipe, child_pipe = multiprocessing.Pipe()
        process = multiprocessing.Process(
            target=self.start_classic_server,
            args=(port, self.puzzle_queue, child_pipe)
        )
        process.start()

        self.process_pipes[process.pid] = parent_pipe
        self.processes[process.pid] = process
        print(f"Nuevo servidor '{name}' creado en el puerto {port}.")
        return port

    async def start_classic_server(self, port, puzzle_queue, pipe):
        """Lanza un proceso del servidor clásico."""
        server = ServerClassic(pipe_puzzle=puzzle_queue, pipe_message=pipe)
        server.start(port)

    async def create_competitive_server(self, name):
        """Crea un nuevo proceso ServerCompetitive y lo registra."""
        port = self.next_port
        self.next_port += 1

        # Crear un pipe para comunicarse con el proceso ServerCompetitive
        parent_pipe, child_pipe = multiprocessing.Pipe()
        process = multiprocessing.Process(
            target=self.start_competitive_server,
            args=(port, self.puzzle_queue, child_pipe)
        )
        process.start()

        self.process_pipes[process.pid] = parent_pipe
        print(f"Nuevo servidor '{name}' creado en el puerto {port}.")
        return port

    async def start_competitive_server(self, port, puzzle_queue, pipe):
        """Lanza un proceso del servidor competitivo."""
        server = ServerCompetitive(pipe_puzzle=puzzle_queue, pipe_message=pipe)
        server.start(port)

if __name__ == "__main__":
    main_server = MainServer()
    asyncio.run(main_server.start_main_server())
