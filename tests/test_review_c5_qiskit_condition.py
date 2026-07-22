import unittest

from spinqit.compiler.translator.qiskit_to_spinq import qiskit_to_spinq
from spinqit.qiskit import QuantumCircuit


class QiskitConditionRegressionTest(unittest.TestCase):
    def test_condition_does_not_leak_to_following_instruction(self):
        source = QuantumCircuit(1, 1)
        source.x(0).c_if(source.cregs[0], 1)
        source.h(0)

        translated = qiskit_to_spinq(source)

        self.assertIsNotNone(translated.instructions[0].condition)
        self.assertIsNone(translated.instructions[1].condition)


if __name__ == '__main__':
    unittest.main()
