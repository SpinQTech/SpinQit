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
import warnings
from copy import deepcopy
# from torch import Tensor
import numpy as np
from spinqit.model.gates import MEASURE
from typing import List, Tuple, Union
from .basic_gate import Gate
from .instruction import Instruction
from .register import QuantumRegister, ClassicalRegister
from .parameter import Parameter, ParameterExpression
from spinqit.utils.function import _flatten


class Circuit(object):
    def __init__(self, params=None):
        if params is not None:
            if not isinstance(params, (Parameter, int)):
                raise ValueError(
                    'The type of parameter should be `spinqit.Parameter or `int`'
                )
            if isinstance(params, Parameter) and len(params.shape) > 1:
                warnings.warn('The parameter will be reshape to 1-dimensions')
                params = params.reshape(-1)

            if isinstance(params, int):
                params = Parameter(np.random.uniform(0, 2 * np.pi, size=params), trainable=True)
        else:
            params = np.array([])

        self.__params = params
        self.__qubits_num = 0
        self.__clbits_num = 0
        self.__qureg_list = []
        self.__clreg_list = []
        self.__instructions = []

    @property
    def qubits_num(self):
        return self.__qubits_num

    @property
    def clbits_num(self):
        return self.__clbits_num

    @property
    def qureg_list(self):
        return self.__qureg_list

    @property
    def clreg_list(self):
        return self.__clreg_list

    @property
    def instructions(self):
        return self.__instructions

    @instructions.setter
    def instructions(self, new_instructions):
        self.__instructions = new_instructions

    @property
    def params(self):
        return self.__params

    @params.setter
    def params(self, new_params):
        try:
            from torch import Tensor
            if isinstance(new_params, Tensor):
                if new_params.is_cuda:
                    new_params = new_params.cpu()
                if new_params.requires_grad:
                    new_params = new_params.detach()
        except Exception as e:
            pass
        if not isinstance(new_params, Parameter):
            new_params = Parameter(new_params, trainable=True)
        for ins in self.instructions:
            if isinstance(ins.params, Parameter) and getattr(ins.params, 'trainable'):
                func = ins.params.func
                _p = func(new_params)
                ins.params = _p
        self.__params = new_params

    @property
    def qubits(self):
        return [i for i in range(self.__qubits_num)]

    def allocateQubits(self, num: int):
        reg = QuantumRegister(num, self.__qubits_num)
        self.__qureg_list.append(num)
        self.__qubits_num += num
        return reg

    def allocateClbits(self, num: int):
        reg = ClassicalRegister(num, self.__clbits_num)
        self.__clreg_list.append(num)
        self.__clbits_num += num
        return reg

    def __add__(self, other: 'Circuit'):
        other_circ = deepcopy(other)

        if self.qubits_num < other.qubits_num:
            self.allocateQubits(other.qubits_num - self.qubits_num)
        if self.clbits_num < other.clbits_num:
            self.allocateClbits(other.clbits_num - self.clbits_num)

        self.__concatenate_params(other_circ)
        self.extend(other_circ.instructions)
        return self

    def __concatenate_params(self, other):
        new_params = Parameter(np.concatenate((self.params, other.params)), trainable=True)
        new_func = ParameterExpression(
            lambda x, start=self.params.size, end=new_params.size:
            x[start:end]
        )
        for ins in other.instructions:
            if isinstance(ins.params, Parameter) and getattr(ins.params, 'trainable'):
                _p = ins.params.func(new_func(new_params))
                ins.params = _p
        self.__params = new_params

    def __lshift__(self, other: Tuple):
        gate = other[0]
        qubits = list(_flatten((other[1],)))
        p = other[2:]
        if not any(callable(x) for x in p):
            self.append(gate, qubits, [], *p)
        else:
            params = self.params
            if params.size == 0:
                raise ValueError(
                    'There is no parameter in the circuit.'
                )
            if not isinstance(p[0], ParameterExpression):
                plambda = ParameterExpression(p[0])
            else:
                plambda = p[0]
            sub_param = plambda(params)
            self.append(gate, qubits, [], sub_param)
        return self

    def __or__(self, other: Tuple):
        self.__instructions[-1].set_condition(other[0], other[1], other[2])

    def measure(self, qubits: Union[int, List[int]], clbits: Union[int, List[int]]):
        if isinstance(qubits, int):
            qubits = [qubits]
        if isinstance(clbits, int):
            clbits = [clbits]
        if len(qubits) != len(clbits):
            raise Exception('The number of qubits does not match the number of classical bits.')
        self.__instructions.append(Instruction(MEASURE, qubits, clbits))

    def append(self, gate: Gate, qubits: List[int] = [], clbits: List[int] = [], *params: Tuple):
        self.__instructions.append(Instruction(gate, qubits, clbits, *params))

    def append_instruction(self, inst: Instruction):
        self.__instructions.append(inst)

    def extend(self, inst_list: List):
        for inst in inst_list:
            self.append_instruction(inst)
