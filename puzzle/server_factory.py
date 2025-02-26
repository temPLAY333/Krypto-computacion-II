import logging
import multiprocessing
import threading
from queue import Queue

from puzzle.game_server import ClassicServer, CompetitiveServer

logger = logging.getLogger(__name__)

class ServerFactory:
    """Factory class for creating different types of game servers"""
    
    def __init__(self, puzzle_queue, message_queue):
        """Initialize the server factory"""
        self.puzzle_queue = puzzle_queue
        self.message_queue = message_queue
        self.next_port = 5001
        self.servers = {}  # Store active servers
        
        logger.info("Server factory initialized")
    
    def create_server(self, name, mode, max_players=8):
        """Create a new server of the specified type"""
        try:
            # Create server instance based on mode
            server_class = self.get_server_class(mode)
            if not server_class:
                logger.error(f"Invalid server mode: {mode}")
                return None
            
            # Set up communication queues
            server_puzzle_queue = multiprocessing.Queue()
            
            # Create the server in a new process
            port = self.get_next_port()
            process = multiprocessing.Process(
                target=self.run_server,
                args=(server_class, name, server_puzzle_queue, self.message_queue, port, max_players)
            )
            process.daemon = True
            process.start()
            
            server_id = process.pid
            self.servers[server_id] = {
                'process': process,
                'puzzle_queue': server_puzzle_queue,
                'name': name,
                'mode': mode,
                'port': port
            }
            
            # Start a thread to feed puzzles to the server
            puzzle_feeder = threading.Thread(
                target=self.feed_puzzles,
                args=(self.puzzle_queue, server_puzzle_queue),
                daemon=True
            )
            puzzle_feeder.start()
            
            logger.info(f"Created {mode} server '{name}' with ID {server_id} on port {port}")
            return server_id
            
        except Exception as e:
            logger.error(f"Failed to create server: {e}")
            return None
    
    def get_server_class(self, mode):
        """Get the server class based on the mode"""
        mode_lower = mode.lower()
        if mode_lower == 'classic':
            return ClassicServer
        elif mode_lower == 'competitive':
            return CompetitiveServer
        else:
            return None
    
    def get_next_port(self):
        """Get the next available port"""
        port = self.next_port
        self.next_port += 1
        return port
    
    @staticmethod
    def run_server(server_class, name, puzzle_queue, message_queue, port, max_players):
        """Run a server in a separate process"""
        try:
            server = server_class(name, puzzle_queue, message_queue, port, max_players)
            server.start()
        except Exception as e:
            logger.error(f"Server process error: {e}")
    
    @staticmethod
    def feed_puzzles(source_queue, target_queue):
        """Feed puzzles from the main queue to the server queue"""
        try:
            while True:
                puzzle = source_queue.get()
                target_queue.put(puzzle)
        except Exception as e:
            logger.error(f"Error feeding puzzles: {e}")