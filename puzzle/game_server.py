import time
import socket
import threading
import logging
from queue import Queue
from abc import ABC, abstractmethod

from puzzle.logic import KryptoLogic
from common.social import PlayerServerMessages as PM
from common.social import MainServerMessages as SM
from common.communication import Communication

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class GameServer(ABC):
    """Abstract base class for all game server types"""
    
    def __init__(self, name, puzzle_queue, message_queue, port=5001, max_players=8):
        self.name = name
        self.port = port
        self.max_players = max_players
        self.puzzle_queue = puzzle_queue
        self.message_queue = message_queue
        
        # Server state
        self.players = 0
        self.solved = 0
        self.abandoned = 0
        self.puzzle = None
        self.client_sockets = []
        
        # Communication
        self.logger = logging.getLogger(f"{self.__class__.__name__}:{name}")
        self.communication = Communication(self.logger)
        
        # Register commands
        self.communication.register_command(PM.SUBMIT_ANSWER, self.handle_possible_solution)
        self.communication.register_command(PM.PLAYER_EXIT, self.handle_player_disconnect)
        
        # Server socket
        self.server_socket = None
        self.running = False
    
    def initialize(self):
        """Initialize the server and prepare it to accept connections"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('localhost', self.port))
            self.server_socket.listen(self.max_players)
            self.logger.info(f"Server {self.name} initialized on port {self.port}")
            
            # Get initial puzzle(s) - implementation varies by server type
            self.get_initial_puzzles()
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize server: {e}")
            self.message_queue.put(f"{SM.ERROR}|{self.name}|{str(e)}")
            return False
    
    @abstractmethod
    def get_initial_puzzles(self):
        """Get initial puzzles - to be implemented by subclasses"""
        pass
    
    def start(self):
        """Start the server and accept client connections"""
        if not self.initialize():
            return False
        
        self.running = True
        self.logger.info(f"Server {self.name} started and accepting connections")
        
        try:
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    self.handle_new_connection(client_socket, client_address)
                except socket.timeout:
                    continue
                except Exception as e:
                    self.logger.error(f"Error accepting connection: {e}")
        finally:
            self.cleanup()
    
    def handle_new_connection(self, client_socket, client_address):
        """Handle a new client connection"""
        if self.players >= self.max_players:
            self.logger.info(f"Connection from {client_address} rejected - server full")
            self.communication.send_message(client_socket, PM.SERVER_FULL)
            self.communication.close_connection(client_socket)
            return
            
        self.logger.info(f"Connection accepted from {client_address}")
        self.communication.send_message(client_socket, PM.GREETING)
        self.players += 1
        
        # Send current puzzle and game state
        self.communication.send_message(client_socket, f"{PM.NEW_PUZZLE}|{self.puzzle}")
        self.broadcast_game_state()
        
        # Start thread to handle client messages
        thread = threading.Thread(
            target=self.handle_client_messages,
            args=(client_socket, client_address),
            daemon=True
        )
        thread.start()
    
    def handle_client_messages(self, client_socket, client_address):
        """Handle messages from a client"""
        self.client_sockets.append(client_socket)
        
        try:
            while self.running:
                success, command, args = self.communication.receive_message(client_socket)
                if not success:
                    break
                
                if command in self.communication.commands:
                    self.communication.execute_command(command, client_socket, *args)
                else:
                    self.logger.warning(f"Unknown command from {client_address}: {command}")
        except Exception as e:
            self.logger.error(f"Error handling client {client_address}: {e}")
        finally:
            self.cleanup_client(client_socket)
    
    def cleanup_client(self, client_socket):
        """Clean up when a client disconnects"""
        try:
            if client_socket in self.client_sockets:
                self.client_sockets.remove(client_socket)
            self.communication.close_connection(client_socket)
        except Exception as e:
            self.logger.error(f"Error cleaning up client: {e}")
            
        self.players -= 1
        if self.players == 0:
            self.logger.info("No players left, notifying main server")
            self.message_queue.put(f"{SM.EMPTY}|{self.name}")
            
        self.broadcast_game_state()
    
    def cleanup(self):
        """Clean up server resources"""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                self.logger.error(f"Error closing server socket: {e}")
                
        # Close all client sockets
        for client_socket in self.client_sockets[:]:
            self.communication.close_connection(client_socket)
        self.client_sockets.clear()
        
        self.logger.info(f"Server {self.name} shut down")
    
    def broadcast(self, message):
        """Send a message to all connected clients"""
        self.logger.debug(f"Broadcasting: {message}")
        for client in self.client_sockets[:]:
            try:
                self.communication.send_message(client, message)
            except Exception as e:
                self.logger.error(f"Error broadcasting to client: {e}")
                # Will be removed in cleanup_client
    
    def broadcast_game_state(self):
        """Broadcast the current game state to all clients"""
        state_msg = f"{PM.GAME_STATE}|{self.solved}|{self.abandoned}|{self.players}"
        self.broadcast(state_msg)
    
    def handle_possible_solution(self, client_socket, solution):
        """Handle a solution attempt from a client"""
        self.logger.info(f"Solution attempt: {solution}")
        
        try:
            # Get the target value from the puzzle
            puzzle_parts = self.puzzle.split(',')
            target = int(puzzle_parts[-1])
            
            # Verify solution
            if KryptoLogic.verify_solution(solution, target):
                self.solved += 1
                self.communication.send_message(client_socket, f"{PM.PUZZLE_RESULT}|Correcto")
                self.logger.info(f"Correct solution: {solution}")
                
                # Check if this round is completed
                self.check_after_solution(client_socket)
            else:
                self.communication.send_message(client_socket, f"{PM.PUZZLE_RESULT}|Incorrecto")
                self.logger.info(f"Incorrect solution: {solution}")
                
            self.broadcast_game_state()
        except Exception as e:
            self.logger.error(f"Error processing solution: {e}")
            self.communication.send_message(client_socket, f"{PM.PUZZLE_RESULT}|Error: {str(e)}")
    
    def handle_player_disconnect(self, client_socket):
        """Handle a player disconnecting"""
        self.logger.info("Player disconnected")
        self.cleanup_client(client_socket)
    
    @abstractmethod
    def check_after_solution(self, client_socket):
        """Check what to do after a solution is submitted - to be implemented by subclasses"""
        pass
