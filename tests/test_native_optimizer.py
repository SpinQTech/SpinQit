from copy import deepcopy
import unittest

import numpy as np

from spinqit import (
    BasicSimulatorConfig,
    Circuit,
    CX,
    CZ,
    H,
    Rx,
    Ry,
    Rz,
    SWAP,
    X,
    Y,
    Z,
    get_basic_simulator,
    get_compiler,
)
from spinqit.compiler.ir import NodeType


SINGLE_QUBIT_GATES = (H, X, Y, Z, Rx, Ry, Rz)
ROTATION_GATES = (Rx, Ry, Rz)


def random_circuit(seed, width=2, depth=16):
    rng = np.random.default_rng(seed)
    circuit = Circuit(f'random-w{width}-d{depth}-s{seed}')
    circuit.allocateQubits(width)
    for _ in range(depth):
        if rng.random() < 0.35:
            first, second = map(int, rng.choice(width, size=2, replace=False))
            circuit << (CZ, (first, second))
            continue
        gate = SINGLE_QUBIT_GATES[int(rng.integers(len(SINGLE_QUBIT_GATES)))]
        qubit = int(rng.integers(width))
        if gate in ROTATION_GATES:
            circuit << (gate, qubit, float(rng.uniform(-2 * np.pi, 2 * np.pi)))
        else:
            circuit << (gate, qubit)
    return circuit


class RemoveNodesTests(unittest.TestCase):
    @staticmethod
    def operation_nodes(ir):
        return [v.index for v in ir.dag.vs if v['type'] == NodeType.op.value]

    @staticmethod
    def qubit_edge_exists(ir, source, target, qubit):
        return any(edge.source == source and edge.target == target and edge['qubit'] == qubit
                   for edge in ir.dag.es)

    def test_reconnects_contiguous_removed_segment(self):
        circuit = Circuit('contiguous-removal')
        circuit.allocateQubits(1)
        circuit << (X, 0)
        circuit << (H, 0)
        circuit << (H, 0)
        circuit << (Y, 0)
        ir = get_compiler('native').compile(circuit, 0)
        x_node, first_h, second_h, y_node = self.operation_nodes(ir)

        ir.remove_nodes([first_h, second_h], True)

        x_node, y_node = self.operation_nodes(ir)
        self.assertTrue(self.qubit_edge_exists(ir, x_node, y_node, 0))

    def test_reconnects_separate_removed_segments(self):
        circuit = Circuit('separate-removal')
        circuit.allocateQubits(1)
        circuit << (X, 0)
        circuit << (H, 0)
        circuit << (X, 0)
        circuit << (Y, 0)
        ir = get_compiler('native').compile(circuit, 0)
        first_x, h_node, second_x, y_node = self.operation_nodes(ir)

        ir.remove_nodes([first_x, second_x], True)

        h_node, y_node = self.operation_nodes(ir)
        init_node = ir.dag.predecessors(h_node)[0]
        self.assertTrue(self.qubit_edge_exists(ir, init_node, h_node, 0))
        self.assertTrue(self.qubit_edge_exists(ir, h_node, y_node, 0))


class NativeOptimizerRegressionTests(unittest.TestCase):
    @staticmethod
    def simulate(ir):
        config = BasicSimulatorConfig()
        config.configure_shots(1)
        state = np.asarray(get_basic_simulator().execute(deepcopy(ir), config).states,
                           dtype=complex)
        return state / np.linalg.norm(state)

    def test_optimization_levels_preserve_reproduction_states(self):
        compiler = get_compiler('native')
        for seed in (2003, 2014):
            circuit = random_circuit(seed)
            reference = self.simulate(compiler.compile(circuit, 0))
            for level in (1, 2, 3):
                with self.subTest(seed=seed, level=level):
                    candidate = self.simulate(compiler.compile(circuit, level))
                    fidelity = float(abs(np.vdot(reference, candidate)) ** 2)
                    self.assertGreaterEqual(fidelity, 1.0 - 1e-9)

    def test_constant_state_optimization_preserves_cz_on_minus_state(self):
        circuit = Circuit('cz-minus-state')
        circuit.allocateQubits(2)
        circuit << (X, 0)
        circuit << (X, 1)
        circuit << (H, 1)
        circuit << (CZ, (0, 1))
        compiler = get_compiler('native')

        reference = self.simulate(compiler.compile(circuit, 0))
        candidate = self.simulate(compiler.compile(circuit, 3))
        fidelity = float(abs(np.vdot(reference, candidate)) ** 2)

        self.assertGreaterEqual(fidelity, 1.0 - 1e-9)

    def test_optimization_levels_preserve_deterministic_sweep(self):
        compiler = get_compiler('native')
        for width in (2, 3, 4, 6):
            for seed in range(2000, 2020):
                circuit = random_circuit(seed, width=width)
                reference = self.simulate(compiler.compile(circuit, 0))
                for level in (1, 2, 3):
                    with self.subTest(width=width, seed=seed, level=level):
                        candidate = self.simulate(compiler.compile(circuit, level))
                        fidelity = float(abs(np.vdot(reference, candidate)) ** 2)
                        self.assertGreaterEqual(fidelity, 1.0 - 1e-8)

    def test_two_qubit_collapse_does_not_reject_valid_circuit(self):
        circuit = Circuit('two-qubit-collapse')
        circuit.allocateQubits(2)
        for gate, qubits in (
            (CZ, [0, 1]),
            (CX, [1, 0]),
            (CX, [1, 0]),
            (SWAP, [1, 0]),
            (CZ, [0, 1]),
            (SWAP, [0, 1]),
            (SWAP, [0, 1]),
        ):
            circuit << (gate, qubits)

        compiler = get_compiler('native')
        reference = self.simulate(compiler.compile(circuit, 0))
        for level in (2, 3):
            with self.subTest(level=level):
                candidate = self.simulate(compiler.compile(circuit, level))
                fidelity = float(abs(np.vdot(reference, candidate)) ** 2)
                self.assertGreaterEqual(fidelity, 1.0 - 1e-9)


if __name__ == '__main__':
    unittest.main()
