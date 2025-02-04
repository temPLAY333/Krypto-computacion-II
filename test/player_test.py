import unittest
from unittest.mock import Mock, MagicMock, patch
from client.player import Player
from common.social import Messages
from parameterized import parameterized

class TestPlayer(unittest.TestCase):

    def setUp(self):
        patcher = patch('builtins.print')
        self.mock_print = patcher.start()
        self.addCleanup(patcher.stop)

        self.username = "test_user"
        self.player = Player(self.username, MagicMock())

    @patch('client.player.curses.wrapper')
    @patch('client.player.threading.Thread')
    def test_01_play(self, mock_thread, mock_curses_wrapper):
        self.player.play()

        mock_thread.assert_called_once()
        mock_curses_wrapper.assert_called_once()

    def test_02_handle_server_messages_new_puzzle(self):
        message = f"{Messages.NEW_PUZZLE}|puzzle_data".encode()
        self.player.commands[Messages.NEW_PUZZLE] = mock_handler = Mock()
        self.player.socket.recv.return_value = message

        self.player.handle_server_messages(test=True)
        mock_handler.assert_called_once_with("puzzle_data")

    def test_03_handle_server_messages_puzzle_result(self):
        message = f"{Messages.PUZZLE_RESULT}|result_data".encode()
        self.player.commands[Messages.PUZZLE_RESULT] = mock_handler = Mock()
        self.player.socket.recv.return_value = message

        self.player.handle_server_messages(test=True)
        mock_handler.assert_called_once_with("result_data")

    def test_04_handle_server_messages_game_state(self):
        message = f"{Messages.GAME_STATE}|1|0|3".encode()
        self.player.commands[Messages.GAME_STATE] = mock_handler = Mock()
        self.player.socket.recv.return_value = message

        self.player.handle_server_messages(test=True)
        mock_handler.assert_called_once_with("1", "0", "3")
    
    def test_05_hande_server_messages_unknown_command(self):
        self.player.socket.recv.return_value = f"unknown_command|data".encode()

        self.player.handle_server_messages(test=True)

        self.assertIn("Unknown command from server: unknown_command", self.player.message_buffer)
    
    def test_06_handle_server_messages_error(self):
        self.player.socket.recv.side_effect = Exception("Error")

        self.player.handle_server_messages(test=True)

        self.assertIn("Error receiving data from server: Error", self.player.message_buffer)

    def test_07_handle_new_puzzle(self):
        puzzle = "new_puzzle"

        self.player.handle_new_puzzle(puzzle)

        self.assertEqual(self.player.puzzle, puzzle)

    def test_08_handle_puzzle_result(self):
        result = "puzzle_result"

        self.player.handle_puzzle_result(result)

        self.assertIn(f"Tu resultado fue: {result}", self.player.message_buffer)

    def test_09_handle_game_state(self):
        self.player.puzzle = "test_puzzle"

        self.player.handle_game_state(1, 1, 3)

        self.assertIn("""
        Jugadores que han terminado: 1/3
        Jugadores que se han rendido: 1/3
        
        Puzzle: test_puzzle""", self.player.message_buffer)

    @patch('client.player.curses.curs_set')
    @patch('client.player.curses.newwin')
    @patch('client.player.curses.echo')
    @patch('client.player.curses.noecho')
    @patch('client.player.Player.exit_game')
    def test_10_handle_user_input_exit(self, mock_noecho, mock_echo, mock_newwin, mock_curs_set, mock_exit_game):
        stdscr = Mock()
        stdscr.getmaxyx.return_value = (20, 80)  # 
        input_win = Mock()
        mock_newwin.return_value = input_win
        input_win.getstr.return_value = b"exit"

        self.player.handle_user_input(stdscr)

        self.player.socket.sendall.assert_called_with(Messages.PLAYER_EXIT.encode())
        # mock_exit_game.assert_called_once()
    
    @patch('client.player.curses.curs_set')
    @patch('client.player.curses.newwin')
    @patch('client.player.curses.echo')
    @patch('client.player.curses.noecho')
    def test_11_handle_user_input_quit(self, mock_noecho, mock_echo, mock_newwin, mock_curs_set):
        stdscr = Mock()
        stdscr.getmaxyx.return_value = (20, 80)
        input_win = Mock()
        mock_newwin.return_value = input_win
        input_win.getstr.return_value = b"quit"

        self.player.handle_user_input(stdscr)

        self.player.socket.sendall.assert_called_with(Messages.PLAYER_SURRENDER.encode())

    @patch('client.player.curses.curs_set')
    @patch('client.player.curses.newwin')
    @patch('client.player.curses.echo')
    @patch('client.player.curses.noecho')
    def test_12_handle_user_input_puzzle_result(self, mock_noecho, mock_echo, mock_newwin, mock_curs_set):
        stdscr = Mock()
        stdscr.getmaxyx.return_value = (20, 80)
        input_win = Mock()
        mock_newwin.return_value = input_win
        input_win.getstr.return_value = b"2 + 2 * 5 - 10"

        self.player.handle_user_input(stdscr)

        self.player.socket.sendall.assert_called_with(f"{Messages.SUBMIT_ANSWER}|2 + 2 * 5 - 10".encode())

    def test_13_display_messages(self):
        stdscr = Mock()
        stdscr.getmaxyx.return_value = (20, 80)  # Mock the return value of getmaxyx
        self.player.message_buffer = ["message1", "message2"]
        self.player.display_messages(stdscr)
        stdscr.clear.assert_called_once()
        stdscr.addstr.assert_any_call(0, 0, "message1")
        stdscr.addstr.assert_any_call(1, 0, "message2")
        stdscr.refresh.assert_called_once()

    def test_14_exit_game(self):
        self.player.socket = Mock()
        self.player.exit_game()
        self.player.socket.sendall.assert_called_with(Messages.PLAYER_EXIT.encode())
        self.player.socket.close.assert_called_once()

if __name__ == '__main__':
    unittest.main()