import unittest
from unittest.mock import patch, MagicMock, call
import asyncio
from queue import Queue

from puzzle.server_classic import ClassicServer
from common.social import ServerClientMessages as SCM
from common.social import PlayerServerMessages as PSM

class TestClassicServer(unittest.TestCase):

    def setUp(self):
        # Mock queues for testing
        self.puzzle_queue = MagicMock(spec=Queue)
        self.message_queue = MagicMock(spec=Queue)
        
        # Create server instance
        self.server = ClassicServer("Test", 5001, self.puzzle_queue, self.message_queue, debug=True)
        
        # Set current puzzle for testing
        self.server.current_puzzle = [1,2,3,4,5]
        
        # Disable logging
        self.server.logger.disabled = True
        
    def tearDown(self):
        self.server = None

    def test_initialization(self):
        """Test server initialization"""
        self.assertEqual(self.server.name, "Test")
        self.assertEqual(self.server.port, 5001)
        self.assertEqual(self.server.mode, "classic")
        self.assertEqual(self.server.max_players, 8)
        
    # Tests for validate_solution
    def test_validate_solution_valid(self):
        """Test validate_solution with valid solution"""
        with patch('puzzle.logic.KryptoLogic.verify_solution', return_value=True):
            self.assertTrue(self.server.validate_solution("4+1*3-2"))
            self.assertTrue(self.server.validate_solution("1+4*3-2"))
            self.assertTrue(self.server.validate_solution("1+4*2-3"))
            self.assertTrue(self.server.validate_solution("4+3-2*1"))
    
    def test_validate_solution_valid_2(self):
        """Test validate_solution with valid solution and different puzzle"""
        self.server.current_puzzle = [5,7,1,10,11]
        with patch('puzzle.logic.KryptoLogic.verify_solution', return_value=True):
            self.assertTrue(self.server.validate_solution("5-7-1+10"))
            self.assertTrue(self.server.validate_solution("7-5-1+10"))
            self.assertTrue(self.server.validate_solution("10+7-5-1"))


    def test_validate_solution_invalid_result(self):
        """Test validate_solution with solution that doesn't match the target"""
        with patch('puzzle.logic.KryptoLogic.verify_solution', return_value=False):
            self.assertFalse(self.server.validate_solution("1+2+3-4"))
            self.assertFalse(self.server.validate_solution("1*2*3*4"))
            self.assertFalse(self.server.validate_solution("1-2-3-4"))

    def test_validate_solution_wrong_numbers(self):
        """Test validate_solution with solution using incorrect numbers"""
        self.assertFalse(self.server.validate_solution("1+2+6-4"))
        self.assertFalse(self.server.validate_solution("3+3/3+3"))
        self.assertFalse(self.server.validate_solution("5-5+5/1"))
        self.assertFalse(self.server.validate_solution("5+0+0+0"))

    def test_validate_solution_too_many_numbers(self):
        """Test validate_solution with too many numbers"""
        self.assertFalse(self.server.validate_solution("1+2+3+4+5"))
        self.assertFalse(self.server.validate_solution("1+1+1+1+1+1"))
        self.assertFalse(self.server.validate_solution("2+2+2+2+2"))

    def test_validate_solution_too_few_numbers(self):
        """Test validate_solution with too few numbers"""
        self.assertFalse(self.server.validate_solution("1+2+2"))
        self.assertFalse(self.server.validate_solution("2+3"))
        self.assertFalse(self.server.validate_solution("5"))

    def test_validate_solution_invalid_characters(self):
        """Test validate_solution with invalid characters in the solution"""
        self.server.current_puzzle = [1,2,3,4,5]

    
    def test_validate_solution_no_puzzle(self):
        """Test validate_solution with no puzzle set"""
        self.server.current_puzzle = None
        
        # Any solution should fail with no puzzle
        self.assertFalse(self.server.validate_solution("1+2+3-4"))
        
    def test_validate_solution_double_digit_numbers(self):
        """Test validate_solution with double digit numbers"""
        self.server.current_puzzle = [10,11,0,4,25]
        
        # Valid solution using double-digit numbers
        with patch('puzzle.logic.KryptoLogic.verify_solution', return_value=True):
            self.assertTrue(self.server.validate_solution("10+11+4-0"))

if __name__ == '__main__':
    unittest.main()