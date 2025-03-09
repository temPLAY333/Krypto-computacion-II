import logging
from client.player import Player
from client.classic_interface import ClassicInterface
from client.competitive_interface import CompetitiveInterface
from common.logger import Logger

def create_player(username, server_address, server_port, game_type="classic", debug=False):
    """
    Create and return a Player object with the appropriate interface
    
    Args:
        username (str): Player's username
        server_address (str): Server's address
        server_port (int): Server's port
        game_type (str): Type of game ('classic' or 'competitive')
        debug (bool): Enable debug logging
        
    Returns:
        Player: Configured player object with appropriate interface
    """
    logger = Logger.get("PlayerFactory", debug)

    if not username:
        logging.error("No se puede crear el jugador: nombre de usuario no proporcionado")
        return None
    
    try:
        # Create appropriate interface
        if game_type.lower() == "competitive":
            interface = CompetitiveInterface(debug=debug)
        else:
            interface = ClassicInterface(debug=debug)
        
        # Create player without connecting
        player = Player(username, server_address, server_port, debug=debug)
        
        # Link player and interface
        player.set_interface(interface)
        interface.set_player(player)
        
        logger.info(f"Created {game_type} player for {username} connecting to {server_address}:{server_port}")
        return player
    
    except Exception as e:
        logger.error(f"Failed to create player: {e}")
        return None
