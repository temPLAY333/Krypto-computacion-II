import random
from collections import Counter

class KryptoLogic:
    
    @staticmethod
    def suma(a, b):
        return a + b
    
    @staticmethod
    def resta(a, b):
        if a > b:
            return a - b
        else:
            return b - a
    
    @staticmethod
    def multiplicacion(a, b):
        return a * b
    
    @staticmethod
    def division(a, b):
        if b == 0 or a == 0:
            return None
        if a % b == 0:
            return a / b
        elif b % a == 0:
            return b / a
        return None
    
    operations = [suma, resta, multiplicacion, division]

    @staticmethod
    def generar_puzzle() -> list:
        """Genera un puzzle aleatorio con cartas de la baraja española"""
        baraja = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] * 4  # Baraja española con 4 palos
        puzzle = []
        while len(puzzle) < 4:
            carta = random.choice(baraja)
            puzzle.append(carta)
            baraja.remove(carta)
        
        answers = list(range(1, 13))
        random.shuffle(answers)
        for answer in answers:
            puzzle.append(answer)
            if KryptoLogic.solucionar_puzzle(puzzle):
                return puzzle
            puzzle.pop()
        
        raise Exception("No se encontró una solución para el puzzle: " + str(puzzle))

    @staticmethod
    def solucionar_puzzle(puzzle):
        a, b, c, d = puzzle[0], puzzle[1], puzzle[2], puzzle[3]
        answer = puzzle[4]
        combinaciones_A = [[[a, b], [c, d]], [[a, c], [b, d]], [[a, d], [b, c]], [[b, c], [a, d]], [[b, d], [a, c]], [[c, d], [a, b]]]
        combinaciones_B = [[[[a, b], c], d], [[[a, c], b], d], [[[a, d], b], c], [[[b, c], a], d], [[[b, d], a], c], [[[c, d], a], b]]
        productos_alfa = set()
        productos_beta = set()

        for combinacion in combinaciones_A:
            for op in KryptoLogic.operations:
                productos_alfa.add(op(combinacion[0][0], combinacion[0][1]))
                productos_beta.add(op(combinacion[1][0], combinacion[1][1]))
            
            productos_alfa.discard(None)
            productos_beta.discard(None)
            
            for alfa in productos_alfa:
                for beta in productos_beta:
                    for op in KryptoLogic.operations:
                        if op(alfa, beta) == answer:
                            return True
            
            productos_beta.clear()
            productos_alfa.clear()
        
        for combinacion in combinaciones_B:
            for op in KryptoLogic.operations:
                productos_alfa.add(op(combinacion[0][0][0], combinacion[0][0][1]))

            productos_alfa.discard(None)
            
            for alfa in productos_alfa:
                for op in KryptoLogic.operations:
                    productos_beta.add(op(alfa, combinacion[0][1]))
            
            productos_beta.discard(None)
            
            for beta in productos_beta:
                for op in KryptoLogic.operations:
                    if op(beta, combinacion[1]) == answer:
                        return True
            
            productos_beta.clear()
            
            for alfa in productos_alfa:
                for op in KryptoLogic.operations:
                    productos_beta.add(op(alfa, combinacion[1]))

            productos_beta.discard(None)
            
            for beta in productos_beta:
                for op in KryptoLogic.operations:
                    if op(beta, combinacion[0][1]) == answer:
                        return True

            productos_beta.clear()
            productos_alfa.clear()
        
        return False

    @staticmethod
    def puzzles_sin_solucion():
        puzzles_totales = []
        puzzles_Irresolubles = Counter()

        for a in range(1, 13):
            for b in range(1, 13):
                for c in range(1, 13):
                    for d in range(1, 13):
                        puzzle_set = Counter([a, b, c, d])
                        if puzzle_set in puzzles_totales:
                            continue
                        puzzles_totales.append(puzzle_set)
                        puzzle = [a, b, c, d]
                        for e in range(1, 13):
                            puzzle.append(e)
                            if not KryptoLogic.solucionar_puzzle(puzzle):
                                puzzles_Irresolubles.update([tuple(puzzle[:4])])
                            puzzle.pop()
        
        #print("Cantidad de puzzles con la misma cantidad de repeticiones:")
        #print(Counter({1: 284, 2: 235, 3: 149, 4: 92, 5: 26, 6: 11, 8: 8, 7: 4})) #Total: 1857 puzzles sin solucion

        #print("Puzzles sin solución:")
        #print(puzzles_Irresolubles)

    @staticmethod
    def verify_solution(solution, answer):
        """Verifica si la solución es correcta"""
        list = KryptoLogic.convertir(solution)
        X = int(list[0])
        Y = int(list[2])
        Z = int(list[4])
        W = int(list[6])
        op1 = list[1]
        op2 = list[3]
        op3 = list[5]

        # Verficar para el patron Combinacion A (X op1 Y) op2 (Z op3 W)
        if KryptoLogic.apply_operation(KryptoLogic.apply_operation(X, op1, Y), op2, KryptoLogic.apply_operation(Z, op3, W)) == answer:
            return True
        
        # Verficar para el patron Combinacion B ((X op1 Y) op2 Z) op3 W
        elif KryptoLogic.apply_operation(KryptoLogic.apply_operation(KryptoLogic.apply_operation(X, op1, Y), op2, Z), op3, W) == answer:
            return True
        
        else:
            return False
        
    @staticmethod
    def convertir(string):
        """Convierte la cadena de texto en una lista de operaciones"""
        list = [i for i in string if i != " "]
        i = 0
        while i < len(list):
            if i + 1 < len(list) and list[i].isdigit() and list[i + 1].isdigit():
                list[i] = list[i] + list[i + 1]
                list.pop(i + 1)
            i += 1
        
        return list
    
    @staticmethod
    def apply_operation(a, op, b):
        if op == "+":
            return KryptoLogic.suma(a, b)
        elif op == "-":
            return KryptoLogic.resta(a, b)
        elif op == "*" or op == "." or op == "x" or op == "X":
            return KryptoLogic.multiplicacion(a, b)
        elif op == "/" or op == "÷" or op == ":":
            return KryptoLogic.division(a, b)
        else:
            return None
    
    
if __name__ == "__main__":
    KryptoLogic.puzzles_sin_solucion()
