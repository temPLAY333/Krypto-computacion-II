
import uuid
import asyncio
import threading
import multiprocessing

from common.social import Messages
from puzzle.logic import KryptoLogic
from puzzle.server_classic import ServerClassic 
from puzzle.server_competitive import ServerCompetitive

class MainServer:
    def __init__(self, host='localhost', port=5000, max_servers=5):
        self.host = host
        self.port = port
        self.max_servers = max_servers

        # Puzzles y servidores
        self.puzzle_queue = multiprocessing.Queue()
        self.process_pipes = {}  # Diccionario {pid: pipe del proceso}
        self.processes = {}  # Diccionario {pid: process}
        self.servers = {}  # Diccionario {server_id: {"port": port, "name": name, "mode": mode}}

        # Siguiente puerto disponible
        self.next_port = port

    def initialize_puzzles(self):
        """Inicializar la cola con puzzles iniciales."""
        for i in range(self.max_servers):
            self.puzzle_queue.put(KryptoLogic.generar_puzzle())
        print("Puzzles iniciales creados.")
    
    async def start_main_server(self):
        """Inicia el servidor principal para manejar jugadores y servidores clásicos."""
        threading.Thread(target=self.listen_to_servers, daemon=True).start()

        server = await asyncio.start_server(self.handle_new_player, self.host, self.port)
        print(f"Servidor principal escuchando en {self.host}:{self.port}...")
        async with server:
            await server.serve_forever()
    
    def listen_to_servers(self, test= False):
        """Escucha los servidores clásicos y actualiza la cola de puzzles."""

        while True:
            for pid, pipe in list(self.process_pipes.items()):
                if pipe.poll():
                    mensaje = pipe.recv()
                    if mensaje == "ok":
                        puzzle = KryptoLogic.generar_puzzle()
                        self.puzzle_queue.put(puzzle)
                        print(f"Nuevo puzzle recibido: {puzzle}")
                    elif mensaje == "vacio":
                        # Matar al proceso que mando este mensaje
                        pipe.close()
                        self.processes[pid].terminate()
                        del self.process_pipes[pid]
                        del self.processes[pid]
                        print(f"Servidor con ID {pid} terminado.")
                    elif mensaje == "error":
                        print(f"Error en el servidor con ID {pid}.")
                    else:
                        print(f"Error en el mensaje del proceso {self.processes[pid]}")
            if test:
                break

    async def handle_new_player(self, reader, writer, test=False):
        """Maneja la conexión con un nuevo jugador."""
        try:
            data = await reader.read(1024)
            username = data.decode().strip()
            player_id = str(uuid.uuid4())
            print(f"Jugador conectado: {username} (ID: {player_id})")
            writer.write(Messages.LOGIN_SUCCESS.encode())
            await writer.drain()
        except Exception as e: #Testear esto
            writer.write(Messages.LOGIN_ERROR)
            print(e)

        while True:
            data = await reader.read(1024)
            option, *args = data.decode().strip().split("|")
            if option == "1":  # Ver lista de servidores
                await self.send_server_list(writer)
            elif option == "2":  # Elegir un servidor
                await self.handle_server_choice( *args, writer)
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

        if server_id in self.servers:
            port = self.servers[server_id]["port"]
            writer.write(f"Success|'{self.servers[server_id]['name']}'|{port}.\n".encode())
        else:
            writer.write(b"Invalid server ID. Please try again.\n")
        await writer.drain()

    async def create_new_server(self, name, mode, writer):
        """Crea un nuevo servidor y lo registra."""
        try:
            # Crear el servidor clásico
            server_id = str(uuid.uuid4())[:4]
            if mode == "classic":
                port = self.create_classic_server(name)
            else:
                port = self.create_competitive_server(name)
            self.servers[server_id] = {"port": port, "name": name, "mode": mode}

            writer.write(
                f"Server created successfully with ID: {server_id}. Share this ID with others.\n".encode()
            )
            await writer.drain()
            
        except Exception as e:
            writer.write(b"Error creating server. Please try again.\n")
            await writer.drain()
            print(f"Error creando servidor: {e}")


    def create_classic_server(self, name):
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

    def start_classic_server(self, port, puzzle_queue, pipe):
        """Lanza un proceso del servidor clásico."""
        server = ServerClassic(pipe_puzzle=puzzle_queue, pipe_message=pipe)
        server.start(port)

    def create_competitive_server(self, name):
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

    def start_classic_server(self, port, puzzle_queue, pipe):
        """Lanza un proceso del servidor competitivo."""
        server = ServerCompetitive(pipe_puzzle=puzzle_queue, pipe_message=pipe)
        server.start(port)


if __name__ == "__main__":
    main_server = MainServer()
    main_server.initialize_puzzles()
    asyncio.run(main_server.start_main_server())
