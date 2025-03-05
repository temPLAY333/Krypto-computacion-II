class LogMessages:
    """Logging-related messages"""
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"
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

class UserMainMessages:
    """Messages between the user and main server"""
    TEST = "test"
    LOGIN = "login"
    LIST_SERVERS = "list"
    CHOOSE_SERVER = "join"
    CREATE_SERVER = "create"
    OK = "success"
    
    # Add all missing message types that are used in user.py
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAIL = "login_fail"
    SERVER_LIST = "server_list"
    JOIN_SUCCESS = "join_success"
    JOIN_FAIL = "join_fail"
    CREATE_SUCCESS = "create_success"
    CREATE_FAIL = "create_fail"
    ERROR = "error"
    LIST = "list"
    CREATE = "create" 
    LOGOUT = "logout"

class InterfaceMessages:
    """Messages shown in the user interface"""
    GREETING = "Welcome to Krypto Game!"
    ASK_USERNAME = "Please enter your username (8-20 alphanumeric characters): "
    INVALID_USERNAME = "Invalid username format! Please use 8-20 alphanumeric characters."
    LOGIN_SUCCESS = "Login successful!"
    LOGIN_ERROR = "Login failed. Please try again."
    MAIN_MENU = (
        "Main Menu:\n"
        "1. View servers\n"
        "2. Join a server\n"
        "3. Create a server\n"
        "Type 'exit' to quit.\n"
        "Enter your choice: "
    )
    INVALID_OPTION = "Invalid option. Please try again.\n"
    NO_SERVERS = "No active servers available."
    ASK_SERVER_ID = "Enter the server ID to join: "
    SERVER_JOIN_SUCCESS = "Successfully joined the server!"
    SERVER_JOIN_FAIL = "Failed to join server. Please check the server ID and try again."
    CREATE_SERVER_NAME = "Enter server name: "
    CREATE_SERVER_MODE = "Enter server mode (classic or competitive): "
    CREATE_SERVER_ERROR = "Invalid server mode. Please use 'classic' or 'competitive'."
    CREATE_SERVER_SUCCESS = "Server created successfully with ID: "
    GOODBYE = "Goodbye! Thanks for playing.\n"
    SERVER_FULL = "Server is full. Please try another server."
    PUZZLE_RESULT = "Your solution was: "  # Correct or incorrect

class PlayerServerMessages:
    """Messages between player and game server"""
    GREETING = "welcome"
    SERVER_FULL = "server_full"
    NEW_PUZZLE = "puzzle"
    PUZZLE_RESULT = "result"
    GAME_STATE = "state"

    # Player Messages
    SUBMIT_ANSWER = "solution"
    PLAYER_SURRENDER = "quit"
    PLAYER_EXIT = "exit"

    # Server Competitive Messages
    GAME_START = "start"
    GAME_COMPLETED = "complete"
    GAME_RESULTS = "results"

class MainServerMessages:
    """Messages between game server and main server"""
    OK = "ok"
    ERROR = "error"
    KILL_SERVER = "kill"

class ServerClientMessages:
    """Messages between game servers and clients"""
    GET_PUZZLE = "get_puzzle"
    PUZZLE = "puzzle"
    SUBMIT_SOLUTION = "submit_solution"
    SOLUTION_CORRECT = "solution_correct"
    SOLUTION_INCORRECT = "solution_incorrect"
    SURRENDER_STATUS = "surrender_status"
    NEW_PUZZLE = "new_puzzle"
    SCORE_UPDATE = "score_update"
    GAME_STATUS = "GAME_STATUS"
    ERROR = "error"