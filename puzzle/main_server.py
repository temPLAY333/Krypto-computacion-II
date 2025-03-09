import uuid
import socket
import asyncio
import logging
import threading
import multiprocessing
from queue import Queue, Empty
from typing import Any, Dict, Optional

from common.logger import Logger
from common.social import LogMessages as Logs
from common.social import UserMainMessages as UM
from common.social import InterfaceMessages as IM
from common.social import MainServerMessages as SM
from common.network import NetworkManager
from common.communication import Communication

from puzzle.logic import KryptoLogic
from puzzle.server_factory import ServerFactory

class MainServer:
    def __init__(self, host='0.0.0.0', port=5000, debug=False):
        """Initialize MainServer"""
        self.host = host  # Usar 0.0.0.0 para escuchar en todas las interfaces
        self.port = port
        self.debug = debug
        self.max_servers = 5
        
        # Set up logging using the new centralized logger
        Logger.configure(debug)

        self.server_ip = self.get_server_ip()
        logging.info(f"Server will use {self.server_ip} for external communications")
    
        # Puzzles y servidores
        self.puzzle_queue = multiprocessing.Queue()
        self.message_queue = multiprocessing.Queue()
        self.server_factory = ServerFactory(self.server_ip, self.puzzle_queue, self.message_queue)
        
        # Create loggers using the centralized logger
        self.server_logger = Logger.get("ServerCommunication", debug)
        self.users_logger = Logger.get("UserCommunication", debug)
        self.main_logger = Logger.get("MainServer", debug)
        
        # Initialize communication objects
        self.users_communication = Communication(self.users_logger) 
        self.server_communication = Communication(self.server_logger)
        
        # Register command handlers for both communication channels
        self.register_user_command_handlers()
        self.register_server_command_handlers()

        self.processes: Dict[int, Any] = {}  # {pid: process}
        self.servers: Dict[str, Dict[str, Any]] = {}  # {server_id: {"port": port, "name": name, ...}}
        self.players: Dict[str, Dict[str, Any]] = {}  # {username: {"id": player_id, ...}}
        self.pending_servers: Dict[int, Any] = {}   # Dictionary to track servers being created
        self.failed_servers = set()  # Set of PIDs that failed to start

        self.main_logger.info(f"MainServer initialized with host={host}, port={port}, debug={debug}")
    
    def enable_debug(self):
        """Enable debug mode"""
        if not self.debug:
            self.debug = True
            Logger.configure(True)
            self.main_logger.info("Debug mode enabled")
    
    def disable_debug(self):
        """Disable debug mode"""
        if self.debug:
            self.debug = False
            Logger.configure(False)
            self.main_logger.info("Debug mode disabled")
    
    def toggle_debug(self):
        """Toggle debug mode on/off"""
        if self.debug:
            self.disable_debug()
        else:
            self.enable_debug()

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
        self.main_logger.info("User command handlers registered")

    def register_server_command_handlers(self):
        """Register all command handlers for server communication"""
        handlers = {
            SM.OK: self.handle_server_ok,
            SM.ERROR: self.handle_server_error,
            SM.KILL_SERVER: self.handle_server_kill,
            SM.PLAYER_JOIN: self.handle_player_join,
            SM.PLAYER_EXIT: self.handle_player_exit,
        }
        self.server_communication.define_all_commands(handlers)
        logging.info("Server command handlers registered")

    async def start_main_server(self):
        """Inicia el servidor principal para manejar jugadores y servidores clásicos."""
        # Usar '0.0.0.0' para IPv4 o '::' para IPv6 (escuchar en todas las interfaces)
        if self.host == 'localhost':
            # Reemplazar localhost con la interfaz apropiada
            self.host = '::' if NetworkManager.is_ipv6_available() else '0.0.0.0'
        
        self.main_logger.info(f"Starting main server on {self.host}:{self.port}")
        
        # Crear el socket manualmente para evitar problemas de resolución
        try:
            # Intentar con IPv6 primero si está disponible
            if NetworkManager.is_ipv6_available() and self.host in ['::']:
                sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                # Permitir conexiones IPv4 también
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                sock.bind((self.host, self.port))
                self.is_ipv6 = True
                self.main_logger.info(f"Using IPv6 socket on {self.host}:{self.port}")
            else:
                # Usar IPv4
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((self.host, self.port))
                self.is_ipv6 = False
                self.main_logger.info(f"Using IPv4 socket on {self.host}:{self.port}")
            
            sock.listen(100)  # Permitir múltiples conexiones pendientes
            
            # Convertir a asyncio server
            server = await asyncio.start_server(
                self.handle_new_player,
                sock=sock
            )
            
            # Inicializar puzzles y listener
            await self.initialize_puzzles()
            self.start_message_listener()
            
            # Mantener el servidor corriendo
            await self.run_server(server, "Main Server")
            
        except Exception as e:
            self.main_logger.error(f"Error starting server: {e}")
            raise  # Re-lanzar para permitir un manejo adecuado en el código principal

    async def initialize_puzzles(self):
        """Inicializar la cola con puzzles iniciales."""
        loop = asyncio.get_running_loop()
        for i in range(self.max_servers):
            # Use run_in_executor to call synchronous code from async context
            await loop.run_in_executor(None, 
                                    lambda: self.puzzle_queue.put(KryptoLogic.generar_puzzle()))
        logging.info("Puzzles inicializados")

    def get_server_ip(self):
        """Obtener IP real del servidor para comunicaciones externas"""
        try:
            # No usar localhost/127.0.0.1 - buscar una IP accesible desde la red
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Conectar a un DNS público para determinar la interfaz utilizada
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            logging.warning(f"Couldn't determine server IP: {e}. Using localhost.")
            return "localhost"

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
                Logger.log_incoming(logging, addr, message)
                
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
                    error_msg = f"{UM.ERROR}|Server internal error: {str(e)}"
                    await self.users_communication.send_message_async(writer, error_msg)
                    Logger.log_outgoing(logging, addr, error_msg)
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
            response = UM.OK
            await self.users_communication.send_message_async(writer, response)
            Logger.log_outgoing(logging, addr, response)
        except Exception as e:
            logging.error(f"Error sending OK response to {addr}: {e}")

    async def handle_login(self, writer, username):
        """Maneja el login del jugador."""
        addr = writer.get_extra_info('peername')
        try:
            # Basic username validation
            if not username or not (3 <= len(username) <= 20):
                response = f"{UM.LOGIN_FAIL}|Invalid username format"
                await self.users_communication.send_message_async(writer, response)
                Logger.log_outgoing(logging, addr, response)
                return
                
            # Check if username is already taken
            if username in self.players:
                response = f"{UM.LOGIN_FAIL}|Username already taken"
                await self.users_communication.send_message_async(writer, response)
                Logger.log_outgoing(logging, addr, response)
                return
                
            # Register the player
            player_id = str(uuid.uuid4())[:8]
            self.players[username] = {"id": player_id, "writer": writer}
            logging.info(f"Jugador conectado: {username} (ID: {player_id})")
            
            # Send success response
            response = f"{UM.LOGIN_SUCCESS}"
            await self.users_communication.send_message_async(writer, response)
            Logger.log_outgoing(logging, addr, response)
            logging.info(f"Login successful for {username} from {addr}")
        except Exception as e:
            logging.error(f"Error in login for {username} from {addr}: {e}")
            try:
                response = f"{UM.LOGIN_FAIL}|Server error during login"
                await self.users_communication.send_message_async(writer, response)
                Logger.log_outgoing(logging, addr, response)
            except:
                pass  # If we can't send the error, we just log it

    async def handle_list_servers(self, writer):
        """Envía la lista de servidores disponibles al jugador."""
        addr = writer.get_extra_info('peername')
        logging.info(f"Server list requested from {addr}")
        try:
            if not self.servers:
                response = f"{UM.SERVER_LIST}|No servers available"
                await self.users_communication.send_message_async(writer, response)
                Logger.log_outgoing(logging, addr, response)
                return

            server_list = []
            for server_id, details in self.servers.items():
                # Usar .get() con valores por defecto para prevenir KeyError
                server_name = details.get('name', 'Unnamed')
                server_mode = details.get('mode', 'Unknown')
                player_count = details.get('player_count', 0)
                max_players = details.get('max_players', 8)
                
                server_list.append(
                    f"ID: {server_id}, Name: {server_name}, Mode: {server_mode}, Players: {player_count}/{max_players}"
                )
            
            server_list_str = "\n".join(server_list)
            response = f"{UM.SERVER_LIST}|{server_list_str}"
            await self.users_communication.send_message_async(writer, response)
            Logger.log_outgoing(logging, addr, response)
            logging.info(f"Sent server list to {addr}: {len(self.servers)} servers")
        except Exception as e:
            logging.error(f"Error sending server list to {addr}: {e}")
            try:
                response = f"{UM.ERROR}|Error retrieving server list"
                await self.users_communication.send_message_async(writer, response)
                Logger.log_outgoing(logging, addr, response)
            except:
                pass  # If we can't send the error, we just log it

    async def handle_server_choice(self, writer, server_id):
        """Handle a player's server choice"""
        addr = writer.get_extra_info('peername')
        server_id = str(server_id).strip()
        logging.info(f"Server choice from {addr}: {server_id}")
        
        if server_id not in self.servers:
            response = f"{UM.JOIN_FAIL}|Server not found"
            await self.users_communication.send_message_async(writer, response)
            Logger.log_outgoing(logging, addr, response)
            return
        
        # Check if the server has reached its maximum capacity
        server_details = self.servers[server_id]
        current_players = server_details.get("player_count", 0)
        max_players = server_details.get("max_players", 8)
        
        if current_players >= max_players:
            response = f"{UM.JOIN_FAIL}|Server is full ({current_players}/{max_players})"
            await self.users_communication.send_message_async(writer, response)
            Logger.log_outgoing(logging, addr, response)
            return
        
        # Send server details to the player
        name = self.servers[server_id]["name"]
        port = self.servers[server_id]["port"]
        mode = self.servers[server_id]["mode"]
        
        response = f"{UM.JOIN_SUCCESS}|{server_details['name']}|{self.server_ip}|{server_details['port']}|{server_details['mode']}"
        await self.users_communication.send_message_async(writer, response)
        Logger.log_outgoing(logging, addr, response)
        logging.info(f"Player from {addr} joined server {name} ({current_players+1}/{max_players})")

    async def handle_create_server(self, writer, server_name, server_mode, number):
        """Crea un nuevo servidor y lo registra."""
        addr = writer.get_extra_info('peername')
        logging.info(f"Create server request: {server_name}, {server_mode} from {addr}")
        try:
            # Validate server settings
            if not server_name or len(server_name) < 3:
                response = f"{UM.CREATE_FAIL}|Invalid server name (minimum 3 characters)"
            elif server_mode not in ["classic", "competitive"]:
                response = f"{UM.CREATE_FAIL}|Invalid game mode (must be 'classic' or 'competitive')"
            elif len(self.servers) >= self.max_servers:
                response = f"{UM.CREATE_FAIL}|Maximum number of servers reached"
            else:
                response = None

            if response:
                await self.users_communication.send_message_async(writer, response)
                Logger.log_outgoing(logging, addr, response)
                return
                
            # Create a new server
            server_id = str(uuid.uuid4())[:4]  # First 4 characters of UUID for server ID
            
            try:
                # Start server process
                result = self.server_factory.create_server(server_name, server_mode, number)
                if not result:
                    response = f"{UM.CREATE_FAIL}|Server creation failed"
                    await self.users_communication.send_message_async(writer, response)
                    Logger.log_outgoing(logging, addr, response)
                    return

                server_pid, server_port, server_process = result
                
                # IMPORTANT: Store the server process in the processes dictionary
                self.processes[server_pid] = server_process
                
                # Register server
                self.servers[server_id] = {
                    "pid": server_pid,
                    "name": server_name, 
                    "mode": server_mode,
                    "player_count": 0,
                    "max_players": int(number),
                    "port": server_port
                }
                
                # Notify client
                response = f"{UM.CREATE_SUCCESS}|{server_id}"
                await self.users_communication.send_message_async(writer, response)
                Logger.log_outgoing(logging, addr, response)
                self.main_logger.info(f"Created server with ID '{server_id}' (PID: {server_pid}): {server_name} ({server_mode}) on port {server_port}")
            
            except Exception as e:
                logging.error(f"Error creating server process: {e}")
                response = f"{UM.CREATE_FAIL}|Error starting server process"
                await self.users_communication.send_message_async(writer, response)
                Logger.log_outgoing(logging, addr, response)

        except Exception as e:
            logging.error(f"Error in create_server handler from {addr}: {e}")

            response = f"{UM.CREATE_FAIL}|Server error processing create request"
            await self.users_communication.send_message_async(writer, response)
            Logger.log_outgoing(logging, addr, response)


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
        message_logger = logging.getLogger("message_listener")
        self.shutdown_event = threading.Event()  # Evento para señalizar el cierre
        
        def listener_thread():
            message_logger.info("Message listener thread started")
            while not self.shutdown_event.is_set():  # Verificar si se debe detener
                try:
                    # Usar get con timeout para poder verificar el evento periódicamente
                    try:
                        message = self.message_queue.get(timeout=0.5)
                        Logger.log_incoming(message_logger, "GameServer", message)
                        
                        # Debug print only if debug is enabled
                        if self.debug:
                            print(f"Debug - Received message from GameServer: {message}")
                        
                        # Run the coroutine directly in a new event loop inside this thread
                        local_loop = asyncio.new_event_loop()
                        try:
                            local_loop.run_until_complete(self.process_message(message))
                        finally:
                            local_loop.close()
                    except Empty:
                        # Timeout - solo continuar para comprobar shutdown_event
                        pass
                        
                except Exception as e:
                    message_logger.error(f"Error in message listener thread: {e}")
                    import traceback
                    message_logger.error(traceback.format_exc())
                    
            message_logger.info("Message listener thread stopped")
        
        self.listener_thread = threading.Thread(target=listener_thread, daemon=True)
        self.listener_thread.start()
        self.main_logger.info("Message listener thread started")

    async def process_message(self, message):
        """Process a message from the queue in the event loop"""
        process_logger = logging.getLogger("process_message")
        
        try:
            process_logger.debug(f"Processing GameServer message: {message}")
            
            # Check if message has the expected format
            if not message or '|' not in message:
                process_logger.error(f"Invalid message format received: {message}")
                return
                
            # Create a dummy writer object since our handlers expect it
            dummy_writer = None
            
            # Debug output only if debug is enabled
            if self.debug:
                print(f"Debug - Parsing message: '{message}'")
                parts = message.split('|')
                print(f"Debug - Command: '{parts[0]}', Args: {parts[1:] if len(parts) > 1 else []}")
                
                # Direct execution for debugging in debug mode
                if parts[0] == SM.OK and len(parts) > 1:
                    print(f"Debug - Executing OK handler directly with PID: {parts[1]}")
                    await self.handle_server_ok(dummy_writer, parts[1], *parts[2:])
                    return
            
            # Use handle_async_command to find and execute the appropriate handler
            await self.server_communication.handle_async_command(message, dummy_writer)
            
        except Exception as e:
            process_logger.error(f"Error processing message: {e}")
            import traceback
            process_logger.error(traceback.format_exc())
    
    async def handle_server_ok(self, writer, pid, *args):
        """Handle OK message from a game server"""
        self.main_logger.info(f"Server with PID {pid} reported OK status")
        
        # Generate a new puzzle and add it to the queue
        puzzle = KryptoLogic.generar_puzzle()
        # Use run_in_executor for the blocking Queue.put operation
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.puzzle_queue.put(puzzle))
        
        self.main_logger.info(f"New puzzle generated for server with PID {pid}")
        Logger.log_outgoing(logging, f"GameServer-{pid}", f"PUZZLE: {puzzle}")

    async def handle_server_error(self, writer, pid, *args):
        """Handle error message from a game server"""
        error_msg = args[0] if args else "Unknown error"
        self.main_logger.error(f"Error reported by server with PID {pid}: {error_msg}")
        
        # Add to failed servers list
        self.failed_servers.add(int(pid))
        
        # If it was a pending server, remove it
        if int(pid) in self.pending_servers:
            del self.pending_servers[int(pid)]
        
        # Check if we need to terminate the server
        server_id_to_remove = None
        for server_id, details in self.servers.items():
            if str(details.get("pid")) == str(pid):
                server_id_to_remove = server_id
                break
                
        if server_id_to_remove:
            # Always terminate on error
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.terminate_server_process(pid))
            del self.servers[server_id_to_remove]
            self.main_logger.warning(f"Server with ID '{server_id_to_remove}' (PID: {pid}) terminated due to error")

    async def handle_server_kill(self, writer, pid, *args):
        """Handle kill request from a game server"""
        self.main_logger.info(f"Kill request from server with PID {pid}")
        
        # Terminate the process
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.terminate_server_process(pid))
        
        # Remove from servers list
        server_id_to_remove = None
        for server_id, details in self.servers.items():
            if str(details.get("pid")) == str(pid):
                server_id_to_remove = server_id
                break
                
        if server_id_to_remove:
            del self.servers[server_id_to_remove]
            self.main_logger.info(f"Server with ID '{server_id_to_remove}' (PID: {pid}) removed from active servers")

    def terminate_server_process(self, pid):
        """Safely terminate a server process"""
        pid = int(pid)  # Ensure pid is an integer
        try:
            if pid in self.processes:
                process = self.processes[pid]
                self.main_logger.info(f"Terminating process with PID {pid}")
                process.terminate()
                process.join(timeout=2)
                del self.processes[pid]
                self.main_logger.info(f"Process with PID {pid} terminated successfully")
            else:
                self.main_logger.warning(f"Cannot terminate: No process found with PID {pid}")
        except Exception as e:
            self.main_logger.error(f"Error terminating process with PID {pid}: {e}")

    async def handle_player_join(self, writer, pid, *args):
        """Handle player join notification from game server"""
        try:
            pid = int(pid)
            
            # Encontrar el servidor por PID
            server_id_to_update = None
            for server_id, details in self.servers.items():
                if details.get("pid") == pid:
                    server_id_to_update = server_id
                    break
                    
            if server_id_to_update:
                # Incrementar el contador de jugadores
                current_count = self.servers[server_id_to_update].get("player_count", 0)
                new_count = min(self.servers[server_id_to_update].get("max_players", 8), current_count + 1)
                self.servers[server_id_to_update]["player_count"] = new_count
                self.main_logger.debug(f"Player joined server {server_id_to_update}. New player count: {new_count}")
            else:
                self.main_logger.warning(f"Received player join for unknown server PID {pid}")
        except Exception as e:
            self.main_logger.error(f"Error handling player join: {e}")
    
    async def handle_player_exit(self, writer, pid):
        """Handle player exit notification from game server"""
        try:
            pid = int(pid)
            
            # Encontrar el servidor por PID
            server_id_to_update = None
            for server_id, details in self.servers.items():
                if details.get("pid") == pid:
                    server_id_to_update = server_id
                    break
                    
            if server_id_to_update:
                # Decrementar el contador de jugadores
                current_count = self.servers[server_id_to_update].get("player_count", 1)
                new_count = max(0, current_count - 1)  # Asegurar que no sea negativo
                self.servers[server_id_to_update]["player_count"] = new_count
                self.main_logger.debug(f"Player exited from server {server_id_to_update}. New player count: {new_count}")
            else:
                self.main_logger.warning(f"Received player exit for unknown server PID {pid}")
        except Exception as e:
            self.main_logger.error(f"Error handling player exit: {e}")

    async def shutdown(self):
        """Clean shutdown of the main server"""
        logging.info("Shutting down MainServer...")
        
        # Señalizar al hilo de escucha que debe terminar
        if hasattr(self, 'shutdown_event'):
            self.shutdown_event.set()
            
        # Esperar a que el hilo termine (opcional)
        if hasattr(self, 'listener_thread') and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=2.0)
        
        # Terminate all game server processes
        for pid in list(self.processes.keys()):
            self.terminate_server_process(pid)
                
        # Clear all data structures
        self.servers.clear()
        self.players.clear()
        self.processes.clear()
        
        logging.info("MainServer shutdown complete")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Krypto Main Server")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--host", default="0.0.0.0", help="Server host (use '0.0.0.0' for IPv4 or '::' for IPv6)")
    parser.add_argument("--port", type=int, default=5000, help="Server port")
    
    args = parser.parse_args()
    
    main_server = MainServer(host=args.host, port=args.port, debug=args.debug)
    try:
        asyncio.run(main_server.start_main_server())
    except KeyboardInterrupt:
        logging.info("Server stopped by Admin")
    finally:
        # Ensure clean shutdown
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main_server.shutdown())
        loop.close()