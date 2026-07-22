import unittest

from spinqit import generate_hamiltonian_matrix
from spinqit.algorithm import QAOA


class QaoaNoncommutingProblemRegressionTest(unittest.TestCase):
    def test_default_problem_ansatz_rejects_order_dependent_term_product(self):
        terms = [('Z', 1.0), ('Y', 1.0)]

        for problem in (terms, generate_hamiltonian_matrix(terms)):
            with self.subTest(problem_type=type(problem).__name__):
                with self.assertRaisesRegex(ValueError, 'commuting Pauli terms'):
                    QAOA(problem, object(), depth=1)


if __name__ == '__main__':
    unittest.main()
