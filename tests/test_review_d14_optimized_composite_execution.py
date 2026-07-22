import json
import subprocess
import sys
import tempfile
import textwrap
import unittest


class OptimizedCompositeExecutionRegressionTests(unittest.TestCase):
    def test_optimized_composite_gate_executes_without_native_crash(self):
        for level in (1, 2, 3):
            with self.subTest(level=level):
                script = textwrap.dedent(f'''
                    import json
                    import os

                    from spinqit import BasicSimulatorConfig, Circuit, H, X, get_basic_simulator, get_compiler
                    from spinqit.model import ControlledGate

                    circuit = Circuit()
                    qubits = circuit.allocateQubits(2)
                    circuit << (X, qubits[0])
                    circuit << (ControlledGate(H), qubits)
                    ir = get_compiler('native').compile(circuit, {level})
                    result = get_basic_simulator().execute(ir, BasicSimulatorConfig())
                    print(json.dumps(result.probabilities), flush=True)
                    os._exit(0)
                ''')
                completed = subprocess.run(
                    [sys.executable, '-c', script],
                    cwd=tempfile.gettempdir(),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                self.assertEqual(completed.returncode, 0, completed.stderr)
                probabilities = json.loads(completed.stdout)
                self.assertAlmostEqual(probabilities['10'], 0.5)
                self.assertAlmostEqual(probabilities['11'], 0.5)


if __name__ == '__main__':
    unittest.main()
