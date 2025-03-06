import curses
import logging
import re
import time
import threading
import signal
import sys
from common.social import InterfaceMessages as IM

class UserInterface:
    """Enhanced user interface using curses"""
    
    def __init__(self, user):
        """Initialize the user interface"""
        self.user = user
        self.stdscr = None
        self.active = False
        self.paused = False
        
        # Windows
        self.header_win = None
        self.content_win = None
        self.status_win = None
        self.input_win = None
        
        # Colors
        self.COLOR_NORMAL = 1
        self.COLOR_HIGHLIGHT = 2
        self.COLOR_WARNING = 3
        self.COLOR_ERROR = 4
        self.COLOR_SUCCESS = 5
        
        # Set up logging
        self.logger = logging.getLogger("UserInterface")
        
        # Add console handler for UI-related logs
        ui_console_handler = logging.StreamHandler(sys.stderr)
        ui_console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('UI: %(message)s')
        ui_console_handler.setFormatter(formatter)
        self.logger.addHandler(ui_console_handler)
    
    def start(self):
        """Start the user interface with curses"""
        self.active = True
        signal.signal(signal.SIGINT, self.handle_interrupt)
        
        try:
            curses.wrapper(self.main)
        except Exception as e:
            self.logger.error(f"Error in curses interface: {e}")
        finally:
            self.active = False
            self.logger.info("User interface stopped")
    
    def pause(self):
        """Pause the UI (when switching to a game interface)"""
        if self.stdscr:
            curses.endwin()
        self.paused = True
        self.logger.info("User interface paused")
    
    def resume(self):
        """Resume the curses interface after it was paused"""
        self.active = True
        self.paused = False
        
        try:
            # Reiniciar completamente la interfaz de curses
            curses.endwin()  # Terminar definitivamente la sesión anterior
            
            # Inicializar una sesión completamente nueva
            self.stdscr = curses.initscr()
            curses.start_color()
            curses.cbreak()
            curses.noecho()
            self.stdscr.keypad(True)
            
            # Ocultar el cursor
            try:
                curses.curs_set(0)
            except:
                pass  # Algunos terminales no soportan esta operación
            
            # Recrear todos los elementos de UI
            self.setup_colors()
            self.setup_windows()
            
            # Limpiar completamente la pantalla
            self.stdscr.clear()
            self.stdscr.refresh()
            
            # Actualizar inmediatamente todos los elementos
            self.update_header()
            self.update_status("Back to main menu")
            
            # Iniciar directamente el menú principal
            self.main_menu()
        except Exception as e:
            self.logger.error(f"Error resuming UI: {e}")
            # Intentar recuperación de emergencia
            curses.wrapper(self.main)
    
    def _resume_internal(self, stdscr):
        """Método interno para reinicializar la interfaz dentro de wrapper"""
        self.stdscr = stdscr
        
        # Setup básico
        curses.cbreak()
        curses.noecho()
        stdscr.keypad(True)
        
        # Recrear configuración
        self.setup_colors()
        self.setup_windows()
        
        # Actualizar la pantalla inmediatamente
        self.update_header()
        self.update_status("Volviendo al menú principal...")
        
        # Continuar con el main menu
        self.main_menu()
    
    def handle_interrupt(self, sig, frame):
        """Handle interrupt signal"""
        self.active = False
        if self.stdscr:
            curses.endwin()
        self.logger.info("Received interrupt signal")
    
    def check_terminal_size(self):
        """Check if terminal size is adequate and handle resize events"""
        h, w = self.stdscr.getmaxyx()
        min_h, min_w = 24, 80  # Dimensiones mínimas recomendadas
        
        if h < min_h or w < min_w:
            # Terminal demasiado pequeña
            self.stdscr.clear()
            msg = f"Terminal muy pequeña. Tamaño mínimo: {min_w}x{min_h}"
            if h > 0 and w > 0:  # Evitar errores si el tamaño es 0
                try:
                    self.stdscr.addstr(0, 0, msg[:w-1])
                    self.stdscr.refresh()
                except:
                    pass
            return False
        return True
    
    def handle_resize(self):
        """Handle terminal resize event"""
        # Obtener el nuevo tamaño
        curses.update_lines_cols()
        
        # Recrear ventanas con el nuevo tamaño
        self.setup_windows()
        
        # Redibujar todo
        self.stdscr.clear()
        self.stdscr.refresh()
        self.update_header()
        self.update_status("Ventana redimensionada")
    
    def setup_colors(self):
        """Set up color pairs"""
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(self.COLOR_NORMAL, curses.COLOR_WHITE, -1)
        curses.init_pair(self.COLOR_HIGHLIGHT, curses.COLOR_CYAN, -1)
        curses.init_pair(self.COLOR_WARNING, curses.COLOR_YELLOW, -1)
        curses.init_pair(self.COLOR_ERROR, curses.COLOR_RED, -1)
        curses.init_pair(self.COLOR_SUCCESS, curses.COLOR_GREEN, -1)
    
    def setup_windows(self):
        """Set up the curses windows for the interface"""
        max_y, max_x = self.stdscr.getmaxyx()
        
        # Create windows
        self.header_win = curses.newwin(3, max_x, 0, 0)
        self.content_win = curses.newwin(max_y - 6, max_x, 3, 0)
        self.status_win = curses.newwin(1, max_x, max_y - 3, 0)
        self.input_win = curses.newwin(2, max_x, max_y - 2, 0)
    
    def main(self, stdscr):
        """Main function that creates the UI"""
        self.stdscr = stdscr
        
        # Setup
        curses.cbreak()
        curses.noecho()
        stdscr.keypad(True)
        
        # Configurar colores y ventanas
        self.setup_colors()
        self.setup_windows()
        
        # Guardar tamaño inicial para detectar redimensionamientos en Windows
        self.last_terminal_size = self.stdscr.getmaxyx()
        
        # Intentar registrar manejador para SIGWINCH solo en sistemas compatibles
        try:
            import platform
            if platform.system() != "Windows":
                signal.signal(signal.SIGWINCH, self.handle_resize)
            else:
                self.logger.info("Resize handling not supported on Windows")
        except Exception as e:
            self.logger.warning(f"Could not register resize handler: {e}")
        
        # Mostrar bienvenida
        self.display_welcome()

        while not self.user.connect_to_server():
            self.display_message("Failed to connect to server. Retrying...", self.COLOR_WARNING, wait_key=False)
  
        while not self.user.login():
            self.display_message("Failed to login. Retrying...", self.COLOR_WARNING, wait_key=False)
        
        # Main menu loop
        while self.active:    
            try:
                if self.check_terminal_size():
                    self.main_menu()
                else:
                    time.sleep(0.5)
            except curses.error as e:
                self.logger.error(f"Curses error: {e}")
                self.handle_resize()
        
        # Clean up
        curses.endwin()
    
    def update_header(self):
        """Update the header window"""
        self.header_win.clear()
        self.header_win.box()
        
        # Display title
        title = "Krypto Game Client"
        self.header_win.addstr(1, 2, title, curses.A_BOLD | curses.color_pair(self.COLOR_HIGHLIGHT))
        
        # Display username if logged in
        if self.user.username:
            user_info = f"User: {self.user.username}"
            self.header_win.addstr(1, len(title) + 10, user_info)
        
        self.header_win.refresh()
    
    def update_status(self, status="Ready"):
        """Update the status bar"""
        self.status_win.clear()
        self.status_win.addstr(0, 0, status[:self.status_win.getmaxyx()[1]-1])
        self.status_win.refresh()
    
    def display_welcome(self):
        """Display the welcome screen"""
        self.update_header()
        
        welcome_text = [
            "Welcome to Krypto Game!",
            "",
            "This game challenges your mathematical skills with Krypto puzzles.",
            "You can join existing game servers or create your own.",
            "",
            "Press any key to continue..."
        ]
        
        # Display welcome message
        for i, line in enumerate(welcome_text):
            y_pos = self.content_win.getmaxyx()[0]//2 - len(welcome_text)//2 + i
            x_pos = max(0, self.content_win.getmaxyx()[1]//2 - len(line)//2)
            
            if i == 0:  # Title line
                self.content_win.addstr(y_pos, x_pos, line, 
                                      curses.A_BOLD | curses.color_pair(self.COLOR_HIGHLIGHT))
            else:
                self.content_win.addstr(y_pos, x_pos, line)
        
        self.content_win.refresh()
        self.update_status("Press any key to continue...")
        
        # Wait for key press
        self.content_win.getch()
    
    def display_message(self, message, color=None, wait_key=True):
        """Display a message to the user"""
        self.content_win.clear()
        self.content_win.box()
        
        # Split message into lines if it contains newlines
        lines = message.split("\n")
        
        # Display each line
        for i, line in enumerate(lines):
            if i >= self.content_win.getmaxyx()[0] - 2:  # Account for box border
                break
                
            color_attr = curses.color_pair(color) if color else 0
            self.content_win.addstr(i + 1, 2, line[:self.content_win.getmaxyx()[1]-4], color_attr)
        
        self.content_win.refresh()
        
        if wait_key:
            # Use the status window for the prompt, not duplicating in content
            self.update_status("Press any key to continue...")
            self.content_win.getch()
            # Clear the status after key press
            self.update_status("")
    
    def get_input(self, prompt, default=""):
        """Get text input from the user"""
        self.content_win.clear()
        self.content_win.box()
        self.content_win.addstr(1, 2, prompt)
        self.content_win.refresh()
        
        # Set up input field
        input_y = 3
        input_x = 2
        max_input_len = self.content_win.getmaxyx()[1] - 4
        
        # Create input box
        self.content_win.addstr(input_y, input_x, " " * max_input_len)
        self.content_win.box()
        self.content_win.refresh()
        
        # Enable cursor and echo for input
        curses.curs_set(1)
        curses.echo()
        
        # Position cursor at the input position
        self.content_win.move(input_y, input_x)
        
        # Get input
        user_input = self.content_win.getstr(input_y, input_x, max_input_len).decode('utf-8')
        
        # Reset cursor and echo settings
        curses.noecho()
        curses.curs_set(0)
        
        return user_input if user_input else default
    
    def menu(self, title, options, prompt="Select an option:"):
        """Display a menu and get user selection"""
        while self.active:
            self.content_win.clear()
            self.content_win.box()
            
            # Display title
            self.content_win.addstr(1, 2, title, curses.A_BOLD)
            self.content_win.addstr(2, 2, prompt)
            
            # Display options
            for i, (option_key, option_text) in enumerate(options.items()):
                option_display = f"{option_key}. {option_text}"
                self.content_win.addstr(i + 4, 4, option_display)
            
            self.content_win.refresh()
            
            # Update status without duplicating press key message
            self.update_status("Enter your choice...")
            
            # Get user input
            choice = self.content_win.getkey().lower()
            
            if choice in options:
                # Clear the status before returning
                self.update_status("")
                return choice
            
            # Display error if invalid choice
            self.update_status("Invalid choice. Try again.")
            time.sleep(1)
    
    def main_menu(self):
        """Display the main menu and handle user choices"""
        while self.active:
            self.update_header()
            
            choice = self.menu(
                "Main Menu",
                {
                    "1": "Learn how to play",
                    "2": "Join Server",
                    "3": "Create Server",
                    "q": "Quit"
                }
            )
            
            if choice == "1":
                self.show_tuturial()
            elif choice == "2":
                self.join_server()
            elif choice == "3":
                self.create_server()
            elif choice == "q":
                # Confirm before quitting
                if self.confirm_dialog("Are you sure you want to quit?"):
                    self.active = False
                    break
    
    def show_tuturial(self):
        """Display the tutorial"""
        self.display_message(IM.TUTORIAL, wait_key=True)

    def _parse_server_list(self):
        """Helper function to get and parse the server list from the server"""
        self.update_status("Getting server list...")
        server_list = self.user.get_server_list()
        
        if not server_list:
            return [], []
        
        # Parse the server entries
        parsed_servers = []
        server_ids = []
        
        for i, server_str in enumerate(server_list):
            try:
                # Extract server information
                id_match = re.search(r"ID:\s*([^,]+)", server_str)
                name_match = re.search(r"Name:\s*([^,]+)", server_str)
                mode_match = re.search(r"Mode:\s*([^,]+)", server_str)
                players_match = re.search(r"Players:\s*([^/]+)/([^,]+)", server_str)
                
                if id_match and name_match and mode_match and players_match:
                    server_id = id_match.group(1).strip()
                    server_name = name_match.group(1).strip()
                    server_mode = mode_match.group(1).strip()
                    current_players = players_match.group(1).strip()
                    max_players = players_match.group(2).strip()
                    
                    # Format display string
                    display_text = f"{server_name} ({server_mode}) - Players: {current_players}/{max_players}"
                    
                    parsed_servers.append(display_text)
                    server_ids.append(server_id)
            except Exception as e:
                self.logger.error(f"Error parsing server entry: {server_str} - {e}")
        
        return parsed_servers, server_ids
    
    
    def join_server(self):
        """Join a server using the menu system"""
        parsed_servers, server_ids = self._parse_server_list()
        
        if not parsed_servers:
            self.display_message("No servers available.", self.COLOR_WARNING)
            return
        
        # Create options dictionary for the menu
        options = {}
        for i, server_text in enumerate(parsed_servers):
            option_key = str(i+1)
            options[option_key] = server_text
        
        # Add back option
        options["q"] = "Back to Main Menu"
        
        # Display menu and handle selection
        choice = self.menu("Join Server", options, "Select a server to join:")
        
        if choice != "q" and choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(server_ids):
                server_name = options[choice].split(" (")[0]  # Get just the server name
                self.update_status(f"Joining server {server_name}")
                self.user.join_server(server_ids[idx])
    
    def create_server(self):
        """Create a new server"""
        options = {
            "1": "Classic Mode",
            "2": "Competitive Mode",
            "c": "Cancel"
        }
        
        choice = self.menu(
            "Create Server",
            options,
            "Select server type:"
        )
        
        if choice == "c":
            return
        elif choice == "1":
            self.create_classic_server()
        elif choice == "2":
            self.create_competitive_server()
    
    def create_classic_server(self):
        """Create a classic mode server"""
        server_name = self.get_input("Enter server name:")
        max_players = self.get_input("Enter maximum players (1-8):", "8")
        
        try:
            max_players = int(max_players)
            if not (1 <= max_players <= 8):
                self.display_message("Invalid number of players. Using default (8).", self.COLOR_WARNING)
                max_players = 8
        except ValueError:
            self.display_message("Invalid input. Using default (8).", self.COLOR_WARNING)
            max_players = 8
        
        
        self.update_status("Creating server...")
        self.user.create_server(server_name, "classic", max_players)
    
    def create_competitive_server(self):
        """Create a competitive mode server"""
        server_name = self.get_input("Enter server name (or leave empty for random name):")
        puzzle_count = self.get_input("Enter number of puzzles (5-20):", "10")
        
        try:
            puzzle_count = int(puzzle_count)
            if not (5 <= puzzle_count <= 20):
                self.display_message("Invalid number of puzzles. Using default (10).", self.COLOR_WARNING)
                puzzle_count = 10
        except ValueError:
            self.display_message("Invalid input. Using default (10).", self.COLOR_WARNING)
            puzzle_count = 10
    
        
        self.update_status("Creating server...")
        if self.user.create_server(server_name, "competitive", puzzle_count):
            self.display_message("Server created successfully!", self.COLOR_SUCCESS)
        else:
            self.display_message("Failed to create server.", self.COLOR_ERROR)
    
    def confirm_dialog(self, message):
        """Display a confirmation dialog"""
        self.content_win.clear()
        self.content_win.box()
        self.content_win.addstr(1, 2, message)
        self.content_win.addstr(3, 2, "Press Y to confirm, N to cancel")
        self.content_win.refresh()
        
        while True:
            key = self.content_win.getkey().lower()
            if key == 'y':
                return True
            elif key == 'n':
                return False