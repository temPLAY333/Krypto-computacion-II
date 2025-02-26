import curses
from common.social import InterfaceMessages as IM

class UserInterface:
    def __init__(self, user):
        self.user = user
        self.stdscr = None

    def start(self):
        """Inicia la interfaz de usuario con curses."""
        curses.wrapper(self.main)

    def main(self, stdscr):
        """Función principal de curses."""
        self.stdscr = stdscr
        curses.curs_set(0)  # Ocultar el cursor
        self.stdscr.clear()
        self.stdscr.refresh()

    def display_message(self, message):
        """Muestra un mensaje al usuario."""
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, message)
        self.stdscr.refresh()
        self.stdscr.getch()

    def get_input(self, prompt):
        """Obtiene una entrada del usuario."""
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, prompt)
        self.stdscr.refresh()
        curses.echo()
        input_str = self.stdscr.getstr(1, 0).decode('utf-8')
        curses.noecho()
        return input_str

    def get_confirmation(self, prompt):
        """Obtiene una confirmación del usuario (sí/no)."""
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, prompt)
        self.stdscr.refresh()
        while True:
            key = self.stdscr.getch()
            if key == ord('y'):
                return True
            elif key == ord('n'):
                return False

    def main_menu(self):
        """Muestra el menú principal y maneja las opciones del usuario."""
        while True:
            self.stdscr.clear()
            self.stdscr.addstr(0, 0, "Main Menu")
            self.stdscr.addstr(1, 0, "1. View Server List")
            self.stdscr.addstr(2, 0, "2. Join Server")
            self.stdscr.addstr(3, 0, "3. Create Server")
            self.stdscr.addstr(4, 0, "q. Quit")
            self.stdscr.refresh()

            key = self.stdscr.getch()
            if key == ord('1'):
                self.view_server_list()
            elif key == ord('2'):
                self.join_server()
            elif key == ord('3'):
                self.create_server()
            elif key == ord('q'):
                if self.get_confirmation("Are you sure you want to quit? (y/n)"):
                    break

    def view_server_list(self):
        """Muestra la lista de servidores activos."""
        # Show "fetching" message
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Fetching server list...")
        self.stdscr.refresh()
        
        # Request server list from the main server
        self.user.send_message(self.user.UM.LIST_SERVERS)
        response = self.user.receive_message(4096) or "No response from server"
        
        # Display the response
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Active Servers:")
        
        line_count = 2
        if response == IM.NO_SERVERS:
            self.stdscr.addstr(line_count, 0, "No active servers available.")
            line_count += 1
        else:
            lines = response.strip().split('\n')
            for i, line in enumerate(lines):
                try:
                    self.stdscr.addstr(i+2, 0, line)
                    line_count = i+3
                except:
                    # Handle case where line might be too long
                    continue
        
        self.stdscr.addstr(0, 0, "Press any key to continue...")
        self.stdscr.refresh()
        curses.echo()
        input_str = self.stdscr.getstr(1, 0).decode('utf-8')
        curses.noecho()
        return input_str

    def join_server(self):
        """Permite al usuario unirse a un servidor."""
        # First show server list
        self.view_server_list()
        
        # Get server ID
        server_id = self.get_input(IM.ASK_SERVER_ID)
        if not server_id:
            return
            
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Connecting to server...")
        self.stdscr.refresh()
        
        # Send join request to the main server
        self.user.send_message(self.user.UM.CHOOSE_SERVER + f"|{server_id}")
        response = self.user.receive_message()
        
        # Handle response
        if response.startswith(self.user.UM.OK):
            _, name, server_game_port = response.split("|")
            self.stdscr.clear()
            self.stdscr.addstr(0, 0, f"Joining Server {name}...")
            self.stdscr.refresh()
            
            # Handle the connection in the User class
            self.user.connect_to_game_server(name, server_game_port.strip('.\n'))
        else:
            self.display_message(response)
            self.stdscr.getch()

    def create_server(self):
        """Permite al usuario crear un servidor nuevo."""
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Create New Server")
        self.stdscr.refresh()
        
        # Get server details
        name = self.get_input(IM.CREATE_SERVER_NAME)
        if not name:
            return
            
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Select Server Mode:")
        self.stdscr.addstr(1, 0, "1. Classic")
        self.stdscr.addstr(2, 0, "2. Competitive")
        self.stdscr.refresh()
        
        while True:
            key = self.stdscr.getch()
            if key == ord('1'):
                mode = "classic"
                break
            elif key == ord('2'):
                mode = "competitive"
                break
        
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Creating server...")
        self.stdscr.refresh()
        
        # Send create request to the main server
        self.user.send_message(self.user.UM.CREATE_SERVER + f"|{name}|{mode}")
        response = self.user.receive_message()
        self.display_message(response)