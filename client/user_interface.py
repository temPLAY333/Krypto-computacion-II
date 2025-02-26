import curses

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
                self.user.view_server_list()
            elif key == ord('2'):
                self.user.join_server()
            elif key == ord('3'):
                self.user.create_server()
            elif key == ord('q'):
                if self.get_confirmation("Are you sure you want to quit? (y/n)"):
                    break

    def view_server_list(self):
        """Muestra la lista de servidores activos."""
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Active Servers:")
        # Aquí se mostraría la lista de servidores activos
        self.stdscr.addstr(1, 0, "Server 1")
        self.stdscr.addstr(2, 0, "Server 2")
        self.stdscr.addstr(3, 0, "Press any key to return to the main menu.")
        self.stdscr.refresh()
        self.stdscr.getch()

    def join_server(self):
        """Permite al usuario unirse a un servidor."""
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Joining Server...")
        self.stdscr.refresh()
        # Aquí se manejaría la lógica para unirse a un servidor
        self.stdscr.getch()

    def create_server(self):
        """Permite al usuario crear un servidor nuevo."""
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Creating Server...")
        self.stdscr.refresh()
        # Aquí se manejaría la lógica para crear un servidor nuevo
        self.stdscr.getch()