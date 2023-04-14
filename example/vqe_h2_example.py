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
from spinqit import generate_hamiltonian_matrix
from spinqit import Circuit, Parameter, Rx, Rz, CX
from spinqit.algorithm import VQE
from spinqit.algorithm.optimizer import TorchOptimizer

ham = [("IIII", -0.04207255194749729), 
       ("ZIII", 0.17771358229095718), 
       ("IZII", 0.17771358229095718),
       ("IIZI", -0.24274501260934922), 
       ("IIIZ", -0.24274501260934922), 
       ("ZIZI", 0.1229333044929736), 
       ("IZIZ", 0.1229333044929736),
       ("ZIIZ", 0.16768338855598627), 
       ("IZZI", 0.16768338855598627), 
       ("ZZII", 0.1705975927683594), 
       ("IIZZ", 0.17627661394176986), 
       ("YYXX", -0.044750084063012674), 
       ("XXYY", -0.044750084063012674),
       ("YXXY", 0.044750084063012674),
       ("XYYX", 0.044750084063012674)]

depth = 1
qubit_num = len(ham[0][0])
Iter = 100
lr = 0.1
seed = 1024
np.random.seed(seed)

params = Parameter(np.random.uniform(0, 2 * np.pi, 3 * qubit_num * depth),
                               trainable=True)
ansatz = Circuit(params)
qreg = ansatz.allocateQubits(qubit_num)
for d in range(depth):
    for q in range(qubit_num):
        ansatz << (Rx, qreg[q], lambda x, idx=3 * qubit_num * d + 3 * q: x[idx])
        ansatz << (Rz, qreg[q], lambda x, idx=3 * qubit_num * d + 3 * q + 1: x[idx])
        ansatz << (Rx, qreg[q], lambda x, idx=3 * qubit_num * d + 3 * q + 2: x[idx])
    
    for q in range(qubit_num - 1):
        ansatz.append(CX, [qreg[q], qreg[q + 1]])
    ansatz.append(CX, [qreg[qubit_num - 1], qreg[0]])

optimizer = TorchOptimizer(maxiter=Iter, verbose=False, learning_rate=lr)
ham_mat = generate_hamiltonian_matrix(ham)
vqe = VQE(qubit_num, depth, ham_mat, ansatz, optimizer=optimizer)
# loss_list = vqe.run(mode='torch', grad_method='backprop')
# loss_list = vqe.run(mode='spinq', grad_method='param_shift')
loss_list = vqe.run(mode='spinq', grad_method='adjoint_differentiation')
print(loss_list)

