import uuid
import time
import socket
import asyncio
import logging
import threading
import multiprocessing
import sys
import os

from common.social import LogMessages as Logs
from common.social import UserMainMessages as UM
from common.social import InterfaceMessages as IM
from common.social import MainServerMessages as SM
from common.logger import Logger
from common.communication import Communication

# Import the new centralized logger
from common.logger import Logger

from puzzle.logic import KryptoLogic
from puzzle.server_factory import ServerFactory

class MainServer:
    def __init__(self, host='localhost', port=5000, max_servers=5, debug=False):
        self.host = host
        self.port = port
        self.max_servers = max_servers
        self.debug_enabled = debug
        
        # Set up logging using the new centralized logger
        Logger.configure(debug)
        
        # Puzzles y servidores
        self.puzzle_queue = multiprocessing.Queue()
        self.message_queue = multiprocessing.Queue()
        self.server_factory = ServerFactory(self.puzzle_queue, self.message_queue, debug)
        
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

        # Start the message listener thread
        self.start_message_listener()

        self.processes = {}  # Diccionario {pid: process}
        self.servers = {}  # Diccionario {server_id: {"port": port, "name": name, "mode": mode}}
        self.players = {}  # Dictionary to track connected players {username: {"id": player_id}}
        self.pending_servers = {}  # Dictionary to track servers being created
        self.failed_servers = set()  # Set of PIDs that failed to start

        self.main_logger.info(f"MainServer initialized with host={host}, port={port}, max_servers={max_servers}, debug={debug}")
    
    def enable_debug(self):
        """Enable debug mode"""
        if not self.debug_enabled:
            self.debug_enabled = True
            Logger.configure(True)
            self.main_logger.info("Debug mode enabled")
    
    def disable_debug(self):
        """Disable debug mode"""
        if self.debug_enabled:
            self.debug_enabled = False
            Logger.configure(False)
            self.main_logger.info("Debug mode disabled")
    
    def toggle_debug(self):
        """Toggle debug mode on/off"""
        if self.debug_enabled:
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
            SM.KILL: self.handle_server_kill,
        }
        self.server_communication.define_all_commands(handlers)
        logging.info("Server command handlers registered")

    async def start_main_server(self):
        """Inicia el servidor principal para manejar jugadores y servidores clásicos."""
        await self.initialize_puzzles()


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
                server_list.append(
                    f"ID: {server_id}, Name: {details['name']}, Mode: {details['mode']}"
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
        """Permite al jugador unirse a un servidor existente."""
        addr = writer.get_extra_info('peername')
        server_id = server_id.strip()  # Clean up any whitespace
        logging.info(f"Join server request for '{server_id}' from {addr}")
        
        try:
            if server_id in self.servers:
                server_details = self.servers[server_id]
                server_name = server_details["name"]
                server_port = server_details["port"]
                server_mode = server_details["mode"]
                
                response = f"{UM.JOIN_SUCCESS}|{server_name}|{server_port}|{server_mode}"
                await self.users_communication.send_message_async(writer, response)
                Logger.log_outgoing(logging, addr, response)
                logging.info(f"Client {addr} joining server {server_id} ({server_name})")
            else:
                # Debug which server IDs are available
                available_ids = list(self.servers.keys())
                logging.warning(f"Server ID '{server_id}' not found. Available IDs: {available_ids}")
                
                response = f"{UM.JOIN_FAIL}|Server not found or no longer available"
                await self.users_communication.send_message_async(writer, response)
                Logger.log_outgoing(logging, addr, response)
                logging.warning(f"Client {addr} attempted to join nonexistent server {server_id}")
        except Exception as e:
            logging.error(f"Error processing join request for {server_id} from {addr}: {e}")

    async def handle_create_server(self, writer, server_name, server_mode, number):
        """Crea un nuevo servidor y lo registra."""
        addr = writer.get_extra_info('peername')
        logging.info(f"Create server request: {server_name}, {server_mode} from {addr}")
        try:
            # Validate server settings
            if not server_name or len(server_name) < 3:
                response = f"{UM.CREATE_FAIL}|Invalid server name (minimum 3 characters)"
                await self.users_communication.send_message_async(writer, response)
                Logger.log_outgoing(logging, addr, response)
                return
                
            if server_mode not in ["classic", "competitive"]:
                response = f"{UM.CREATE_FAIL}|Invalid game mode (must be 'classic' or 'competitive')"
                await self.users_communication.send_message_async(writer, response)
                Logger.log_outgoing(logging, addr, response)
                return
                
            # Check if we've reached the maximum number of servers
            if len(self.servers) >= self.max_servers:
                response = f"{UM.CREATE_FAIL}|Maximum number of servers reached"
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
            try:
                response = f"{UM.CREATE_FAIL}|Server error processing create request"
                await self.users_communication.send_message_async(writer, response)
                Logger.log_outgoing(logging, addr, response)
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
        message_logger = logging.getLogger("message_listener")
        
        def listener_thread():
            message_logger.info("Message listener thread started")
            while True:
                try:
                    # This blocks until a message is available without wasting CPU
                    message = self.message_queue.get()
                    Logger.log_incoming(message_logger, "GameServer", message)
                    
                    # Debug print only if debug is enabled
                    if self.debug_enabled:
                        print(f"Debug - Received message from GameServer: {message}")
                    
                    # Run the coroutine directly in a new event loop inside this thread
                    local_loop = asyncio.new_event_loop()
                    try:
                        local_loop.run_until_complete(self.process_message(message))
                    finally:
                        local_loop.close()
                    
                except Exception as e:
                    message_logger.error(f"Error in message listener thread: {e}")
                    import traceback
                    message_logger.error(traceback.format_exc())
        
        thread = threading.Thread(target=listener_thread, daemon=True)
        thread.start()
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
            if self.debug_enabled:
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
    import argparse
    
    parser = argparse.ArgumentParser(description="Krypto Main Server")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=5000, help="Server port")
    parser.add_argument("--max-servers", type=int, default=5, help="Maximum number of game servers")
    
    args = parser.parse_args()
    
    main_server = MainServer(host=args.host, port=args.port, 
                            max_servers=args.max_servers, debug=args.debug)
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