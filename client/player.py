import time
import curses
import threading

from common.social import PlayerServerMessages as SM

class Player():
    def __init__(self, username, socket):
        self.username = username
        self.puzzle = None

        self.socket = socket

        self.message_buffer = []
        self.commands = {
            SM.NEW_PUZZLE: self.handle_new_puzzle,
            SM.PUZZLE_RESULT: self.handle_puzzle_result,
            SM.GAME_STATE: self.handle_game_state,
        }
        
    def play(self):
        """Inicia el flujo de juego."""
        threading.Thread(target=self.handle_server_messages, daemon=True).start()
        curses.wrapper(self.handle_user_input)

    def handle_server_messages(self, test=False):
        """Hilo para escuchar y manejar mensajes del servidor."""
        while True:
            try:
                data = self.socket.recv(1024).decode()
                if not data:
                    break
                command, *args = data.split("|")
                if command in self.commands:
                    self.commands[command](*args)
                else:
                    self.message_buffer.append(f"Unknown command from server: {command}")
            except Exception as e:
                self.message_buffer.append(f"Error receiving data from server: {e}")
                break
            if test:
                break

    def handle_new_puzzle(self, puzzle):
        """Maneja un nuevo puzzle recibido del servidor."""
        self.puzzle = puzzle

    def handle_puzzle_result(self, result):
        """Maneja el resultado del puzzle recibido del servidor."""
        self.message_buffer.append(f"Tu resultado fue: {result}")
    
    def handle_game_state(self, solved, abandoned, players):
        self.message_buffer.append(f"""
        Jugadores que han terminado: {solved}/{players}
        Jugadores que se han rendido: {abandoned}/{players}
        
        Puzzle: {self.puzzle}""")

    def handle_user_input(self, stdscr, test=False):
        """Hilo para manejar la entrada del usuario."""
        curses.curs_set(1)
        stdscr.clear()
        stdscr.refresh()

        max_y, max_x = stdscr.getmaxyx()
        input_win = curses.newwin(3, max_x, max_y - 3, 0)
        input_win.border()
        input_win.addstr(1, 1, "Enter your solution (or 'exit' to end playing or 'quit' to surrender): ")
        input_win.refresh()

        while True:
            self.display_messages(stdscr)
            input_win.clear()
            input_win.border()
            input_win.addstr(1, 1, "Enter your solution (or 'exit' to end playing or 'quit' to surrender): ")
            input_win.refresh()
            curses.echo()
            user_input = input_win.getstr(1, 65, 20).decode('utf-8').strip()
            curses.noecho()

            if user_input.lower() == "exit":
                self.socket.sendall(SM.PLAYER_EXIT.encode())
                self.exit_game()
                break
            elif user_input.lower() == "quit":
                self.socket.sendall(SM.PLAYER_SURRENDER.encode())
                if test:
                    break
            else:
                try:
                    # Envía la solución al servidor
                    solution = user_input  # Ejemplo: "2 + 2 * 5 - 10"
                    self.socket.sendall(f"{SM.SUBMIT_ANSWER}|{solution}".encode())
                    if test:
                        break
                except Exception as e:
                    self.message_buffer.append(f"Error sending solution: {e}")

    def display_messages(self, stdscr):
        """Muestra los mensajes del buffer."""
        stdscr.clear()
        max_y, _ = stdscr.getmaxyx()
        for idx, message in enumerate(self.message_buffer[-(max_y - 4):]):
            stdscr.addstr(idx, 0, message)
        stdscr.refresh()

    def exit_game(self, *args):
        """Cierra la conexión con el servidor."""
        if self.socket:
            self.socket.sendall(SM.PLAYER_EXIT.encode())
            self.socket.close()
        print("Goodbye!")

if __name__ == "__main__":
    username = input("Enter your username: ")
    player = Player(username)
    player.play()