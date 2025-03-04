import abc
from common.logger import Logger

class PlayerInterface(abc.ABC):
    """Abstract base class for player interfaces"""
    
    def __init__(self, debug=False):
        """Initialize interface
        
        Args:
            debug (bool): Enable debug logging
        """
        self.player = None
        self.debug = debug
        self.logger = Logger.get(self.__class__.__name__, debug)
        
    def set_player(self, player):
        """Link this interface to a player
        
        Args:
            player: Player instance to use
        """
        self.player = player
        self.logger.debug(f"Interface linked to player {player.username}")
    
    @abc.abstractmethod
    def show_new_puzzle(self, puzzle, *args):
        """Show a new puzzle to the user"""
        pass

    @abc.abstractmethod
    def run(self):
        """Start the interface"""
        pass
        
    @abc.abstractmethod
    def show_solution_result(self, is_correct, *args):
        """Display the result of a solution submission"""
        pass
        
    @abc.abstractmethod
    def show_message(self, message):
        """Display a message to the user"""
        pass
        
    @abc.abstractmethod
    def show_score_update(self, player_name, score, *args):
        """Display a score update"""
        pass
        
    @abc.abstractmethod
    def get_user_input(self):
        """Get input from the user"""
        pass
