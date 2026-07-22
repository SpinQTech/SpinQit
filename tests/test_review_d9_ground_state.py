import contextlib
import io
import unittest

import numpy as np
from scipy import sparse

from spinqit.utils.function import get_ground_state_info


class GroundStateRegressionTest(unittest.TestCase):
    def test_ground_state_uses_algebraically_smallest_eigenvalue(self):
        eigenvalues = np.array([-5.0, -1.0, 0.25, 2.0])
        hamiltonian = sparse.diags(eigenvalues, format='csr')

        with contextlib.redirect_stdout(io.StringIO()):
            energy = get_ground_state_info(hamiltonian)

        self.assertAlmostEqual(energy, eigenvalues.min())


if __name__ == '__main__':
    unittest.main()
