import abc
import asyncio
import logging
import os
from queue import Empty, Queue
import time

from common.social import MainServerMessages as SM

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
        self.logger = logging.getLogger(f"GameServer-{name}")
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)

        # Iniciar temporizador de autodestrucción (60 segundos sin jugadores)
        self.idle_timer = None
        self.idle_timer_active = False
        
    def start(self):
        """Start the game server"""
        try:
            # Initialize puzzles
            self.initialize_puzzles()
            
            # Send OK message to main server after initialization
            self.message_queue.put(f"{SM.OK}|{os.getpid()}")
            self.logger.info(f"Sent OK message with PID {os.getpid()} to main server")
            
            # Run the server
            asyncio.run(self.run_server())
        except Exception as e:
            self.logger.error(f"Fatal error in game server: {e}")
            self.message_queue.put(f"{SM.ERROR}|{os.getpid()}|{str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
    
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
                    
        except asyncio.CancelledError:
            self.logger.debug("Idle timer was cancelled because players joined")
        except Exception as e:
            self.logger.error(f"Error in idle timer: {e}")
    
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
            
    async def run_server(self):
        """Run the game server - async entry point"""
        try:
            server = await asyncio.start_server(
                self.handle_client_connection,
                'localhost',
                self.port
            )
            
            self.logger.info(f"Game server running on port {self.port}")

            self.idle_timer_active = True
            self.idle_timer = asyncio.create_task(self.start_idle_timer())
        
            
            async with server:
                await server.serve_forever()
                
        except Exception as e:
            self.logger.error(f"Error running game server: {e}")
            self.message_queue.put(f"{SM.ERROR}|{os.getpid()}|{str(e)}")
            
    @abc.abstractmethod
    def get_initial_puzzles(self):
        """Get initial puzzles for the game - must be implemented by subclasses"""
        pass
    
    @abc.abstractmethod
    async def handle_client_connection(self, reader, writer):
        """Handle a client connection - can be overridden by subclasses"""
        pass
        
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
