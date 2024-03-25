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
import tensorflow as tf
from tensorflow.keras import Sequential, losses, optimizers

from spinqit import Circuit, Rz, Ry, CX, generate_hamiltonian_matrix, StateVector
from spinqit.interface import to_qlayer
from spinqit.interface.tf_interface import QuantumLayer
from spinqit.algorithm.loss import expval

@to_qlayer(backend_mode='torch',
           grad_method='backprop',
           measure=expval(generate_hamiltonian_matrix([('ZI', 1)])))
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
    np.random.seed(0)
    num_data = len(Y)
    n_train = int(0.75 * num_data)
    index = np.random.permutation(range(num_data))

    x_train = tf.Variable(features[index[:n_train]], trainable=False)
    y_train = tf.Variable(Y[index[:n_train]], trainable=False)
    x_val = tf.Variable(features[index[n_train:]], trainable=False)

    y_val = Y[index[n_train:]]
    return n_train, x_train, y_train, x_val, y_val,

def get_model(qubit_num, layer_num, bias=None):
    weight_shape = (layer_num, qubit_num, 3)
    state_shape = (2 ** qubit_num)
    qlayer = build_circuit(state_shape, weight_shape, qubit_num, layer_num)
    
    ql = QuantumLayer(qlayer, weight_shape, bias)
    model = Sequential()
    model.add(ql)
    return model

def test_train(model, num_train, features_train, labels_train, features_val, labels_val):
    optimizer = optimizers.SGD(learning_rate=0.01, momentum=0.9, nesterov=True)
    loss_fn = losses.MeanSquaredError()
    iter = 55
    batch_size = 10
    print('-----begin train----------')
    for i in range(iter):
        batch_index = np.random.randint(0, num_train, (batch_size,))
        feats_train_batch = tf.gather(features_train, batch_index) 
        Y_train_batch = tf.gather(labels_train, batch_index)
        with tf.GradientTape() as tape:
            pred = model(feats_train_batch, training=True)
            loss = loss_fn(Y_train_batch, pred)
            gradients = tape.gradient(loss, model.trainable_variables)
            optimizer.apply_gradients(zip(gradients, model.trainable_variables))
            print(f'Loss : {loss.numpy()}')

    print('---------begin predict--------------')
    total_error = 0
    for k in range(features_val.shape[0]):
        test_x = features_val[k]
        pred = model(test_x)
        print(pred, labels_val[k])
        if abs(labels_val[k] - np.sign(pred.numpy())) > 1e-5:
            total_error = total_error + 1
            
    print(total_error)
    assert np.allclose(total_error, 0)


if __name__ == '__main__':
    file_path = "resource/iris_classes_data.txt"
    qubit_num, layer_num = 2, 6
    seed = 1024
    np.random.seed(seed)
    tf.random.set_seed(seed)
    bias = tf.Variable(0.0, trainable=True)
    model = get_model(qubit_num, layer_num, bias=bias)
    
    num_train, features_train, labels_train, features_val, labels_val, = get_data(file_path)
    test_train(model, num_train, features_train, labels_train, features_val, labels_val)