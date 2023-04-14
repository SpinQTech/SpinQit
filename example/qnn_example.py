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
import torch
import torch.optim as optim
from torch import nn

from spinqit import Circuit, Parameter
from spinqit import Rz, Ry, CX
from spinqit.algorithm import ExpvalCost
from spinqit.algorithm import QuantumModel


def build_circuit(weights, qubit_num, layer_num):
    circ = Circuit(weights)
    q = circ.allocateQubits(qubit_num)

    for i in range(layer_num):
        circ << (Rz, q[0], lambda x, idx=i * layer_num + 0: x[idx])
        circ << (Ry, q[0], lambda x, idx=i * layer_num + 1: x[idx])
        circ << (Rz, q[0], lambda x, idx=i * layer_num + 2: x[idx])
        circ << (Rz, q[1], lambda x, idx=i * layer_num + 3: x[idx])
        circ << (Ry, q[1], lambda x, idx=i * layer_num + 4: x[idx])
        circ << (Rz, q[1], lambda x, idx=i * layer_num + 5: x[idx])
        circ << (CX, q)
    return circ


def get_data():
    file_path = "./resource/iris_classes_data.txt"
    data = np.loadtxt(file_path)
    Xdata = data[:, 0:2]
    padding = 0.3 * np.ones((len(Xdata), 1))
    X_pad = np.c_[np.c_[Xdata, padding], np.zeros((len(Xdata), 1))]
    normalization = np.sqrt(np.sum(X_pad ** 2, -1))
    X_norm = (X_pad.T / normalization).T

    features = X_norm

    Y = data[:, -1]
    np.random.seed(0)
    num_data = len(Y)
    n_train = int(0.75 * num_data)
    index = np.random.permutation(range(num_data))
    x_train = torch.tensor(features[index[:n_train]]).to(torch.float32)
    y_train = torch.tensor(Y[index[:n_train]]).to(torch.float32)
    x_val = torch.tensor(features[index[n_train:]]).to(torch.float32)
    y_val = Y[index[n_train:]]
    return n_train, x_train, y_train, x_val, y_val,


def get_model():
    qubit_num, layer_num = 2, 6

    class HybridModel(nn.Module):
        def __init__(self, n_qubit, n_layer, ):
            super(HybridModel, self).__init__()
            w = 0.01 * Parameter(np.random.randn(layer_num * qubit_num * 3), trainable=True)
            circuit = build_circuit(w, n_qubit, n_layer, )
            fn = ExpvalCost(circuit,
                            hamiltonian=([('Z', 1.0)]),
                            backend_mode='torch',
                            grad_method='backprop', )
            quantum_layer = QuantumModel(fn)
            quantum_layer.quantum_fn.update_backend_config(qubits=[0])
            b = torch.tensor(0.0)

            self.b = nn.Parameter(b, requires_grad=True)
            self.quantum_layer = quantum_layer

        def forward(self, state, ):
            return self.quantum_layer(state=state) + self.b

    model = HybridModel(qubit_num, layer_num)
    return model


def test_train():
    model = get_model()
    num_train, features_train, labels_train, features_val, labels_val, = get_data()
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


if __name__ == '__main__':
    seed = 1024
    np.random.seed(seed)
    test_train()