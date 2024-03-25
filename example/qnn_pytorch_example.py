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
import numpy as np
from spinqit import interface
import torch
import torch.optim as optim
from torch import nn

from spinqit import Circuit, Rz, Ry, CX, generate_hamiltonian_matrix, StateVector
from spinqit.interface import to_qlayer, TorchQuantumModule
from spinqit.algorithm.loss import expval

@to_qlayer(backend_mode='torch',
           grad_method='backprop',
           measure=expval(generate_hamiltonian_matrix([('ZI', 1)])), 
           interface='torch')
def build_circuit(state_shape, weights_shape, qubit_num, layer_num):
    circ = Circuit()
    state = circ.add_params(shape=state_shape) 
    weight = circ.add_params(shape=weights_shape) 
    q = circ.allocateQubits(qubit_num)
    circ << (StateVector, q, state[:])
    
    for i in range(layer_num):
        for j in range(qubit_num):
            circ << (Rz, q[j], weight[i][j][0])
            circ << (Ry, q[j], weight[i][j][1])
            circ << (Rz, q[j], weight[i][j][2])
        circ << (CX, q)
    return circ

def get_data(file_path):
    data = np.loadtxt(file_path)
    Xdata = data[:, 0:2]
    padding = 0.3 * np.ones((len(Xdata), 1))
    X_pad = np.c_[np.c_[Xdata, padding], np.zeros((len(Xdata), 1))]
    normalization = np.sqrt(np.sum(X_pad ** 2, -1))
    X_norm = (X_pad.T / normalization).T
    features = X_norm
    Y = data[:, -1]
    num_data = len(Y)
    n_train = int(0.75 * num_data)
    index = np.random.permutation(range(num_data))
    x_train = torch.tensor(features[index[:n_train]], requires_grad=False).to(torch.float32)
    y_train = torch.tensor(Y[index[:n_train]], requires_grad=False).to(torch.float32)
    x_val = torch.tensor(features[index[n_train:]], requires_grad=False).to(torch.float32)
    y_val = Y[index[n_train:]]
    return n_train, x_train, y_train, x_val, y_val,

def get_model(qubit_num, layer_num, bias=None):
    weight_shape = (layer_num, qubit_num, 3)
    state_shape = (2 ** qubit_num)
    quantum_layer = build_circuit(state_shape, weight_shape, qubit_num, layer_num)
    model = TorchQuantumModule(quantum_layer, weight_shape, bias)
    return model

def test_train(model, num_train, features_train, labels_train, features_val, labels_val):
    optimizer = optim.SGD(model.parameters(), lr=0.01, momentum=0.9, nesterov=True)
    loss_fn = nn.MSELoss()
    iter = 45
    batch_size = 10
    print('-----begin train----------')
    for i in range(iter):
        batch_index = np.random.randint(0, num_train, (batch_size,))
        feats_train_batch = features_train[batch_index]
        Y_train_batch = labels_train[batch_index]

        optimizer.zero_grad()
        pred = model(feats_train_batch)
        loss = loss_fn(pred, Y_train_batch)
        print(f'Loss : {loss.item()}')
        loss.backward()
        optimizer.step()
    print('---------begin predict--------------')
    total_error = 0
    with torch.no_grad():
        for k in range(len(features_val)):
            test_x = features_val[k].reshape(-1)
            pred = model(test_x)
            print(pred, labels_val[k])
            if abs(labels_val[k] - np.sign(pred.item())) > 1e-5:
                total_error = total_error + 1
    print(total_error)
    # assert np.allclose(total_error, 0)

if __name__ == '__main__':
    file_path = "resource/iris_classes_data.txt"
    qubit_num, layer_num = 2, 6
    seed = 1024
    np.random.seed(seed)
    torch.random.manual_seed(seed)
    bias = nn.Parameter(torch.tensor(0.0), requires_grad=True)
    model = get_model(qubit_num, layer_num, bias=bias)
    num_train, features_train, labels_train, features_val, labels_val, = get_data(file_path)
    test_train(model, num_train, features_train, labels_train, features_val, labels_val, )
