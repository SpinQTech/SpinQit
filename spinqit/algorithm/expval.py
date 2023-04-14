# Copyright 2022 SpinQ Technology Co., Ltd.
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
from spinqit.qiskit.circuit import QuantumCircuit
from spinqit import Circuit
from spinqit.backend import BasicSimulatorBackend, BasicSimulatorConfig
from spinqit.backend.pytorch_backend import TorchSimulatorBackend, TorchSimulatorConfig
from spinqit.backend.qasm_backend import QasmBackend, QasmConfig
from spinqit.compiler import get_compiler
from spinqit.primitive.vector_encoding import amplitude_encoding
from spinqit.model.exceptions import InappropriateBackendError


class ExpvalCost:
    """
    With different backend to run the quantum circuit.

    Args:
        circuit (Circuit, file): The quantum circuit. Support class `Circuit` or `qasm` file.
        hamiltonian ([List, sparse.csr_matrix]): use generate_hamiltonian_matrix to construct the hamiltonian.
        backend_mode (str): `torch` or `spinq`. For simulator backend only support spinq or torch backend.
        grad_method (str): `backprop`, `param_shift`, `adjoint_differentiation`
    """

    def __init__(self,
                 circuit=None,
                 hamiltonian=None,
                 backend_mode='spinq',
                 grad_method=None,
                 shots=1024,
                 optimization_level=0,
                 *args,
                 **kwargs):

        # check and compile the circuit
        if circuit is None:
            params = None
            qubits_num = None
        else:
            if isinstance(circuit, Circuit):
                params = circuit.params
            else:
                params = None
            qubits_num = self.check_qnum(circuit)

        # init backend
        backend, config = self.check_backend_and_config(backend_mode, **kwargs)
        config.configure_shots(shots)

        self.backend_mode = backend_mode
        self.hamiltonian = hamiltonian
        self.circuit = circuit
        self.params = params
        self.qubits_num = qubits_num
        self.config = config
        self.optimization_level = optimization_level
        self.backend = backend
        self.grad_method = grad_method

    def __call__(self, new_params):
        self.update(new_params)
        res = self.forward()
        return res

    def update_backend_config(self, shots=None, qubits=None):
        """
        update the basic simulator backend configure shots or measure qubits
        """
        if isinstance(qubits, int):
            qubits = [qubits]
        if not isinstance(qubits, list):
            raise ValueError('The measure qubits should be int or list, '
                             f'but got {type(qubits)}')

        if shots is not None:
            self.config.configure_shots(shots)
        if qubits is not None:
            self.config.configure_measure_qubits(qubits)

    def execute(self, circuit, state=None, hamiltonian=None, params=None):
        circuit = self.decompose_state(state, circuit)
        compiler = self.check_circuit_get_compiler(circuit)
        ir = compiler.compile(circuit, self.optimization_level)
        if hamiltonian is None:
            return self.backend.execute(ir, self.config, state, params)
        return self.backend.expval(ir, self.config, hamiltonian, state, params)

    def execute_grads(self, circuit, state=None, hamiltonian=None, params=None):
        circ = self.decompose_state(state, circuit)
        compiler = self.check_circuit_get_compiler(circ)
        ir = compiler.compile(circ, self.optimization_level)
        loss, grads = self.backend.grads(ir,
                                         params,
                                         hamiltonian,
                                         self.config,
                                         self.grad_method,
                                         state)
        return loss, grads

    def forward(self, state=None, ):
        """
        Calculating the Hamiltonian expectation.
        """
        res = self.execute(self.circuit, state, self.hamiltonian, self.params)
        return getattr(res, 'states', res)

    def backward(self, state=None):
        """
        Return the grads when computing over the ir
        """

        loss, grads = self.execute_grads(self.circuit,
                                         state,
                                         self.hamiltonian,
                                         self.params,)
        return loss, grads

    def update(self, params):
        """
        Update the params for Parameterized Quantum Circuit
        """
        self.circuit.params = params
        self.params = params

    @staticmethod
    def check_circuit_get_compiler(circuit):
        ext_circuit = type(None)
        try:
            ext_qiskit = __import__('qiskit.circuit.quantumcircuit',fromlist=['None'])
            ext_circuit = getattr(ext_qiskit, 'QuantumCircuit')
        except Exception as e:
            pass
        if isinstance(circuit, Circuit):
            compiler = get_compiler('native')
        elif isinstance(circuit, (QuantumCircuit, ext_circuit)):
            compiler = get_compiler('qiskit')
        elif isinstance(circuit, str):
            compiler = get_compiler('qasm')
        else:
            raise ValueError(
                f'Expected circuit type `str`, `qiskit.QuantumCircuit`, `spinqit.Circuit`, '
                f'But got type {type(circuit)}.'
            )
        return compiler

    def check_qnum(self, circuit):
        ext_circuit = type(None)
        try:
            ext_qiskit = __import__('qiskit.circuit.quantumcircuit',fromlist=['None'])
            ext_circuit = getattr(ext_qiskit, 'QuantumCircuit')
        except Exception as e:
            pass
        if isinstance(circuit, Circuit):
            qnum = circuit.qubits_num
        elif isinstance(circuit, (QuantumCircuit, ext_circuit)):
            qnum = circuit.num_qubits
        elif isinstance(circuit, str):
            compiler = self.check_circuit_get_compiler(circuit)
            qnum = compiler.compile(circuit, 0).qnum
        else:
            raise ValueError(
                f'Expected circuit type `str`, `qiskit.QuantumCircuit`, `spinqit.Circuit`, '
                f'But got type {type(circuit)}.'
            )
        return qnum

    @staticmethod
    def check_backend_and_config(backend_mode, **kwargs):
        if backend_mode == 'spinq':
            backend = BasicSimulatorBackend()
            config = BasicSimulatorConfig()
        elif backend_mode == 'torch':
            backend = TorchSimulatorBackend()
            config = TorchSimulatorConfig()
        elif backend_mode[:4] == 'qasm':
            fn = kwargs.get('backend_fn', None)
            backend = QasmBackend(fn)
            config = QasmConfig()
        else:
            raise InappropriateBackendError(
                'Only `spinq` or `torch` or `qasm` simulator backend supports the state calculation.'
                f'But got `{backend_mode}` instead.')
        return backend, config

    def decompose_state(self, state, circ):
        if self.backend_mode != 'torch':
            if state is None:
                return circ

            def build_circ(_state):
                new_circ = Circuit()
                new_circ.allocateQubits(circ.qubits_num)
                ilist = amplitude_encoding(_state, circ.qubits)
                new_circ.extend(ilist)
                new_circ += circ
                return new_circ

            circ = build_circ(state)
        return circ
