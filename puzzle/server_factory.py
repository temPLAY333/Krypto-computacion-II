import logging
import multiprocessing
from queue import Queue
import os
import socket
from common.social import MainServerMessages as SM

from puzzle.server_classic import ClassicServer
from puzzle.server_competitive import CompetitiveServer

logger = logging.getLogger(__name__)

class ServerFactory:
    """Factory class for creating different types of game servers"""
    
    def __init__(self, puzzle_queue:Queue, message_queue:Queue, debug=False):
        """Initialize the server factory"""
        self.puzzle_queue = puzzle_queue
        self.message_queue = message_queue
        self.next_port = 5001
        self.debug = debug
        
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
            port = self._find_available_port()
            
            # Create the server in a new process
            process = multiprocessing.Process(
                target=self._start_game_server,
                args=(name, mode, number, port, self.puzzle_queue, self.message_queue, self.debug)
            )
            process.daemon = True
            process.start()
            
            logger.info(f"Created {mode} server '{name}' with PID {process.pid} on port {port}")
            return process.pid, port, process  # Return the process object as well
            
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
    
    def _find_available_port(self, start_port=5001):
        """Find an available port starting from start_port"""
        port = start_port
        max_attempts = 100
        
        for _ in range(max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except OSError:
                port += 1
                
        raise RuntimeError("Could not find an available port after multiple attempts")
    
    @staticmethod
    def _start_game_server(name, mode, number, port, puzzle_queue, message_queue, debug=False):
        """Function that runs in the new process to start a game server"""
        try:
            # Configure logging for this process - with updated date format
            log_level = logging.DEBUG if debug else logging.INFO
            logging.basicConfig(
                level=log_level,
                format=f'%(asctime)s - %(name)s[{os.getpid()}] - %(levelname)s - %(message)s',
                datefmt='%m-%d %H:%M:%S'
            )
            logger = logging.getLogger("game_server")
            
            # Create specific server type based on mode
            if mode.lower() == 'classic':
                from puzzle.server_classic import ClassicServer
                server = ClassicServer(name, port, puzzle_queue, message_queue, debug=debug)
            elif mode.lower() == 'competitive':
                from puzzle.server_competitive import CompetitiveServer
                server = CompetitiveServer(name, port, puzzle_queue, message_queue, debug=debug)
            else:
                raise ValueError(f"Invalid game mode: {mode}")
            
            # Don't send OK message here - let the server do it
            # The OK message will be sent from AbstractGameServer.start()
            
            # Start the server (this should block until the server stops)
            server.start()
            
        except Exception as e:
            # Log and notify main server of error with proper format
            logging.error(f"Error in game server: {e}")
            message_queue.put(f"{SM.ERROR}|{os.getpid()}|{str(e)}")