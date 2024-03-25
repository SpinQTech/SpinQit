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
from typing import Callable
import numpy as np
from sklearn import svm
from spinqit import Circuit, iqp_encoding, invert_instruction
from spinqit.interface import to_qlayer
from spinqit.algorithm.loss import MeasureOp, probs

class QSVC():
    '''
    Either feature_map or qubit_number must be specified.
    '''
    def __init__(self, feature_map: Callable = None, use_projected: bool = False, qubit_num: int = None, measure: MeasureOp = probs(), backend_mode: str = 'spinq', **kwargs):
        if feature_map is not None:
            self.feature_map = feature_map
            if use_projected:
                self.__qsvm = svm.SVC(kernel=self.projected_quantum_kernel)
            else:
                self.__qsvm = svm.SVC(kernel=self.quantum_kernel)
        else:
            if qubit_num is None:
                raise ValueError('The qubit_num argument must be specified when the feature_map argument is not provided.')
            self.qubit_num = qubit_num
            qlayer = to_qlayer(backend_mode=backend_mode, measure = measure, **kwargs)
            if use_projected:
                self.feature_map = qlayer(self.build_projected_circuit)()
                self.__qsvm = svm.SVC(kernel=self.projected_quantum_kernel)
            else:
                self.feature_map = qlayer(self.build_circuit)()
                self.__qsvm = svm.SVC(kernel=self.quantum_kernel)

    @property
    def qsvm(self):
        return self.__qsvm

    def build_projected_circuit(self):
        circ = Circuit()
        qreg = circ.allocateQubits(self.qubit_num)
        x = circ.add_params(shape=(self.qubit_num,)) 
        ilist1 = iqp_encoding(x, qreg)
        circ.extend(ilist1)
        return circ

    def projected_kernel_estimator(self, x1, x2):
        p_feature_vector_1 = np.array(self.feature_map(x1))
        p_feature_vector_2 = np.array(self.feature_map(x2))
        return np.exp(-((p_feature_vector_1 - p_feature_vector_2) ** 2).sum())

    def projected_quantum_kernel(self, X1, X2):
        return np.array([[self.projected_kernel_estimator(x1, x2) for x2 in X2] for x1 in X1])

    def build_circuit(self):
        circ = Circuit()
        qreg = circ.allocateQubits(self.qubit_num)
        x1 = circ.add_params(shape=(self.qubit_num,))
        x2 = circ.add_params(shape=(self.qubit_num,)) 
        ilist1 = iqp_encoding(x1, qreg)
        circ.extend(ilist1)
        ilist2 = iqp_encoding(x2, qreg)
        ilist2_inv = []
        for inst in ilist2[::-1]:
            ilist2_inv.append(invert_instruction(inst))
        circ.extend(ilist2_inv)
        return circ

    def quantum_kernel_estimator(self, x1, x2):
        probabilities = self.feature_map(x1, x2)     
        return probabilities[0]

    def quantum_kernel(self, X1, X2):
        return np.array([[self.quantum_kernel_estimator(x1, x2) for x2 in X2] for x1 in X1])

    def fit(self, X_train, y_train):
        self.__qsvm.fit(X_train, y_train)

    def predict(self, X_test):
        return self.__qsvm.predict(X_test)
