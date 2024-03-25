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
import matplotlib
from matplotlib import pyplot as plt
import numpy as np
from sklearn.datasets import make_circles

from spinqit import Circuit, generate_hamiltonian_matrix
from spinqit.interface.qlayer import to_qlayer
from spinqit.algorithm.loss import expval
from spinqit.primitive.vector_encoding import iqp_encoding
from spinqit.algorithm import QSVC

expval_list = []
for op_pauli in [[('ZI', 1)],
                 [('IZ', 1)],
                 [('XI', 1)],
                 [('IX', 1)],
                 [('YI', 1)],
                 [('IY', 1)]]:
    expval_list.append(expval(generate_hamiltonian_matrix(op_pauli)))

@to_qlayer(backend_mode='torch', measure=expval_list)
def build_circuit():
    circ = Circuit()
    qubits_num = 2
    qreg = circ.allocateQubits(qubits_num)
    x = circ.add_params(shape=(qubits_num,)) 
    ilist1 = iqp_encoding(x, qreg)
    circ.extend(ilist1)
    return circ

def visualize_decision_bound(clf):
    XX, YY = np.meshgrid(np.linspace(-1.2, 1.2, 10),
                         np.linspace(-1.2, 1.2, 10))

    Z = clf.decision_function(np.c_[XX.ravel(), YY.ravel()])
    Z_qke = Z.reshape(XX.shape)

    plt.contourf(XX, YY, Z_qke, vmin=-1., vmax=1., levels=20,
                 cmap=matplotlib.cm.coolwarm, alpha=1)
    plt.scatter(X_train[:, 0], X_train[:, 1],
                c=matplotlib.cm.coolwarm(np.array(y_train, dtype=np.float32)),
                edgecolor='black')
    plt.scatter(X_test[:, 0], X_test[:, 1], marker='v',
                c=matplotlib.cm.coolwarm(np.array(y_test, dtype=np.float32)),
                edgecolor='black')
    plt.contour(XX, YY, Z_qke, colors=['k', 'k', 'k'], linestyles=['--', '-', '--'],
                levels=[-.2, 0, .2])
    plt.show()


X_train, y_train = make_circles(10, noise=0.05, factor=0.2, random_state=0)
X_test, y_test = make_circles(10, noise=0.05, factor=0.2, random_state=1024)

qlayer = build_circuit()

# Either feature_map or qubit_num must be specified.
qsvc = QSVC(feature_map=qlayer, use_projected=True)
# qsvc = QSVC(use_projected=True, qubit_num=2, measure=expval_list, backend_mode='torch')
# qsvc = QSVC(use_projected=False, qubit_num=2, backend_mode='torch')

qsvc.fit(X_train, y_train)
predict_svm_pqk_train = qsvc.predict(X_train)
predict_svm_pqk_test = qsvc.predict(X_test)

accuracy_train = np.array(predict_svm_pqk_train == y_train, dtype=int).sum() / len(y_train)
accuracy_test = np.array(predict_svm_pqk_test == y_test, dtype=int).sum() / len(y_test)

fig, ax = plt.subplots(1, 2, figsize=[10, 4])
ax[0].scatter(X_train[:, 0], X_train[:, 1], marker='o',
              c=matplotlib.cm.coolwarm(np.array(predict_svm_pqk_train, dtype=np.float32)))
ax[0].set_title('Prediction on training set, accuracy={:.2f}'.format(accuracy_train))
ax[1].scatter(X_test[:, 0], X_test[:, 1], marker='v',
              c=matplotlib.cm.coolwarm(np.array(predict_svm_pqk_test, dtype=np.float32)))
ax[1].set_title('Prediction on testing set, accuracy={:.2f}'.format(accuracy_test))

visualize_decision_bound(qsvc.qsvm)