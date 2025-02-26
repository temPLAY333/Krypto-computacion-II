import curses
import logging
import threading
import signal
from abc import ABC, abstractmethod

class PlayerInterface(ABC):
    """Abstract base class for player interfaces"""
    
    def __init__(self):
        self.player = None
        self.messages = []
        self.max_messages = 100  # Maximum number of messages to keep in history
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self.running = False
    
    def set_player(self, player):
        """Set the player this interface belongs to"""
        self.player = player
    
    def start(self):
        """Start the interface"""
        if self.player is None:
            raise ValueError("Player must be set before starting interface")
        
        self.running = True
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_interrupt)
        signal.signal(signal.SIGTERM, self.handle_interrupt)
        
        # Start the player's message receiver
        self.player.start()
        
        # Start the curses UI
        try:
            curses.wrapper(self.run_interface)
        except Exception as e:
            self.logger.error(f"Error in interface: {e}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        if self.player:
            self.player.stop()
        self.running = False
        self.logger.info("Interface shut down")
    
    def handle_interrupt(self, signum, frame):
        """Handle interrupt signals"""
        self.logger.info(f"Received signal {signum}, shutting down")
        self.running = False
        if self.player:
            self.player.stop()
    
    def display_message(self, message):
        """Add a message to the display queue"""
        self.messages.append(message)
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
    
    def handle_disconnect(self):
        """Handle disconnection from server"""
        self.display_message("Disconnected from server")
        self.running = False
    
    @abstractmethod
    def run_interface(self, stdscr):
        """Run the main interface loop - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def update_puzzle(self, puzzle):
        """Update the interface with a new puzzle - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def display_result(self, result):
        """Display a puzzle result - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    def update_game_state(self, state):
        """Update the game state display - must be implemented by subclasses"""
        pass
