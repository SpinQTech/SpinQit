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
from math import pi
from qiskit import QuantumCircuit
from qiskit import execute
from qiskit import Aer #Qiskit 0.31.0
#from qiskit_aer import AerSimulator #Qiskit 0.34.0
from spinqit import H, CP, Circuit, get_compiler
from spinqit import get_qasm_backend, QasmConfig, QiskitQasmResult

# With Qiskit 0.31.0
def qiskit_fn(qasm, shots=1024, *args, **kwargs):
    qc = QuantumCircuit.from_qasm_str(qasm)
    simulator = Aer.get_backend('statevector_simulator')
    result = execute(qc, simulator, *args, **kwargs).result()
    print(result.get_statevector())
    qiskit_result = QiskitQasmResult()
    qiskit_result.set_result(result.get_statevector(), shots)
    return qiskit_result

# With Qiskit 0.34.0
#def qiskit_fn(qasm, shots=1024, *args, **kwargs):
#    qc = QuantumCircuit.from_qasm_str(qasm)
#    simulator = AerSimulator(method='statevector')
#    qc.save_state()
#    result = execute(qc, simulator, *args, **kwargs).result()
#    qiskit_result = QiskitQasmResult()
#    qiskit_result.set_result(result.get_statevector().data, shots)
#    return qiskit_result

compiler = get_compiler()

circuit = Circuit()
q = circuit.allocateQubits(2)
circuit << (H, q[0])
circuit << (CP, q, pi / 2)

exe = compiler.compile(circuit, 0)
config = QasmConfig()
engine = get_qasm_backend(qiskit_fn)
states = engine.execute(exe, config).states
print(states)
