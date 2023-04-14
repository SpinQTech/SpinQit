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

# Test the HHL circuit metioned in Qiskit Tutorial https://qiskit.org/textbook/ch-applications/hhl_tutorial.html
#
# Abstract Graph
#
#       ┌────────────┐┌──────┐        ┌─────────┐
# q0_0: ┤0           ├┤3     ├────────┤3        ├
#       │  circuit-8 ││      │        │         │
# q0_1: ┤1           ├┤4     ├────────┤4        ├
#       └────────────┘│      │┌──────┐│         │
# q1_0: ──────────────┤0     ├┤2     ├┤0        ├
#                     │  QPE ││      ││  QPE_dg │
# q1_1: ──────────────┤1     ├┤1     ├┤1        ├
#                     │      ││      ││         │
# q1_2: ──────────────┤2     ├┤0 1/x ├┤2        ├
#                     │      ││      ││         │
# a1_0: ──────────────┤5     ├┤      ├┤5        ├
#                     └──────┘│      │└─────────┘
# q2_0: ──────────────────────┤3     ├───────────
#                             └──────┘
# Expect to have peak at '0100001' (around 336), then a lower peak at '1100001' (around 288), then a lower peak at '1000001' (around 190), then a lower peak at '1100000' (around 120)
#
import numpy as np
from spinqit.qiskit import QuantumCircuit
from qiskit.algorithms.linear_solvers.hhl import HHL
from qiskit.algorithms.linear_solvers.matrices import TridiagonalToeplitz
from qiskit.algorithms.linear_solvers.observables import MatrixFunctional
from spinqit import get_basic_simulator, get_compiler, BasicSimulatorConfig

matrix = TridiagonalToeplitz(2, 1, 1 / 3, trotter_steps=2)
right_hand_side = [1.0, -2.1, 3.2, -4.3]
observable = MatrixFunctional(1, 1 / 2)
rhs = right_hand_side / np.linalg.norm(right_hand_side)

# Initial state circuit
num_qubits = matrix.num_state_qubits
qc = QuantumCircuit(num_qubits)
qc.isometry(rhs, list(range(num_qubits)), None)

hhl = HHL()
hhl_circ = hhl.construct_circuit(matrix, rhs)
# print(hhl_circ)

engine = get_basic_simulator()
comp = get_compiler("qiskit")
exe = comp.compile(hhl_circ, 0)
config = BasicSimulatorConfig()
config.configure_shots(1024)

result = engine.execute(exe, config)
print("======= SpinQit simulate result =======")
print(result.counts)


# from qiskit import Aer, transpile, ClassicalRegister
# hhl_circ.measure_all()
# aer_sim = Aer.get_backend('aer_simulator')
# t_hhl = transpile(hhl_circ, aer_sim)
# # print(t_qpe)
# result = aer_sim.run(t_hhl).result()

# print("======= IBM aer simulate result =======")
# print(result.get_counts())

# print("======= IBM solve result =======")
# solution = hhl.solve(matrix, qc, observable)
# print(solution)
# print(solution.state)


