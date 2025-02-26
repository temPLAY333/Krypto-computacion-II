import unittest
from unittest.mock import patch, MagicMock, call
from puzzle.game_server import ServerClassic
from common.social import Messages

class TestServerClassic(unittest.TestCase):

    def setUp(self):
        patcher = patch('builtins.print')
        self.mock_print = patcher.start()
        self.addCleanup(patcher.stop)

        self.pipe_puzzle = MagicMock()
        self.pipe_message = MagicMock()

        # Mock the socket methods to avoid address/port conflicts
        self.socket_patcher = patch('socket.socket')
        self.mock_socket_class = self.socket_patcher.start()
        self.addCleanup(self.socket_patcher.stop)

        self.mock_socket_instance = MagicMock()
        self.mock_socket_class.return_value = self.mock_socket_instance

        self.server = ServerClassic(self.pipe_puzzle, self.pipe_message)
    
    def tearDown(self):
        self.server = None
    
    @patch('puzzle.server_classic.ServerClassic.handle_client_messages', return_value=None)
    @patch('puzzle.server_classic.ServerClassic.check_game_status', return_value=None)
    @patch('socket.socket', new_callable=MagicMock())
    def test_01_starting(self, mock_socket, mock_check_game_status, mock_handle_client):
        self.server.server_socket = MagicMock()
        self.server.server_socket.accept.return_value = (mock_socket, "test-direction")
        self.pipe_puzzle.get.return_value = "test puzzle"

        self.server.start(test=True)

        self.pipe_puzzle.get.assert_called_once()
        self.pipe_message.sendall.assert_called_with("ok")
        self.server.server_socket.accept.assert_called_once()
        self.mock_print.assert_called_with("Conexión aceptada de test-direction")
        self.assertEqual(self.server.players, 1)

        mock_socket.sendall.assert_has_calls([
            call(Messages.GREETING.encode()),
            call((Messages.NEW_PUZZLE + "|" + "test puzzle").encode())
        ])
        mock_check_game_status.assert_called_once()
        mock_handle_client.assert_called_once()
    
    @patch('socket.socket', new_callable=MagicMock())
    def test_02_starting_server_full(self, mock_socket):
        self.server.players = 8
        self.server.server_socket = MagicMock()
        self.server.server_socket.accept.return_value = (mock_socket, "test-direction")
        self.pipe_puzzle.get.return_value = "test puzzle"

        self.server.start(test=True)

        self.pipe_puzzle.get.assert_called_once()
        self.pipe_message.sendall.assert_called_with("ok")
        self.server.server_socket.accept.assert_called_once()
        self.assertEqual(self.server.players, 8)

    def test_03_broadcast(self):
        client_socket1 = MagicMock()
        client_socket2 = MagicMock()
        self.server.client_sockets = [client_socket1, client_socket2]
        message = "test broadcast"

        self.server.broadcast(message)

        client_socket1.sendall.assert_called_with(message.encode('utf-8'))
        client_socket2.sendall.assert_called_with(message.encode('utf-8'))

    @patch('puzzle.server_classic.ServerClassic.check_game_status', return_value=None)
    @patch('puzzle.logic.KryptoLogic.verify_solution', return_value=True)
    def test_04_handle_posible_solution_correct(self, mock_krypto ,mock_status):
        client_socket = MagicMock()
        self.server.puzzle = [4,4,4,4,1]
        solution = "test solution"

        self.server.handle_posible_solution(client_socket, solution)

        self.assertEqual(self.server.solved, 1)

        client_socket.sendall.assert_called_with((Messages.PUZZLE_RESULT + "|Correcto").encode())
        mock_status.assert_called_once()
    
    @patch('puzzle.logic.KryptoLogic.verify_solution', return_value=False)
    def test_05_handle_posible_solution_incorrect(self, mock_krypto):
        client_socket = MagicMock()
        self.server.puzzle = [4,4,4,4,1]
        solution = "test solution"

        self.server.handle_posible_solution(client_socket, solution)

        self.assertEqual(self.server.solved, 0)

        client_socket.sendall.assert_called_with((Messages.PUZZLE_RESULT + "|Incorrecto").encode())

    @patch('puzzle.server_classic.ServerClassic.check_game_status', return_value=None)
    def test_06_handle_posible_rend(self, mock_status):
        client_socket = MagicMock()

        self.server.handle_player_rend(client_socket)

        self.assertEqual(self.server.abandoned, 1)
        client_socket.sendall.assert_called_with(("You gave up").encode())
        mock_status.assert_called_once()

    @patch('puzzle.server_classic.ServerClassic.check_game_status', return_value=None)
    def test_07_handle_player_disconnect(self, mock_status):
        self.server.players = 1

        self.server.handle_player_disconnect()

        self.assertEqual(self.server.players, 0)
        self.pipe_message.sendall.assert_called_with("vacio")
        mock_status.assert_called_once()

    @patch('puzzle.server_classic.ServerClassic.broadcast', return_value=None)
    def test_08_check_game_status_incomplete(self, mock_broadcast):
        self.server.players = 6
        self.server.solved = 1
        self.server.abandoned = 1
        self.server.puzzle = "puzzle"
        self.server.client_sockets = [MagicMock(), MagicMock()]

        self.server.check_game_status()

        self.pipe_puzzle.get.assert_not_called()
        self.assertEqual(self.server.solved, 1)
        self.assertEqual(self.server.abandoned, 1)
        self.server.broadcast.assert_any_call(Messages.GAME_STATE + f"|1|1|6")

    @patch('puzzle.server_classic.ServerClassic.broadcast', return_value=None)
    def test_09_check_game_status_complete(self, mock_broadcast):
        self.server.players = 2
        self.server.solved = 1
        self.server.abandoned = 1
        self.server.puzzle = "puzzle"
        self.server.client_sockets = [MagicMock(), MagicMock()]

        self.server.check_game_status()

        self.pipe_puzzle.get.assert_called_once()
        self.pipe_message.sendall.assert_called_with("ok")
        self.assertEqual(self.server.solved, 0)
        self.assertEqual(self.server.abandoned, 0)
        self.server.broadcast.assert_any_call(Messages.NEW_PUZZLE + "|" + self.server.puzzle)
        self.server.broadcast.assert_any_call(Messages.GAME_STATE + f"|0|0|2")

if __name__ == '__main__':
    unittest.main()