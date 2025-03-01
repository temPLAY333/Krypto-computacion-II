import threading
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
        self.puzzle_queue = multiprocessing.Queue()
        self.message_queue = multiprocessing.Queue()
        self.server_factory = ServerFactory(self.puzzle_queue, self.message_queue)
        
        # Create separate loggers for the two communication channels
        self.server_logger = logging.getLogger("server_communication")
        self.users_logger = logging.getLogger("users_communication")
        
        # Initialize communication objects
        self.users_communication = Communication(self.users_logger) 
        self.server_communication = Communication(self.server_logger)
        
        # Register command handlers for both communication channels
        self.register_user_command_handlers()
        self.register_server_command_handlers()

        # Start the message listener thread
        self.start_message_listener()

        self.processes = {}  # Diccionario {pid: process}
        self.servers = {}  # Diccionario {server_id: {"port": port, "name": name, "mode": mode}}
        self.players = {}  # Dictionary to track connected players {username: {"id": player_id}}

        logging.info(f"MainServer initialized with host={host}, port={port}, max_servers={max_servers}")

    def register_user_command_handlers(self):
        """Register all command handlers for user communication"""
        handlers = {
            UM.TEST: self.handle_test_message,
            UM.LOGIN: self.handle_login,
            UM.LIST_SERVERS: self.handle_list_servers,
            UM.CHOOSE_SERVER: self.handle_server_choice,
            UM.CREATE_SERVER: self.handle_create_server,
            UM.LOGOUT: self.handle_logout,
        }
        self.users_communication.define_all_commands(handlers)
        logging.info("User command handlers registered")

    def register_server_command_handlers(self):
        """Register all command handlers for server communication"""
        handlers = {
            SM.OK: self.handle_server_ok,
            SM.ERROR: self.handle_server_error,
            SM.KILL: self.handle_server_kill,
        }
        self.server_communication.define_all_commands(handlers)
        logging.info("Server command handlers registered")

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
            self.run_server(server, "Main")
        )

    async def initialize_puzzles(self):
        """Inicializar la cola con puzzles iniciales."""
        loop = asyncio.get_running_loop()
        for i in range(self.max_servers):
            # Use run_in_executor to call synchronous code from async context
            await loop.run_in_executor(None, 
                                    lambda: self.puzzle_queue.put(KryptoLogic.generar_puzzle()))
        logging.info("Puzzles inicializados")

    """------------------------------------------- Manejo de Usuarios ------------------------------------------- """

    async def run_server(self, server, protocol):
        """Ejecuta el servidor principal."""
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
                data = await reader.read(1024)  # Increased buffer size
                if not data:
                    logging.info(f"Conexión cerrada por {addr}")
                    break
                message = data.decode()
                logging.info(f"Mensaje recibido de {addr}: {message}")
                
                # Handle command through the Communication object
                await self.users_communication.handle_async_command(message, writer)
            except asyncio.CancelledError:
                logging.info(f"Connection handling for {addr} was cancelled")
                break
            except ConnectionResetError:
                logging.warning(f"Connection reset by {addr}")
                break
            except Exception as e:
                logging.error(f"Error manejando la conexión con {addr}: {e}")
                try:
                    # Try to send error message to client
                    await self.users_communication.send_message_async(
                        writer, f"{UM.ERROR}|Server internal error: {str(e)}"
                    )
                except:
                    pass  # If we can't send the error, we just log it
                break

        # Clean up
        try:
            writer.close()
            await writer.wait_closed()
            logging.info(f"Connection with {addr} closed properly")
        except:
            logging.warning(f"Could not properly close connection with {addr}")
    
    async def handle_test_message(self, writer):
        """Handles test message from client and responds with OK"""
        addr = writer.get_extra_info('peername')

        try:
            await self.users_communication.send_message_async(writer, UM.OK)
            logging.info(f"Sent OK response to {addr}")
        except Exception as e:
            logging.error(f"Error sending OK response to {addr}: {e}")

    async def handle_login(self, writer, username):
        """Maneja el login del jugador."""
        addr = writer.get_extra_info('peername')
        try:
            # Basic username validation
            if not username or not (3 <= len(username) <= 20):
                await self.users_communication.send_message_async(
                    writer, f"{UM.LOGIN_FAIL}|Invalid username format"
                )
                return
                
            # Check if username is already taken
            if username in self.players:
                await self.users_communication.send_message_async(
                    writer, f"{UM.LOGIN_FAIL}|Username already taken"
                )
                return
                
            # Register the player
            player_id = str(uuid.uuid4())
            self.players[username] = {"id": player_id, "writer": writer}
            logging.info(f"Jugador conectado: {username} (ID: {player_id})")
            
            # Send success response
            await self.users_communication.send_message_async(writer, f"{UM.LOGIN_SUCCESS}")
            logging.info(f"Login successful for {username} from {addr}")
        except Exception as e:
            logging.error(f"Error in login for {username} from {addr}: {e}")
            try:
                await self.users_communication.send_message_async(
                    writer, f"{UM.LOGIN_FAIL}|Server error during login"
                )
            except:
                pass  # If we can't send the error, we just log it

    async def handle_list_servers(self, writer):
        """Envía la lista de servidores disponibles al jugador."""
        addr = writer.get_extra_info('peername')
        logging.info(f"Server list requested from {addr}")
        try:
            if not self.servers:
                await self.users_communication.send_message_async(
                    writer, f"{UM.SERVER_LIST}|No servers available"
                )
                return

            server_list = []
            for server_id, details in self.servers.items():
                server_list.append(
                    f"ID: {server_id}, Name: {details['name']}, Mode: {details['mode']}"
                )
            
            server_list_str = "\n".join(server_list)
            await self.users_communication.send_message_async(
                writer, f"{UM.SERVER_LIST}|{server_list_str}"
            )
            logging.info(f"Sent server list to {addr}: {len(self.servers)} servers")
        except Exception as e:
            logging.error(f"Error sending server list to {addr}: {e}")
            try:
                await self.users_communication.send_message_async(
                    writer, f"{UM.ERROR}|Error retrieving server list"
                )
            except:
                pass  # If we can't send the error, we just log it

    async def handle_server_choice(self, writer, server_id):
        """Permite al jugador unirse a un servidor existente."""
        addr = writer.get_extra_info('peername')
        logging.info(f"Join server request for {server_id} from {addr}")
        try:
            if server_id in self.servers:
                server_details = self.servers[server_id]
                server_name = server_details["name"]
                server_port = server_details["port"]
                server_mode = server_details["mode"]
                
                await self.users_communication.send_message_async(
                    writer, f"{UM.JOIN_SUCCESS}|{server_name}|{server_port}|{server_mode}"
                )
                logging.info(f"Client {addr} joining server {server_id} ({server_name})")
            else:
                await self.users_communication.send_message_async(
                    writer, f"{UM.JOIN_FAIL}|Server not found or no longer available"
                )
                logging.warning(f"Client {addr} attempted to join nonexistent server {server_id}")
        except Exception as e:
            logging.error(f"Error processing join request for {server_id} from {addr}: {e}")
            try:
                await self.users_communication.send_message_async(
                    writer, f"{UM.JOIN_FAIL}|Server error processing join request"
                )
            except:
                pass  # If we can't send the error, we just log it

    async def handle_create_server(self, writer, server_name, server_mode, number):
        """Crea un nuevo servidor y lo registra."""
        addr = writer.get_extra_info('peername')
        logging.info(f"Create server request: {server_name}, {server_mode} from {addr}")
        try:
            # Validate server settings
            if not server_name or len(server_name) < 3:
                await self.users_communication.send_message_async(
                    writer, f"{UM.CREATE_FAIL}|Invalid server name (minimum 3 characters)"
                )
                return
                
            if server_mode not in ["classic", "competitive"]:
                await self.users_communication.send_message_async(
                    writer, f"{UM.CREATE_FAIL}|Invalid game mode (must be 'classic' or 'competitive')"
                )
                return
                
            # Check if we've reached the maximum number of servers
            if len(self.servers) >= self.max_servers:
                await self.users_communication.send_message_async(
                    writer, f"{UM.CREATE_FAIL}|Maximum number of servers reached"
                )
                return
                
            # Create a new server
            server_id = str(uuid.uuid4())[:4]  # First 4 characters of UUID for server ID
            
            try:
                # Start server process
                server_pid, server_port = self.server_factory.create_server(server_name, server_mode, number)
                
                # Register server
                self.servers[server_id] = {
                    "pid": server_pid,
                    "name": server_name, 
                    "mode": server_mode,
                    "port": server_port
                }
                
                # Notify client
                await self.users_communication.send_message_async(
                    writer, f"{UM.CREATE_SUCCESS}|{server_id}"
                )
                logging.info(f"Created server {server_id}: {server_name} ({server_mode}) on port {server_port}")
            except Exception as e:
                logging.error(f"Error creating server process: {e}")
                await self.users_communication.send_message_async(
                    writer, f"{UM.CREATE_FAIL}|Error starting server process"
                )
        except Exception as e:
            logging.error(f"Error in create_server handler from {addr}: {e}")
            try:
                await self.users_communication.send_message_async(
                    writer, f"{UM.CREATE_FAIL}|Server error processing create request"
                )
            except:
                pass  # If we can't send the error, we just log it

    async def handle_logout(self, writer):
        """Handle player logout"""
        addr = writer.get_extra_info('peername')
        logging.info(f"Logout request from {addr}")
        
        # Find and remove player by writer object
        username_to_remove = None
        for username, data in self.players.items():
            if data.get("writer") == writer:
                username_to_remove = username
                break
                
        if username_to_remove:
            del self.players[username_to_remove]
            logging.info(f"Player {username_to_remove} logged out")
            
        # No need to respond as client is disconnecting

    """------------------------------------------- Manejo de Servidores de Juego ------------------------------------------- """
    
    def start_message_listener(self):
        """Start a separate thread to listen for messages"""
        # Capture the main event loop reference before creating the thread
        main_loop = asyncio.get_event_loop()
        
        def listener_thread():
            while True:
                try:
                    # This blocks until a message is available without wasting CPU
                    message = self.message_queue.get()
                    
                    # Schedule processing in the event loop and properly handle the future
                    future = asyncio.run_coroutine_threadsafe(
                        self.process_message(message), 
                        main_loop  # Use the captured main event loop
                    )
                    
                    # Add a callback to handle completion and capture any exceptions
                    def done_callback(fut):
                        try:
                            fut.result()  # This will raise any exceptions from the coroutine
                        except Exception as e:
                            logging.error(f"Error in process_message coroutine: {e}")
                    
                    future.add_done_callback(done_callback)
                    
                except Exception as e:
                    logging.error(f"Error in message listener thread: {e}")
        
        thread = threading.Thread(target=listener_thread, daemon=True)
        thread.start()
        logging.info("Message listener thread started")

    async def process_message(self, message):
        """Process a message from the queue in the event loop"""
        try:
            logging.debug(f"Received message from game server: {message}")
            self.server_communication.execute_command(message)
        except Exception as e:
            logging.error(f"Error processing message: {e}")
    
    def handle_server_ok(self, pid, *args):
        """Handle OK message from a game server"""
        logging.info(f"Server {pid} reported OK status")
        
        # Generate a new puzzle and add it to the queue
        puzzle = KryptoLogic.generar_puzzle()
        asyncio.create_task(self.puzzle_queue.put(puzzle))
        logging.info(f"New puzzle generated for server {pid}")

    def handle_server_error(self, pid, *args):
        """Handle error message from a game server"""
        error_msg = args[0] if args else "Unknown error"
        logging.error(f"Error reported by server {pid}: {error_msg}")
        
        # Check if we need to terminate the server
        server_id_to_remove = None
        for server_id, details in self.servers.items():
            if details.get("pid") == pid:
                server_id_to_remove = server_id
                break
                
        if server_id_to_remove:
            # Only terminate if it's a critical error
            if "critical" in error_msg.lower():
                self.terminate_server_process(pid)
                del self.servers[server_id_to_remove]
                logging.warning(f"Server {server_id_to_remove} (PID: {pid}) terminated due to critical error")

    def handle_server_kill(self, pid, *args):
        """Handle kill request from a game server"""
        logging.info(f"Kill request from server with PID {pid}")
        
        # Terminate the process
        self.terminate_server_process(pid)
        
        # Remove from servers list
        server_id_to_remove = None
        for server_id, details in self.servers.items():
            if details.get("pid") == pid:
                server_id_to_remove = server_id
                break
                
        if server_id_to_remove:
            del self.servers[server_id_to_remove]
            logging.info(f"Server {server_id_to_remove} (PID: {pid}) removed from active servers")
    
    def terminate_server_process(self, pid):
        """Safely terminate a server process"""
        try:
            if pid in self.processes:
                self.processes[pid].terminate()
                self.processes[pid].join(timeout=2)
                del self.processes[pid]
                logging.info(f"Process with PID {pid} terminated successfully")
            else:
                logging.warning(f"No process found with PID {pid}")
        except Exception as e:
            logging.error(f"Error terminating process {pid}: {e}")
    
    async def shutdown(self):
        """Clean shutdown of the main server"""
        logging.info("Shutting down MainServer...")
        
        # Terminate all game server processes
        for pid in list(self.processes.keys()):
            self.terminate_server_process(pid)
            
        # Clear all data structures
        self.servers.clear()
        self.players.clear()
        self.processes.clear()
        
        logging.info("MainServer shutdown complete")

if __name__ == "__main__":
    main_server = MainServer()
    try:
        asyncio.run(main_server.start_main_server())
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
    finally:
        # Ensure clean shutdown
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main_server.shutdown())
        loop.close()