# Copyright 2023 SpinQ Technology Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
class MeasureOp:
    """
    MeasureOp is temporarily used for the QLayer measurement.

    Args:
        mtype: For now, we have `state`, `prob`, `count` and `expval`(For hamiltonian measurements)
        hamiltonian: Default to None, if `mtype` is `'expval'` the hamiltonian should be given.

    Example:
        from spinqit.loss.measurement import MeasureOp
        from spinqit import Circuit, generate_hamiltonian_matrix, Ry
        from spinqit.algorithm.qlayer import to_qlayer

        measure = MeasureOp('expval', hamiltonian=generate_hamiltonian_matrix([('X', 1.5)]))

        @to_qlayer(measure=measure)
        def build_circuit():
            circuit = Circuit()
            q = circuit.allocateQubits(1)
            circuit << (Ry, [q[0]], np.pi/2)
            return circuit

        qlayer = build_circuit()
        print(qlayer())
        # 1.5
    """
    def __init__(self, mtype, mqubits=None, shots=None, hamiltonian=None):
        self.mtype = mtype
        self.hamiltonian = hamiltonian
        self.mqubits = mqubits
        self.shots = shots


def expval(hamiltonian):
    """
    For `matrix` is True, It will generate the sparse matrix for hamiltonian.

    Example:
        hamiltonian = [('X', 1.5)]

        @to_qlayer(measure=expval(hamiltonian, True))
        def build_circuit():
            circuit = Circuit()
            q = circuit.allocateQubits(1)
            circuit << (Ry, [q[0]], np.pi/2)
            return circuit
    """
    return MeasureOp('expval', hamiltonian=hamiltonian)


def probs(mqubits=None):
    """
    Measure the probabilities of the quantum circuit result.

    Example:

        @to_qlayer(measure=probs(mqubits=[0,]))
        def build_circuit():
            circuit = Circuit()
            q = circuit.allocateQubits(2)
            circuit << (Ry, [q[0]], np.pi/2)
            return circuit

    """
    return MeasureOp('prob', mqubits=mqubits)


def counts(shots=None, mqubits=None):
    return MeasureOp('count', mqubits=mqubits, shots=shots)


def states():
    return MeasureOp('state')
