import os
import socket
import multiprocessing
from queue import Queue

from common.logger import Logger
from common.social import MainServerMessages as SM
from common.network import NetworkManager

from puzzle.server_classic import ClassicServer
from puzzle.server_competitive import CompetitiveServer

logger = Logger.get("ServerFactory", True)

class ServerFactory:
    """Factory class for creating different types of game servers"""
    
    def __init__(self, host, puzzle_queue:Queue, message_queue:Queue, debug=False):
        """Initialize the server factory"""
        self.host = host 
        self.puzzle_queue = puzzle_queue
        self.message_queue = message_queue
        self.next_port = 5001
        self.debug = debug
        
        logger.info(f"Server factory initialized on host: {host}")
    
    def create_server(self, name, mode, max_players):
        """Create a new server of the specified type"""
        try:
            # Determine if host is IPv4 or IPv6
            host_is_ipv6 = ':' in self.host

            # Create server instance based on mode
            server_class = self.get_server_class(mode)
            if not server_class:
                logger.error(f"Invalid server mode: {mode}")
                return None
            
            # Set up port
            port = self._find_available_port()
            
            # Create the server in a new process - pasar el host
            process = multiprocessing.Process(
                target=self._start_game_server,
                args=(name, mode, max_players, self.host, port, self.puzzle_queue, self.message_queue, self.debug)
            )
            process.daemon = True
            process.start()
            
            logger.info(f"Created {mode} server '{name}' with PID {process.pid} on {self.host}:{port}")
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
        
        # Determinar si el host es IPv4 o IPv6
        host_is_ipv6 = ':' in self.host
        bind_addr = '::' if host_is_ipv6 else '0.0.0.0'
        
        for _ in range(max_attempts):
            try:
                if host_is_ipv6:
                    with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
                        s.bind((bind_addr, port))
                        return port
                else:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.bind((bind_addr, port))
                        return port
            except OSError:
                port += 1
                
        raise RuntimeError("Could not find an available port after multiple attempts")

    @staticmethod
    def _start_game_server(name, mode, max_players, host, port, puzzle_queue, message_queue, debug=False):
        """Function that runs in the new process to start a game server"""
        try:
            # Crear el tipo correcto de servidor
            if mode == "classic":
                server = ClassicServer(name, port, puzzle_queue, message_queue, max_players, debug=debug)
            elif mode == "competitive":
                server = CompetitiveServer(name, port, puzzle_queue, message_queue, max_players, debug=debug)
            else:
                raise ValueError(f"Invalid game mode: {mode}")
            
            # Verificar si la dirección es IPv4 o IPv6
            host_is_ipv6 = ':' in host and not host.startswith('::ffff:')
            
            # Si es IPv4, usar un socket IPv4 forzosamente
            if not host_is_ipv6 and NetworkManager.is_ipv6_available():
                logger.info(f"Host '{host}' es IPv4, usando socket IPv4 aunque IPv6 esté disponible")
                use_ipv6 = False
            else:
                use_ipv6 = NetworkManager.is_ipv6_available()
            
            # Iniciar el servidor con la configuración adecuada
            import asyncio
            asyncio.run(server.start(host))
            
        except Exception as e:
            # Log and notify main server of error with proper format
            logger.error(f"Error in game server: {e}")
            message_queue.put(f"{SM.ERROR}|{os.getpid()}|{str(e)}")

