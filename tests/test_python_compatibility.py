import json
import subprocess
import sys
import tempfile
import textwrap
import unittest


class PythonCompatibilityTest(unittest.TestCase):
    def test_graph_is_exported_through_public_igraph_api(self):
        script = textwrap.dedent(
            """
            import json

            from igraph import Graph
            from spinqit.backend.backend_util import get_graph_data

            graph = Graph(3, [(0, 1), (1, 2)], directed=True)
            graph["qnum"] = 2
            graph.vs["kind"] = ["input", "gate", "output"]
            graph.es["qubit"] = [0, 1]
            print(json.dumps(get_graph_data(graph)))
            """
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=tempfile.gettempdir(),
            capture_output=True,
            text=True,
            timeout=180,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        data = json.loads(completed.stdout)
        self.assertTrue(data["directed"])
        self.assertEqual(data["vertex_count"], 3)
        self.assertEqual(data["edges"], [[0, 1], [1, 2]])
        self.assertEqual(data["graph_attrs"], {"qnum": 2})
        self.assertEqual(data["vertex_attrs"]["kind"], ["input", "gate", "output"])
        self.assertEqual(data["edge_attrs"]["qubit"], [0, 1])

    def test_basic_simulator_does_not_depend_on_igraph_binary_layout(self):
        script = textwrap.dedent(
            """
            import json
            from spinqit import BasicSimulatorConfig, Circuit, H, get_basic_simulator, get_compiler

            circuit = Circuit("python-compatibility")
            qubit = circuit.allocateQubits(1)[0]
            circuit << (H, qubit)

            result = get_basic_simulator().execute(
                get_compiler("native").compile(circuit, 0),
                BasicSimulatorConfig(),
            )
            print(json.dumps(result.probabilities), flush=True)
            """
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=tempfile.gettempdir(),
            capture_output=True,
            text=True,
            timeout=180,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        probabilities = json.loads(completed.stdout)
        self.assertAlmostEqual(probabilities["0"], 0.5)
        self.assertAlmostEqual(probabilities["1"], 0.5)

    def test_autograd_crosses_the_native_simulator_boundary(self):
        script = textwrap.dedent(
            """
            import json

            from autograd import grad
            from spinqit import Circuit, Parameter, Ry, generate_hamiltonian_matrix
            from spinqit.algorithm.loss import expval
            from spinqit.interface.qlayer import QLayer

            circuit = Circuit("autograd-compatibility")
            qubit = circuit.allocateQubits(1)[0]
            theta = circuit.add_params(shape=(1,))
            circuit << (Ry, qubit, theta[0])
            layer = QLayer(
                circuit,
                measure=expval(generate_hamiltonian_matrix([("Z", 1.0)])),
                backend_mode="spinq",
                grad_method="adjoint_differentiation",
            )

            params = Parameter([0.4])
            value = float(layer(params))
            derivative = float(grad(lambda values: layer(values))(params)[0][0])
            print(json.dumps({"value": value, "derivative": derivative}))
            """
        )
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=tempfile.gettempdir(),
            capture_output=True,
            text=True,
            timeout=180,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertAlmostEqual(result["value"], 0.9210609940028851)
        self.assertAlmostEqual(result["derivative"], -0.3894183423086505)


if __name__ == "__main__":
    unittest.main()
