import abc
import asyncio
import logging
import os
from queue import Queue
import socket
import time

from common.social import MainServerMessages as SM

class AbstractGameServer(abc.ABC):
    """Abstract base class for different game server types"""
    
    def __init__(self, name, port, puzzle_queue, message_queue, debug=False):
        self.name = name
        self.port = port
        self.puzzle_queue = puzzle_queue
        self.message_queue = message_queue
        self.clients = {}  # Track connected clients
        self.current_puzzle = None
        self.debug_enabled = debug
        
        # Configure logger with updated format
        self.logger = logging.getLogger(f"GameServer-{name}")
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        
    def start(self):
        """Start the game server"""
        try:
            # Initialize puzzles
            self.initialize_puzzles()
            
            # Send OK message to main server after initialization
            # This ensures GameServer sends it, not ServerFactory
            self.message_queue.put(f"{SM.OK}|{os.getpid()}")
            self.logger.info(f"Sent OK message with PID {os.getpid()} to main server")
            
            # Run the server
            asyncio.run(self.run_server())
        except Exception as e:
            self.logger.error(f"Fatal error in game server: {e}")
            self.message_queue.put(f"{SM.ERROR}|{os.getpid()}|{str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
    
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
            
            async with server:
                await server.serve_forever()
                
        except Exception as e:
            self.logger.error(f"Error running game server: {e}")
            self.message_queue.put(f"{SM.ERROR}|{str(e)}")
            
    @abc.abstractmethod
    def get_initial_puzzles(self):
        """Get initial puzzles for the game - must be implemented by subclasses"""
        pass
    
    @abc.abstractmethod
    def check_after_solution(self, solution):
        """Check what happens after a solution is submitted - must be implemented by subclasses"""
        pass
    
    async def handle_client_connection(self, reader, writer):
        """Handle a client connection"""
        addr = writer.get_extra_info('peername')
        client_id = f"{addr[0]}:{addr[1]}"
        
        self.logger.info(f"New client connected: {client_id}")
        
        # Add client to tracking
        self.clients[client_id] = {
            "reader": reader,
            "writer": writer,
            "last_activity": time.time()
        }
        
        try:
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                    
                message = data.decode()
                self.logger.debug(f"Received from {client_id}: {message}")
                
                # Process message - implement in subclasses if needed
                await self.process_client_message(client_id, message)
                
        except Exception as e:
            self.logger.error(f"Error handling client {client_id}: {e}")
        finally:
            # Clean up
            writer.close()
            await writer.wait_closed()
            if client_id in self.clients:
                del self.clients[client_id]
            self.logger.info(f"Client disconnected: {client_id}")
            
    async def process_client_message(self, client_id, message):
        """Process a message from a client - override in subclasses if needed"""
        pass
        
    def get_next_puzzle(self):
        """Get the next puzzle from the queue"""
        try:
            puzzle = self.puzzle_queue.get(timeout=5)
            self.current_puzzle = puzzle
            return puzzle
        except Exception as e:
            self.logger.error(f"Error getting next puzzle: {e}")
            return None
