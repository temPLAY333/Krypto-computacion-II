class UserMainMessages:
    TEST = "TEST_MESSAGE"
    LOGIN = "LOGIN"
    LIST_SERVERS = "LIST_SERVERS"
    CHOOSE_SERVER = "CHOOSE_SERVER"
    OK = "Server choosen successfully"
    CREATE_SERVER = "CREATE_SERVER"
    # Agrega más mensajes de comando según sea necesario

class MainServerMessages:
    OK = "The game server has been served with an old puzzle"
    KILL = "The game server has no more players"
    ERROR = "The game server has an unidentified error"

class PlayerServerMessages:
    # PLayer Messages
    SEND_PUZZLE = "send_puzzle"
    NEW_PUZZLE = "new_puzzle"
    SUBMIT_ANSWER = "submit_answer"
    PLAYER_SURRENDER = "player_surrender"
    PLAYER_EXIT = "player_exit"

    # Server Messages
    GAME_STATE = "game_state"

class LogMessages:
    SERVER_STARTED = "Servidor principal definido."
    SERVER_RUNNING = "Servidor principal ejecutándose..."
    SERVER_CLOSED = "Servidor principal cerrado."
    NEW_CONNECTION = "Nueva conexión recibida"
    PLAYER_CONNECTED = "Jugador conectado: {username} (ID: {player_id})"
    SENDING_SERVER_LIST = "Enviando lista de servidores..."
    NEW_PUZZLE_RECEIVED = "Nuevo puzzle recibido: {puzzle}"
    SERVER_TERMINATED = "Servidor con ID {pid} terminado."
    SERVER_ERROR = "Error en el servidor con ID {pid}."
    UNKNOWN_MESSAGE = "Error en el mensaje del proceso {pid}"

class InterfaceMessages:
    GREETING = "Welcome to the Krypto Game!\n"
    ASK_USERNAME = (
        "Username must have between 8 and 20 characters. No special characters allowed. "
        "Enter your username: "
    )
    INVALID_USERNAME = "That username is not allowed."
    LOGIN_SUCCESS = "Login successful!\n"
    LOGIN_ERROR = "Login failed. Try again.\n"
    MAIN_MENU = (
        "Main Menu:\n"
        "1. View servers\n"
        "2. Join a server\n"
        "3. Create a server\n"
        "Type 'exit' to quit.\n"
        "Enter your choice: "
    )
    INVALID_OPTION = "Invalid option. Please try again.\n"
    NO_SERVERS = "No servers are available.\n"
    ASK_SERVER_ID = "Enter the server ID to join: "
    SERVER_JOIN_SUCCESS = "You joined the server successfully!\n"
    SERVER_JOIN_FAIL = "Failed to join the server.\n"
    CREATE_SERVER_NAME = "Enter a name for your server: "
    CREATE_SERVER_MODE = "Enter the game mode (classic or competitive): "
    CREATE_SERVER_ERROR = "Invalid game mode. Try again.\n"
    CREATE_SERVER_SUCCESS = "Server created successfully with ID: "
    GOODBYE = "Goodbye! Thanks for playing.\n"
    SERVER_FULL = "Server is full. Try again later.\n"
    PUZZLE_RESULT = "Your solution was: "  # Correct or incorrect