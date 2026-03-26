# Copyright 2024 SpinQ Technology Co., Ltd.
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
from sklearn import KNeighborsClassifier
from ..backend import check_backend_and_config
from ..compiler import get_compiler
from ..model import Circuit
from ..primitive import SwapTest

class QKNN():
    def __init__(self, backend_mode: str = 'spinq', **kwargs):
        self.backend_mode = backend_mode
        self.backend, self.config = check_backend_and_config(backend_mode, **kwargs)

    def swap_test(self, state1, state2):
        circ = Circuit()
        qubit_num = int(np.log2(len(state1)))
        qreg = circ.allocateQubits(1+2*qubit_num)
        st_insts = SwapTest(state1, state2, qreg[0], qreg[1:qubit_num], qreg[qubit_num+1:])
        circ.extend(st_insts)
        compiler = get_compiler()
        exe = compiler.compile(circ, 0)
        self.config.configure_measure_qubits([0])
        result = self.backend.execute(exe, self.config)
        prob0 = result.probabilities['0']
        return 1 - np.sqrt(prob0 * 2 - 1)

    def predict(self, train_x, train_y, test_x):
        knn = KNeighborsClassifier(algorithm='auto', metric=self.swap_test, n_neighbors=1, p=2, weights='uniform')
        knn.fit(train_x, train_y)
        return knn.predict(test_x)