import unittest

from sympy.logic.boolalg import Boolean

from spinqit.solver import SATSolver


class SatStringRegressionTest(unittest.TestCase):
    def test_string_expression_constructs_solver(self):
        solver = SATSolver('(a | b) & (~a | b)')

        self.assertIsInstance(solver.expr, Boolean)
        self.assertIsNotNone(solver.circuit)


if __name__ == '__main__':
    unittest.main()
