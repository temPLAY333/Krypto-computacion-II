import time
import socket
import threading
from client.player_interface import PlayerInterface
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
            PSM.GREETING: self.handle_welcome,
            SCM.PUZZLE: self.handle_puzzle,
            SCM.NEW_PUZZLE: self.handle_new_puzzle,
            SCM.SOLUTION_CORRECT: self.handle_solution_correct,
            SCM.SOLUTION_INCORRECT: self.handle_solution_incorrect,
            SCM.SURRENDER_STATUS: self.handle_surrender_status,
            SCM.SCORE_UPDATE: self.handle_score_update,
            SCM.GAME_STATUS: self.handle_game_status, 
            SCM.ERROR: self.handle_error,
        }
        self.communication.define_all_commands(handlers)
        
    def set_interface(self, interface: PlayerInterface):
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
            
            return True
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False
    
    def start_listener(self):
        """Start thread to listen for server messages"""
        thread = threading.Thread(target=self.listen_for_messages, daemon=True)
        thread.start()
        
    def listen_for_messages(self):
        """Listen for messages from server"""
        self.logger.info("Starting message listener thread")
        
        while self.connected:
            try:
                success, message = self.communication.receive_message(self.socket)
                if not success:
                    self.logger.error("Connection lost")
                    self.connected = False
                    break
                    
                if message:
                    self.logger.debug(f"Raw message received: '{message}'")
                    
                    # Process message
                    self.communication.handle_sync_command(message)
                    
                    # Process any additional complete messages in buffer
                    while self.connected and self.communication.has_complete_message():
                        success, next_message = self.communication.get_next_message()
                        if success:
                            self.logger.debug(f"Processing additional message from buffer: '{next_message}'")
                            self.communication.handle_sync_command(next_message)
                    
                    # Force immediate UI refresh after processing all messages
                    if self.interface and hasattr(self.interface, 'request_refresh'):
                        self.interface.request_refresh()
                            
            except Exception as e:
                self.logger.error(f"Error in listener: {e}")
                if self.debug:
                    import traceback
                    self.logger.error(traceback.format_exc())
                self.connected = False
                break
    
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
                # Primero marcar como desconectado para detener el listener thread
                self.connected = False
                
                # Enviar mensaje de salida de forma ordenada
                try:
                    message = f"{PSM.PLAYER_EXIT}|{self.username}"
                    self.communication.send_message(self.socket, message)
                    
                    # Esperar brevemente para que el mensaje se envíe completamente
                    time.sleep(0.5)
                except Exception as e:
                    self.logger.warning(f"Error al enviar mensaje de salida: {e}")
            
            # Cerrar socket después de enviar mensajes
            if hasattr(self, 'socket') and self.socket:
                try:
                    self.socket.shutdown(socket.SHUT_RDWR)  # Cerrar ordenadamente
                except:
                    pass  # El socket ya podría estar cerrado
                
                try:
                    self.socket.close()
                except:
                    pass
                
                self.socket = None
                
            self.logger.info("Desconectado del servidor")
        except Exception as e:
            self.logger.error(f"Error durante la desconexión: {e}")
    
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

    def handle_welcome(self, server_name, *args):
        """Handle welcome message from server
        
        Args:
            server_name (str): Name of the server
        """
        try:
            if self.interface:
                self.interface.add_message(f"Connected to server: {server_name}")
            self.logger.info(f"Received welcome from server: {server_name}")
        except Exception as e:
            self.logger.error(f"Error processing welcome message: {e}")

    def handle_puzzle(self, puzzle, *args):
        """Handle puzzle message from server"""
        self.logger.debug(f"BEFORE: current_puzzle = {self.current_puzzle}")
        self.current_puzzle = puzzle
        if self.interface:
            self.interface.show_puzzle(puzzle, *args)
        self.logger.info(f"Received puzzle: {puzzle}")
        self.logger.debug(f"AFTER: current_puzzle = {self.current_puzzle}")

    def handle_new_puzzle(self, puzzle, *args):
        """Handle new puzzle message"""
        self.logger.debug(f"BEFORE: current_puzzle = {self.current_puzzle}")
        self.current_puzzle = puzzle
        if self.interface:
            self.interface.show_new_puzzle(puzzle)
            self.interface.show_game_stats(
                total_players=self.interface.stats.get("total_players", 0), 
                correct_answers=0,  # Reset to zero
                surrendered=0       # Reset to zero
            )
        self.logger.info(f"Received new puzzle: {puzzle}")
        self.logger.debug(f"AFTER: current_puzzle = {self.current_puzzle}")
    
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
    
        # In Player class - add/update handler
    def handle_surrender_status(self, status="", *args):
        """Handle surrender status message
        
        Args:
            status (str): Additional status info like disable_input
        """
        try:
            if self.interface:
                self.interface.show_message("You surrendered this puzzle")
                if status == "disable_input":
                    self.interface.disable_input_until_new_puzzle()
        except Exception as e:
            self.logger.error(f"Error processing surrender status: {e}")
    
    def handle_score_update(self, player_name, score, *args):
        """Handle score update message"""
        if self.interface:
            self.interface.show_score_update(player_name, score, *args)

    def handle_game_status(self, total_players, correct_answers, surrendered, *args):
        """Handle game status update message
        
        Args:
            total_players (int): Total number of players in the server
            correct_answers (int): Number of players with correct answers
            surrendered (int): Number of players who surrendered
        """
        try:
            if self.interface:
                # Strip any non-numeric parts from values
                total_players_str = ''.join(c for c in str(total_players) if c.isdigit())
                correct_answers_str = ''.join(c for c in str(correct_answers) if c.isdigit())
                surrendered_str = ''.join(c for c in str(surrendered) if c.isdigit())
                
                # Log raw and cleaned values for debugging
                self.logger.debug(f"Raw game status: {total_players},{correct_answers},{surrendered}")
                self.logger.debug(f"Cleaned game status: {total_players_str},{correct_answers_str},{surrendered_str}")
                
                # Use default values if we can't parse
                try:
                    total_players_int = int(total_players_str) if total_players_str else 0
                    correct_answers_int = int(correct_answers_str) if correct_answers_str else 0
                    surrendered_int = int(surrendered_str) if surrendered_str else 0
                except ValueError:
                    self.logger.error(f"Failed to parse game stats values")
                    return
                    
                self.interface.show_game_stats(total_players_int, correct_answers_int, surrendered_int)
        except Exception as e:
            self.logger.error(f"Error processing game status: {e}")
    
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