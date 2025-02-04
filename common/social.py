# common/social.py

class Messages:
    # Login Messages
    GREETING = "Welcome to the Krypto Game!\n"
    ASK_USERNAME = (
        "Username must have beetwen 8 and 20 caracters. Not special caracterts allowed."
        "Enter your username: "
    )
    INVALID_USERNAME = "That username is not allowed."
    LOGIN_SUCCESS = "Login successful!\n"
    LOGIN_ERROR = "Login failed. Try again.\n"

     # Main Server Messages
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
    CREATE_SERVER_ERROR = "Invalid game mode. Try again. \n"
    CREATE_SERVER_SUCCESS = "Server created successfully with ID: "
    
    GOODBYE = "Goodbye! Thanks for playing.\n"

    # Game-specific messages
    SERVER_FULL = "Server is full. Try again later.\n"

    SEND_PUZZLE = "send_puzzle"
    NEW_PUZZLE = "new_puzzle"

    SUBMIT_ANSWER = "submit_answer"
    PUZZLE_RESULT = "Your soluticion was: "  # Correct or incorrect

    PLAYER_SURRENDER = "player_render"
    PLAYER_EXIT = "player_exit"

    GAME_STATE = "game_state"
    
