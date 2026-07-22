import json
import subprocess
import sys
import tempfile
import textwrap
import unittest


class BasicCountsRegressionTest(unittest.TestCase):
    def test_low_probability_distribution_still_allocates_all_shots(self):
        script = textwrap.dedent('''
            import json
            import os

            from spinqit import BasicSimulatorConfig, Circuit, H, get_basic_simulator, get_compiler

            circuit = Circuit('broad-distribution')
            qubits = circuit.allocateQubits(3)
            for qubit in qubits:
                circuit << (H, qubit)

            config = BasicSimulatorConfig()
            config.configure_shots(1)
            result = get_basic_simulator().execute(
                get_compiler('native').compile(circuit, 0), config
            )
            counts = result.counts
            print(json.dumps({
                'count_total': sum(counts.values()),
                'probability_total': sum(result.probabilities.values()),
            }), flush=True)
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
        payload = json.loads(completed.stdout)
        self.assertAlmostEqual(payload['probability_total'], 1.0)
        self.assertEqual(payload['count_total'], 1)


if __name__ == '__main__':
    unittest.main()
