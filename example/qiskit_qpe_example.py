# Copyright 2021 SpinQ Technology Co., Ltd.
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

from spinqit import get_basic_simulator, get_compiler, BasicSimulatorConfig
from qiskit import QuantumCircuit
from qiskit.circuit.library import PhaseEstimation
from math import pi

unitary = QuantumCircuit(2)
unitary.p(pi/4, 0)
unitary.p(pi/2, 1)

qpe_alg = PhaseEstimation(3, unitary)
pre = QuantumCircuit(5)
pre.x(3)
pre.x(4)
circ = pre.compose(qpe_alg)
# print(circ.decompose().decompose())

engine = get_basic_simulator()
comp = get_compiler("qiskit")
exe = comp.compile(circ, 0)

config = BasicSimulatorConfig()
config.configure_shots(1024)
config.configure_measure_qubits(list(range(3)))
result = engine.execute(exe, config)
print("======= SpinQit simulate result =======")
print(result.counts)

from qiskit import Aer, transpile, ClassicalRegister
circ.barrier()
cr_state = ClassicalRegister(3, "c")
circ.add_register(cr_state)
for n in range(3):
    circ.measure(n,n)
aer_sim = Aer.get_backend('aer_simulator')
t_qpe = transpile(circ, aer_sim)
result = aer_sim.run(t_qpe).result()

print("======= IBM aer simulate result =======")
print(result.get_counts())


