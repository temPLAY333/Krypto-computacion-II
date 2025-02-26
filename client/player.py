import time
import threading
import logging
from abc import ABC, abstractmethod

from common.communication import Communication
from common.social import PlayerServerMessages as SM

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class Player:
    """Base Player class that handles communication with the server"""
    
    def __init__(self, username, socket):
        self.username = username
        self.socket = socket
        self.puzzle = None
        self.game_state = {
            "solved": 0,
            "abandoned": 0,
            "players": 0
        }
        self.interface = None
        
        # Set up communication and logging
        self.logger = logging.getLogger(f"Player:{username}")
        self.communication = Communication(self.logger)
        
        # Register message handlers
        self.communication.register_command(SM.NEW_PUZZLE, self.handle_new_puzzle)
        self.communication.register_command(SM.PUZZLE_RESULT, self.handle_puzzle_result)
        self.communication.register_command(SM.GAME_STATE, self.handle_game_state)
        self.communication.register_command(SM.GREETING, self.handle_greeting)
        self.communication.register_command(SM.SERVER_FULL, self.handle_server_full)
        
        # Thread for listening to server messages
        self.receiver_thread = None
        self.running = False
    
    def set_interface(self, interface):
        """Assign a UI interface to this player"""
        self.interface = interface
        interface.set_player(self)
    
    def start(self):
        """Start the player's message receiving thread"""
        if self.receiver_thread is None:
            self.running = True
            self.receiver_thread = threading.Thread(
                target=self.handle_server_messages,
                daemon=True
            )
            self.receiver_thread.start()
            self.logger.info(f"Player {self.username} started")
    
    def stop(self):
        """Stop the player's message receiving thread"""
        self.running = False
        if self.socket:
            try:
                self.send_message(SM.PLAYER_EXIT)
                self.socket.close()
            except Exception as e:
                self.logger.error(f"Error during player shutdown: {e}")
        self.logger.info(f"Player {self.username} stopped")
    
    def handle_server_messages(self):
        """Thread for listening to and handling server messages"""
        while self.running:
            try:
                data = self.socket.recv(1024).decode()
                if not data:
                    self.logger.warning("Empty data received from server. Connection may be closed.")
                    break
                
                self.logger.debug(f"Received message: {data}")
                command, *args = data.split("|")
                
                if command in self.communication.commands:
                    self.communication.execute_command(command, *args)
                else:
                    self.logger.warning(f"Unknown command from server: {command}")
                    if self.interface:
                        self.interface.display_message(f"Unknown command from server: {command}")
            except Exception as e:
                self.logger.error(f"Error receiving data from server: {e}")
                if self.interface:
                    self.interface.display_message(f"Connection error: {e}")
                break
        
        self.logger.info("Server message handling thread stopped")
        if self.interface:
            self.interface.handle_disconnect()
    
    def send_message(self, command, *args):
        """Send a message to the server"""
        try:
            message = command
            if args:
                message += "|" + "|".join(str(arg) for arg in args)
            
            self.logger.debug(f"Sending message: {message}")
            self.socket.sendall(message.encode())
            return True
        except Exception as e:
            self.logger.error(f"Error sending message to server: {e}")
            return False
    
    def submit_solution(self, solution):
        """Submit a solution to the current puzzle"""
        return self.send_message(SM.SUBMIT_ANSWER, solution)
    
    def surrender(self):
        """Surrender the current puzzle (classic mode only)"""
        return self.send_message(SM.PLAYER_SURRENDER)
    
    def exit_game(self):
        """Exit the game and close the connection"""
        if self.send_message(SM.PLAYER_EXIT):
            self.stop()
    
    # Message handlers
    def handle_new_puzzle(self, puzzle):
        """Handle a new puzzle from the server"""
        self.puzzle = puzzle
        self.logger.info(f"New puzzle received: {puzzle}")
        if self.interface:
            self.interface.update_puzzle(puzzle)
    
    def handle_puzzle_result(self, result):
        """Handle the result of a puzzle attempt"""
        self.logger.info(f"Puzzle result: {result}")
        if self.interface:
            self.interface.display_result(result)
    
    def handle_game_state(self, solved, abandoned, players):
        """Handle updated game state"""
        self.game_state = {
            "solved": int(solved),
            "abandoned": int(abandoned),
            "players": int(players)
        }
        self.logger.debug(f"Updated game state: {self.game_state}")
        if self.interface:
            self.interface.update_game_state(self.game_state)
    
    def handle_greeting(self, *args):
        """Handle server greeting"""
        self.logger.info("Connected to server")
        if self.interface:
            self.interface.display_message("Connected to server successfully")
    
    def handle_server_full(self, *args):
        """Handle server full message"""
        self.logger.warning("Server is full, cannot join")
        if self.interface:
            self.interface.display_message("Server is full, cannot join")
            self.interface.handle_disconnect()