import logging
import multiprocessing
from queue import Queue

from puzzle.server_classic import ClassicServer
from puzzle.server_competitive import CompetitiveServer

logger = logging.getLogger(__name__)

class ServerFactory:
    """Factory class for creating different types of game servers"""
    
    def __init__(self, puzzle_queue:Queue, message_queue:Queue):
        """Initialize the server factory"""
        self.puzzle_queue = puzzle_queue
        self.message_queue = message_queue
        self.next_port = 5001
        
        logger.info("Server factory initialized")
    
    def create_server(self, name, mode, number):
        """Create a new server of the specified type"""
        try:
            # Create server instance based on mode
            server_class = self.get_server_class(mode)
            if not server_class:
                logger.error(f"Invalid server mode: {mode}")
                return None
            
            # Set up port
            port = self.get_next_port()
            
            # Create the server in a new process
            process = multiprocessing.Process(
                target=self.run_server,
                args=(server_class, name, self.puzzle_queue, self.message_queue, port, int(number))
            )
            process.daemon = True
            process.start()
            
            logger.info(f"Created {mode} server '{name}' on port {port}")
            return process.pid, port
            
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
    def run_server(server_class, name, puzzle_queue, message_queue, port, number):
        """Run a server in a separate process"""
        try:
            server = server_class(name, puzzle_queue, message_queue, port, number)
            server.start()
        except Exception as e:
            logger.error(f"Server process error: {e}")