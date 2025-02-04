import unittest
from unittest.mock import patch, MagicMock
from unittest import mock
from client.user import User
from common.social import Messages

class TestUser(unittest.TestCase):

    def setUp(self):
        patcher = patch('builtins.print')
        self.mock_print = patcher.start()
        self.addCleanup(patcher.stop)

    @patch('socket.socket', new_callable=MagicMock())
    def test_01_connect_to_server_success(self, mock_socket):
        mock_socket_instance = mock_socket.return_value
        mock_socket_instance.connect.return_value = None

        user = User()
        user.socket = mock_socket_instance

        self.assertTrue(user.connect_to_server())
        mock_socket_instance.connect.assert_called_once()


    @patch('socket.socket.connect', side_effect=Exception("Connection error"))
    def test_02_connect_to_server_exception(self, mock_connect):
        user = User()
    
        self.assertFalse(user.connect_to_server())
        self.mock_print.assert_any_call("Connection error: Connection error")

    @patch('builtins.input', return_value='testUsername')
    @patch('socket.socket', new_callable=MagicMock())
    def test_03_login_success(self, mock_socket, mock_input):
        user = User()
        user.socket = mock_socket
        mock_socket.recv.return_value = Messages.LOGIN_SUCCESS.encode()

        self.assertTrue(user.login())

        mock_socket.sendall.assert_called_with(b'testUsername')
        mock_socket.recv.assert_called_once()
        self.assertEqual(user.username, 'testUsername')
        self.mock_print.assert_any_call(Messages.LOGIN_SUCCESS)

    @patch('builtins.input', return_value='wrong')
    @patch('socket.socket', new_callable=MagicMock())
    def test_04_login_invalid_username(self, mock_socket, mock_input):
        user = User()
        user.socket = mock_socket
        mock_socket.recv.return_value = Messages.INVALID_USERNAME.encode()

        self.assertFalse(user.login())
        self.mock_print.assert_any_call(Messages.INVALID_USERNAME)

    @patch('builtins.input', return_value='testUsername')
    @patch('socket.socket', new_callable=MagicMock())
    def test_05_login_error(self, mock_socket, mock_input):
        user = User()
        user.socket = mock_socket
        mock_socket.recv.return_value = Messages.LOGIN_ERROR.encode()

        self.assertFalse(user.login())
        self.mock_print.assert_any_call(Messages.LOGIN_ERROR)
    
    @patch('builtins.input', return_value='testUsername')
    @patch('socket.socket', new_callable=MagicMock())
    def test_06_login_exception(self, mock_socket, mock_input):
        user = User()
        user.socket = mock_socket
        mock_socket.recv.side_effect = Exception("Connection error")

        self.assertFalse(user.login())
        self.mock_print.assert_any_call("Error during login: Connection error")

    @patch('builtins.input', return_value='1')
    @patch('socket.socket', new_callable=MagicMock())
    def test_07_view_server_list(self, mock_socket, mock_input):
        user = User()
        user.socket = mock_socket
        mock_socket.recv.return_value = 'Server List'.encode()

        user.view_server_list()

        mock_socket.sendall.assert_called_with(b"1")
        mock_socket.recv.assert_called_once()
        self.mock_print.assert_any_call('Server List')

    @patch('builtins.input', return_value='server_id')
    @patch('socket.socket', new_callable=MagicMock)
    def test_08_join_server_success(self, mock_socket, mock_input):
        mock_socket_instance = mock_socket.return_value
        mock_socket_instance.recv.return_value = 'Success|server_name|12345'.encode()

        user = User()
        user.socket = mock_socket_instance

        with patch('client.player.Player.play') as mock_play:
            user.join_server()

            mock_socket_instance.sendall.assert_called_with(b"2|server_id")
            mock_socket_instance.recv.assert_called()
            mock_socket_instance.connect.assert_called_once()
            mock_play.assert_called_once()

    @patch('builtins.input', return_value='server_id')
    @patch('socket.socket', new_callable=MagicMock())
    def test_09_join_server_failure(self, mock_socket, mock_input):
        user = User()
        user.socket = mock_socket
        mock_socket.recv.return_value = 'Fail'.encode()

        user.join_server()

        mock_socket.sendall.assert_called_with(b"2|server_id")
        mock_socket.recv.assert_called_once()
    
    @patch('builtins.input', return_value='server_id')
    @patch('socket.socket', new_callable=MagicMock())
    def test_10_join_server_full(self, mock_socket, mock_input):
        user = User()
        user.socket = mock_socket
        mock_socket.recv.return_value = Messages.SERVER_FULL.encode()

        user.join_server()

        mock_socket.sendall.assert_called_with(b"2|server_id")
        mock_socket.recv.assert_called()

    @patch('builtins.input', side_effect=['server_name', 'classic'])
    @patch('socket.socket', new_callable=MagicMock())
    def test_11_create_server_success(self, mock_socket, mock_input):
        user = User()
        user.socket = mock_socket
        mock_socket.recv.return_value = 'Server created'.encode()

        user.create_server()

        mock_socket.sendall.assert_called_with(b"3|server_name|classic")
        mock_socket.recv.assert_called_once()

    @patch('builtins.input', side_effect=['server_name', 'invalid_mode'])
    @patch('socket.socket', new_callable=MagicMock())
    def test_12_create_server_failure(self, mock_socket, mock_input):
        user = User()
        user.socket = mock_socket

        user.create_server()

        self.assertEqual(mock_input.call_count, 2)

if __name__ == '__main__':
    unittest.main()