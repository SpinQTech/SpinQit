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

import numpy as np

from spinqit import get_basic_simulator, BasicSimulatorConfig
from spinqit import generate_hamiltonian_matrix
from spinqit.algorithm.optimizer.adam import ADAM
from spinqit.algorithm.qaoa import QAOA

    
vcount = 4
E = [(0,1), (1,2), (2,3), (3,0)]

# Build Hamiltonian
ham = []
for (u,v) in E:
    pauli_str = ''
    for i in range(vcount):
        if i == u or i == v:
            pauli_str += 'Z'
        else:
            pauli_str += 'I'
    ham.append((pauli_str, 1.0))
print(ham)
# ham = [('ZZII', 1.0), ('IZZI', 1.0), ('IIZZ', 1.0), ('ZIIZ', 1.0), ('IZIZ', 1.0)]

qubit_num = vcount
depth = 4
Iter = 50
lr = 0.1

np.random.seed(1024)
optimizer = ADAM(maxiter=Iter, verbose=True, learning_rate=lr, )
ham_mat = generate_hamiltonian_matrix(ham)
qaoa = QAOA(qubit_num, depth, optimizer=optimizer, problem=ham_mat, )

loss = qaoa.run(mode='torch', grad_method='backprop')[-1]

backend = get_basic_simulator()
config = BasicSimulatorConfig()
config.configure_shots(1024)
result = qaoa.get_measurements(backend, config)
print(result.counts)