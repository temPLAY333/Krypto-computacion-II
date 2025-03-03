import socket
import threading
from common.social import PlayerServerMessages as PSM
from common.social import ServerClientMessages as SCM
from common.communication import Communication
from common.logger import Logger

class Player:
    """Handles game communication with GameServer"""
    
    def __init__(self, username, server_host, server_port, debug=False):
        """Initialize Player instance
        
        Args:
            username (str): Player's username
            server_host (str): Game server host
            server_port (int): Game server port
            debug (bool): Enable debug logging
        """
        self.username = username
        self.server_host = server_host
        self.server_port = server_port
        self.debug = debug
        self.socket = None
        self.connected = False
        self.current_puzzle = None
        self.interface = None
        
        # Set up logging
        self.logger = Logger.get(f"Player-{username}", debug)
        
        # Set up communication
        self.communication = Communication(self.logger)
        
        # Register handlers
        self.register_message_handlers()
        
    def register_message_handlers(self):
        """Register handlers for GameServer messages"""
        handlers = {
            SCM.PUZZLE: self.handle_puzzle,
            SCM.NEW_PUZZLE: self.handle_new_puzzle,
            SCM.SOLUTION_CORRECT: self.handle_solution_correct,
            SCM.SOLUTION_INCORRECT: self.handle_solution_incorrect,
            SCM.SCORE_UPDATE: self.handle_score_update,
            SCM.ERROR: self.handle_error,
        }
        self.communication.define_all_commands(handlers)
        
    def set_interface(self, interface):
        """Set the interface for player interaction
        
        Args:
            interface: Interface to use
        """
        self.interface = interface
        self.logger.debug(f"Interface set for player {self.username}")
        
    def connect(self):
        """Connect to GameServer
        
        Returns:
            bool: True if connection successful
        """
        if not self.interface:
            self.logger.error("Cannot connect: No interface set")
            return False
            
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            self.connected = True
            self.logger.info(f"Connected to GameServer at {self.server_host}:{self.server_port}")
            
            # Start listener
            self.start_listener()
            
            # Request puzzle
            self.request_puzzle()
            return True
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False
    
    def start_listener(self):
        """Start thread to listen for server messages"""
        thread = threading.Thread(target=self.listen_for_messages, daemon=True)
        thread.start()
        
    def listen_for_messages(self):
        """Listen and process messages from GameServer"""
        while self.connected:
            try:
                success, data = self.communication.receive_message(self.socket)
                if not success or not data:
                    self.logger.warning("Connection closed by server")
                    self.connected = False
                    break
                    
                if self.debug:
                    self.logger.debug(f"Received: {data}")
                
                self.communication.handle_sync_command(data)
                
            except Exception as e:
                self.logger.error(f"Error in listener: {e}")
                self.connected = False
                break
                
        # Notify interface
        if self.interface:
            self.interface.show_message("Connection to server lost")
    
    def request_puzzle(self):
        """Request a puzzle from server"""
        if not self.connected:
            return
            
        try:
            self.communication.send_message(self.socket, SCM.GET_PUZZLE)
        except Exception as e:
            self.logger.error(f"Failed to request puzzle: {e}")
    
    def submit_solution(self, solution:str):
        """Submit a solution to server
        
        Args:
            solution (str): Solution to submit
            
        Returns:
            bool: True if submission succeeded
        """
        if not self.connected:
            self.logger.warning("Not connected to server")
            return False
            
        try:
            message = f"{SCM.SUBMIT_SOLUTION}|{solution}|{self.username}"
            self.communication.send_message(self.socket, message)
            return True
        except Exception as e:
            self.logger.error(f"Failed to submit solution: {e}")
            return False
    
    def surrender(self):
        """Surrender the current puzzle"""
        if not self.connected:
            return
            
        try:
            message = f"{PSM.PLAYER_SURRENDER}|{self.username}"
            self.communication.send_message(self.socket, message)
        except Exception as e:
            self.logger.error(f"Failed to surrender: {e}")
    
    def exit_game(self):
        """Exit the game"""
        try:
            if self.connected:
                message = f"{PSM.PLAYER_EXIT}|{self.username}"
                self.communication.send_message(self.socket, message)
                
            if self.socket:
                self.socket.close()
                self.socket = None
                
            self.connected = False
            self.logger.info("Disconnected from server")
        except Exception as e:
            self.logger.error(f"Error during exit: {e}")
    
    def play(self):
        """Start the game
        
        Returns:
            bool: True if game started successfully
        """
        if not self.interface:
            self.logger.error("Cannot play: No interface set")
            return False
            
        if not self.connected and not self.connect():
            return False
            
        self.interface.run()
        return True
        
    # Message handlers
    def handle_puzzle(self, puzzle, *args):
        """Handle puzzle message from server"""
        self.current_puzzle = puzzle
        if self.interface:
            self.interface.show_puzzle(puzzle, *args)
        self.logger.info(f"Received puzzle: {puzzle}")
    
    def handle_new_puzzle(self, puzzle, *args):
        """Handle new puzzle message"""
        self.current_puzzle = puzzle
        if self.interface:
            self.interface.show_new_puzzle(puzzle, *args)
        self.logger.info(f"Received new puzzle: {puzzle}")
    
    def handle_solution_correct(self, *args):
        """Handle correct solution message"""
        if self.interface:
            self.interface.show_solution_result(True, *args)
        self.logger.info("Solution correct")
    
    def handle_solution_incorrect(self, *args):
        """Handle incorrect solution message"""
        if self.interface:
            self.interface.show_solution_result(False, *args)
        self.logger.info("Solution incorrect")
    
    def handle_score_update(self, player_name, score, *args):
        """Handle score update message"""
        if self.interface:
            self.interface.show_score_update(player_name, score, *args)
    
    def handle_error(self, error_msg, *args):
        """Handle error message from server"""
        if self.interface:
            self.interface.show_message(f"Server error: {error_msg}")
        self.logger.error(f"Server error: {error_msg}")

if __name__ == "__main__":
    username = input("Enter your username: ")
    server_host = input("Enter server host: ")
    server_port = int(input("Enter server port: "))
    player = Player(username, server_host, server_port)
    player.play()