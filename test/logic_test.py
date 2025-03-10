import unittest
from puzzle.logic import KryptoLogic
from parameterized import parameterized
from unittest.mock import patch

class TestLogic(unittest.TestCase):
    
    def test_01_suma(self):
        self.assertEqual(KryptoLogic.suma(1, 2), 3)
        self.assertEqual(KryptoLogic.suma(2, 1), 3)
    
    def test_02_resta(self):
        self.assertEqual(KryptoLogic.resta(2, 1), 1)
        self.assertEqual(KryptoLogic.resta(1, 2), 1)
    
    def test_03_multiplicacion(self):
        self.assertEqual(KryptoLogic.multiplicacion(2, 3), 6)
        self.assertEqual(KryptoLogic.multiplicacion(3, 2), 6)

    @parameterized.expand([
        (6, 2),
        (0, None),
        (7, None),
    ])
    def test_04_division(self, a, expected):
        self.assertEqual(KryptoLogic.division(a, 3), expected)
        self.assertEqual(KryptoLogic.division(3, a), expected)
   
    def test_05_generar_puzzle(self):
        puzzle = KryptoLogic.generar_puzzle()
        self.assertEqual(len(puzzle), 5)
    
    @parameterized.expand([
        (1, ),
        (2, ),
        (3, ),
        (4, ),
        (5, ),
        (6, ),
        (7, ),
        (8, ),
        (9, ),
        (12, ),
    ])
    def test_06_solucionar_puzzle_con4_true(self, expected):
        puzzle = [4, 4, 4, 4, expected]
        self.assertTrue(KryptoLogic.solucionar_puzzle(puzzle))

    @parameterized.expand([
        ([4,4,4,4,10], ),
        ([4,4,4,4,11], )
    ])
    def test_07_solucionar_puzzle_con4_false(self, puzzle):
        self.assertFalse(KryptoLogic.solucionar_puzzle(puzzle))
    
    @parameterized.expand([
        ([1, 5, 6, 4, 1], ),        # ((6 + 4) / 5) - 1 = 1
        ([1, 5, 6, 4, 11], )        # ((6 - 4) * 5) + 1 = 11
    ])
    def test_08_solucionar_puzzle_complejos(self,puzzle):
        self.assertTrue(KryptoLogic.solucionar_puzzle(puzzle))
        
    @parameterized.expand([
        ([11, 11, 11, 11, 5], ),
        ([3, 8, 9, 11, 5], ),
        ([7, 9, 11, 12, 9], ),
        ([7, 7, 8, 8, 6], ),
        ([7, 7, 8, 8, 9], )
    ])
    def test_09_solucionar_puzzle_false(self,puzzle):
        self.assertFalse(KryptoLogic.solucionar_puzzle(puzzle))

    @parameterized.expand([
        ("1+2*3-4", ["1","+","2","*","3","-","4"]),
        ("1 +  2*  3-4  ", ["1","+","2","*","3","-","4"]),
        ("6/2+3*2", ["6","/","2","+","3","*","2"]),
        (" 6 / 2 + 3 * 2 ", ["6","/","2","+","3","*","2"]),
        ("10-2/2+3", ["10","-","2","/","2","+","3"]),
    ])
    def test_10_convertir(self, string, expected):
        self.assertEqual(KryptoLogic.convertir(string), expected)

    @parameterized.expand([
        ("1+2*3-4", 3, ["1","+","2","*","3","-","4"]),
        ("6/2+3*2", 9, ["6","/","2","+","3","*","2"]),
        ("10-2/2+3", 7, ["10","-","2","/","2","+","3"]),
        ("7-5-1+10", 11, ["7","-","5","-","1","+","10"]),
        ("5-7-1+10", 11, ["5","-","7","-","1","+","10"]),
    ])
    @patch('puzzle.logic.KryptoLogic.convertir')
    def test_11_verify_solution_true(self, string, answer, expected, mock_convertir):
        mock_convertir.return_value = expected

        self.assertTrue(KryptoLogic.verify_solution(string, answer))

    def test_12_verify_solution_false(self):
        self.assertFalse(KryptoLogic.verify_solution("1+2*3-4", 4))
        
    @patch('puzzle.logic.KryptoLogic.solucionar_puzzle')
    def test_13_generate_puzzle_normal(self, mock_solucionar_puzzle):
        # Mock solucionar_puzzle to return True
        mock_solucionar_puzzle.return_value = True

        puzzle = KryptoLogic.generar_puzzle()

        self.assertIsInstance(puzzle, list)
        self.assertEqual(len(puzzle), 5)
        self.assertTrue(all(1 <= x <= 12 for x in puzzle))

    @patch('puzzle.logic.KryptoLogic.solucionar_puzzle')
    def test_14_generate_puzzle(self, mock_solucionar_puzzle):
        # Mock solucionar_puzzle to return False for the first two calls and then call the real method
        original_solucionar_puzzle = KryptoLogic.solucionar_puzzle
        mock_solucionar_puzzle.side_effect = [False, True, original_solucionar_puzzle]
        
        puzzle = KryptoLogic.generar_puzzle()
        
        # Verify that generate_puzzle returns a puzzle with a solution
        self.assertEqual(len(puzzle), 5)
        self.assertTrue(original_solucionar_puzzle(puzzle))
    
    @patch('puzzle.logic.KryptoLogic.solucionar_puzzle')
    def test_15_generate_puzzle_no_solution(self, mock_solucionar_puzzle):
        # Mock solucionar_puzzle to always return False
        mock_solucionar_puzzle.return_value = False
        
        with self.assertRaises(Exception) as context:
            KryptoLogic.generar_puzzle()
        
        # Verify that the exception message is as expected
        self.assertTrue('No se encontró una solución para el puzzle: ' in str(context.exception))
    
if __name__ == '__main__':
    unittest.main()