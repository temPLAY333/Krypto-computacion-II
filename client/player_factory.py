import socket
import logging
from client.player import Player
from client.classic_interface import ClassicPlayerInterface
from client.competitive_interface import CompetitivePlayerInterface

def create_player(username, server_address, server_port, game_type="classic"):
    """
    Create and return a Player object with the appropriate interface
    
    Args:
        username (str): Player's username
        server_address (str): Server's address
        server_port (int): Server's port
        game_type (str): Type of game ('classic' or 'competitive')
        
    Returns:
        tuple: (Player, PlayerInterface) or (None, None) if connection fails
    """
    logger = logging.getLogger("PlayerFactory")
    
    try:
        # Connect to server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((server_address, server_port))
        logger.info(f"Connected to server at {server_address}:{server_port}")
        
        # Create player
        player = Player(username, sock)
        
        # Create appropriate interface
        if game_type.lower() == "competitive":
            interface = CompetitivePlayerInterface()
            
            # Register competitive-specific handlers
            from common.social import PlayerServerMessages as SM
            player.communication.register_command(SM.GAME_START, interface.handle_game_start)
            player.communication.register_command(SM.GAME_COMPLETED, interface.handle_game_completed)
            player.communication.register_command(SM.GAME_RESULTS, interface.handle_game_results)
        else:
            interface = ClassicPlayerInterface()
        
        # Link player and interface
        player.set_interface(interface)
        
        return player, interface
    except Exception as e:
        logger.error(f"Failed to create player: {e}")
        return None, None
