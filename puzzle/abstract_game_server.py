import os
import abc
import socket
import asyncio
import logging
from queue import Empty, Queue

from common.social import MainServerMessages as SM
from common.social import ServerClientMessages as SCM
from common.logger import Logger
from common.network import NetworkManager

class AbstractGameServer(abc.ABC):
    """Abstract base class for different game server types"""
    
    def __init__(self, name, port, puzzle_queue: Queue, message_queue: Queue, debug=False):
        self.name = name
        self.port = port
        self.puzzle_queue = puzzle_queue
        self.message_queue = message_queue
        self.clients = {}  # Track connected clients {client_id: {reader, writer, last_activity}}
        self.current_puzzle = list()
        self.debug_enabled = debug
        
        # Configure logger
        self.logger = Logger.get(f"GameServer-{name}")
        Logger.configure(debug)

        # Iniciar temporizador de autodestrucción (60 segundos sin jugadores)
        self.idle_timer = None
        self.idle_timer_active = False
        
    async def start(self, host='0.0.0.0'):
        """Start the game server"""
        # Detectar si es dirección IPv4 explícita (como 192.168.0.115)
        is_ipv4_address = '.' in host and all(part.isdigit() and int(part) <= 255 
                                              for part in host.split('.') if part)
        
        try:
            # Usar socket IPv4 si la dirección es IPv4
            if is_ipv4_address:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.is_ipv6 = False
                self.logger.info(f"Using IPv4 socket for IPv4 address {host}")
            else:
                # Intentar con IPv6 si está disponible
                if NetworkManager.is_ipv6_available():
                    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                    self.is_ipv6 = True
                    self.logger.info(f"Using IPv6 socket for address {host}")
                else:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.is_ipv6 = False
                    self.logger.info(f"Using IPv4 socket (IPv6 not available) for address {host}")
            
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, self.port))
            sock.listen(10)
            
            # Convertir a asyncio server
            self.server = await asyncio.start_server(
                self.handle_client_connection,
                sock=sock
            )
            
            # Inicializar puzzles
            self.initialize_puzzles()
            
            # Mantener el servidor corriendo
            async with self.server:
                await self.server.serve_forever()
            
        except Exception as e:
            self.logger.error(f"Error starting server: {e}")
            raise

    def enable_debug(self):
        """Enable debug mode"""
        if not self.debug_enabled:
            self.debug_enabled = True
            self.logger.setLevel(logging.DEBUG)
            self.logger.info("Debug mode enabled")
    
    def disable_debug(self):
        """Disable debug mode"""
        if self.debug_enabled:
            self.debug_enabled = False 
            self.logger.setLevel(logging.INFO)
            self.logger.info("Debug mode disabled")

    def initialize_puzzles(self):
        """Get initial puzzles from queue"""
        try:
            initial_puzzles = self.get_initial_puzzles()
            if initial_puzzles:
                self.current_puzzle = initial_puzzles[0]
            else:
                self.current_puzzle = self.puzzle_queue.get(timeout=5)
                
            self.logger.info(f"Initial puzzle set: {self.current_puzzle}")
        except Exception as e:
            self.logger.error(f"Error initializing puzzles: {e}")
            raise
            
    @abc.abstractmethod
    def get_initial_puzzles(self):
        """Get initial puzzles for the game - must be implemented by subclasses"""
        pass
    
    async def handle_client_connection(self, reader, writer):
        """Handle a client connection"""
        addr = writer.get_extra_info('peername')
        client_id = f"{addr[0]}:{addr[1]}"
        
        self.logger.info(f"New client connected: {client_id}")
        
        # Desactivar temporizador de inactividad si es el primer cliente
        if self.idle_timer_active and len(self.clients) == 0:
            self.logger.info("First player joined. Canceling idle timer.")
            self.idle_timer_active = False
        
        # Añadir cliente a la estructura de seguimiento
        self.clients[client_id] = {
            "reader": reader,
            "writer": writer,
            "last_activity": asyncio.get_event_loop().time(),
            "disconnected": False
        }
        
        # Inicializar player con estado vacío
        if client_id not in self.players:
            self.players[client_id] = {"username": client_id, "state": None}
        
        # Enviar el puzzle actual al nuevo cliente
        if self.current_puzzle:
            await asyncio.sleep(0.5)
            await self.comm.send_message_async(writer, f"{SCM.NEW_PUZZLE}|{self.current_puzzle}\n")
        
        # CORREGIDO: Notificar al servidor principal con manejo de errores
        try:
            if hasattr(self, 'message_queue') and self.message_queue:
                try:
                    self.message_queue.put_nowait(f"{SM.PLAYER_JOIN}|{os.getpid()}")
                except Exception as e:
                    self.logger.warning(f"Could not notify main server of player join: {e}")
        except Exception as e:
            self.logger.error(f"Error accessing message queue: {e}")
        
        # Broadcast actualizado de estadísticas
        await self.broadcast_game_stats()

        # Manejar mensajes del jugador
        await self.handle_player_message(reader, writer, client_id)
    
    async def handle_player_message(self, reader, writer, client_id):
        """Handle a message from a player"""
        try:
            while not writer.is_closing():
                try:
                    data = await asyncio.wait_for(reader.readline(), timeout=1.0)
                    if not data:  # Connection closed
                        break
                        
                    message = data.decode('utf-8').strip()
                    if message:
                        self.logger.debug(f"Received from {client_id}: {message}")
                        await self.comm.handle_async_command(message, writer)
                        
                    # Actualizar timestamp de última actividad
                    self.clients[client_id]["last_activity"] = asyncio.get_event_loop().time()
                        
                except asyncio.TimeoutError:
                    # Esto es normal, solo verificar si el cliente sigue conectado
                    continue
                except Exception as e:
                    self.logger.error(f"Error processing client message: {e}")
                    break
        except Exception as e:
            self.logger.error(f"Error in client connection handler: {e}")
        finally:
            # Cleanup when client disconnects
            if client_id in self.clients:
                self.clients[client_id]["disconnected"] = True
                
            self.logger.info(f"Client disconnected: {client_id}")
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                self.logger.error(f"Error closing client connection: {e}")
                
            # Process player exit
            await self.handle_player_exit(writer)
        
        
    @abc.abstractmethod
    async def broadcast_message(self, message):
        """Send message to all clients - must be implemented by subclasses"""
        pass
        
    def get_next_puzzle(self):
        """Get the next puzzle from the queue or generate one if needed"""
        try:
            if not self.puzzle_queue.empty():
                next_puzzle = self.puzzle_queue.get()
                self.message_queue.put(f"{SM.OK}|{os.getpid()}")
                self.logger.info(f"Got new puzzle from queue: {next_puzzle}")
                return next_puzzle
            else:
                self.logger.warning("Puzzle queue empty, generating a random puzzle")
                # Import here to avoid circular imports
                random_puzzle = [4,7,3,6,2]
                self.logger.info(f"Generated random puzzle: {random_puzzle}")
                return random_puzzle
        except Exception as e:
            self.logger.error(f"Error getting next puzzle: {e}")
            return None
    
    async def start_idle_timer(self):
        """Start a timer that will shut down the server if no players join within 60 seconds"""
        try:
            self.logger.info("Starting 60-second idle timer for player connection")
            
            # Esperar 60 segundos
            await asyncio.sleep(60)
            
            # Solo continuar si el temporizador sigue activo
            if self.idle_timer_active:
                # Verificar si hay jugadores activos
                active_clients = {cid: data for cid, data in self.clients.items() 
                                if not data.get("disconnected", False)}
                
                if not active_clients:
                    self.logger.info("No players joined within 60 seconds. Auto-shutting down server.")
                    self.message_queue.put(f"{SM.KILL_SERVER}|{os.getpid()}")
                else:
                    self.logger.info(f"Players have joined ({len(active_clients)}). Server will continue running.")
                    self.idle_timer_active = False
                    
                    # Iniciar verificación periódica de clientes
                    asyncio.create_task(self.check_clients_periodically())
                    
        except asyncio.CancelledError:
            self.logger.debug("Idle timer was cancelled")
        except Exception as e:
            self.logger.error(f"Error in idle timer: {e}")
            
    async def check_clients_periodically(self):
        """Verificar periódicamente el estado de los clientes"""
        try:
            while True:
                await asyncio.sleep(30)  # Verificar cada 30 segundos
                
                # Verificar clientes inactivos
                now = asyncio.get_event_loop().time()
                inactive_timeout = 120  # 2 minutos sin actividad
                
                for client_id, client_data in list(self.clients.items()):
                    # Si el cliente ya está marcado como desconectado, ignorarlo
                    if client_data.get("disconnected", False):
                        continue
                        
                    # Verificar si el cliente ha estado inactivo demasiado tiempo
                    last_activity = client_data.get("last_activity", 0)
                    if now - last_activity > inactive_timeout:
                        self.logger.warning(f"Client {client_id} inactive for too long, marking as disconnected")
                        self.clients[client_id]["disconnected"] = True
                        
                        writer = client_data.get("writer")
                        if writer and not writer.is_closing():
                            try:
                                writer.close()
                            except:
                                pass
                
                # Verificar si todos los clientes están desconectados
                active_clients = {cid: data for cid, data in self.clients.items() 
                                 if not data.get("disconnected", False)}
                                 
                if not active_clients and len(self.clients) > 0:
                    self.logger.info("All clients disconnected. Auto-shutting down server.")
                    self.message_queue.put(f"{SM.KILL_SERVER}|{os.getpid()}")
                    break
                    
        except Exception as e:
            self.logger.error(f"Error checking clients: {e}")

    def check_message_queue(self):
        """Verificar si la cola de mensajes sigue activa"""
        try:
            # Prueba de verificación simple
            self.message_queue.put_nowait(f"{SM.HEARTBEAT}|{os.getpid()}")
            return True
        except Exception as e:
            self.logger.warning(f"Message queue appears to be unavailable: {e}")
            return False
    
    def safe_queue_put(self, message):
        """Poner un mensaje en la cola de forma segura"""
        try:
            if hasattr(self, 'message_queue') and self.message_queue:
                try:
                    self.message_queue.put_nowait(message)
                    return True
                except:
                    # Silenciosamente fallar si la cola está llena o cerrada
                    return False
        except:
            # Ignorar cualquier error de acceso a la cola
            return False