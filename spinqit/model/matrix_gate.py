# Copyright 2021-2022 SpinQ Technology Co., Ltd.
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
from typing import Union, Callable, List
from .basic_gate import Gate, GateBuilder
from .controlled_gate import ControlledGate
import numpy as np

class MatrixGate(Gate):
    def __init__(self, label: str, qubit_num: int) -> None:
        super().__init__(label, qubit_num)
        
class MatrixGateBuilder(GateBuilder):
    def __init__(self, mat: Union[Callable, np.ndarray]) -> None:
        if isinstance(mat, np.ndarray):
            if not np.allclose(np.eye(len(mat)), mat.dot(mat.T.conj())):
                raise ValueError("The gate matrix must be unitary.")
            qubit_num = int(np.log2(mat.shape[0]))
        else:
            params = [0] * mat.__code__.co_argcount
            zmat = mat(params)
            if not np.allclose(np.eye(len(zmat)), zmat.dot(zmat.T.conj())):
                raise ValueError("The gate matrix must be unitary.")
            qubit_num = int(np.log2(zmat.shape[0]))
        
        super().__init__(qubit_num)
        gate_name = str(id(self)) + '_' + str(qubit_num)
        self._GateBuilder__gate = MatrixGate(gate_name, qubit_num)
        if isinstance(mat, np.ndarray):
            self._GateBuilder__gate.matrix = lambda *args: mat
        else:
            self._GateBuilder__gate.matrix = mat

    # def to_gate(self):
    #     return self.__gate

class MultiControlledMatrixGate(ControlledGate):
    def __init__(self, matlambda: Callable, ctrl_num: int, qubit_num: int):
        self._ControlledGate__label = 'C' + str(ctrl_num) + 'm' + str(id(self))
        self._ControlledGate__qubit_num = qubit_num
        self._ControlledGate__factors = []
        self.control_bits = ctrl_num
        mbuilder = MatrixGateBuilder(matlambda)
        self.base_gate = mbuilder.to_gate()

    # @property
    # def label(self) -> str:
    #     return self.__label

    # @property
    # def qubit_num(self):
    #     return self.__qubit_num

    # @property
    # def factors(self) -> List:
        # return self.__factors

class MultiControlledMatrixGateBuilder(GateBuilder):
    def __init__(self, matlambda: Callable, ctrl_num: int, qubit_num: int) -> None:
        super().__init__(qubit_num)
        self._GateBuilder__gate = MultiControlledMatrixGate(matlambda, ctrl_num, qubit_num)
    
    # def to_gate(self):
    #     return self.__gate