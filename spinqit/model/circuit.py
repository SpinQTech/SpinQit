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
from spinqit.model.gates import MEASURE
from typing import List, Tuple, Union, Iterable
from .basic_gate import Gate, GateBuilder
from .instruction import Instruction
from .register import QuantumRegister, ClassicalRegister
from .parameter import LazyParameter, PlaceHolder
from spinqit.utils.function import to_list


class Circuit(object):
    """
    The quantum circuit for spinqit, Includes parameterized circuit.

    The following example shows how to construct a parameterized circuit,

    Example:
        from spinqit import Circuit, U, Rx, Ry
        from spinqit.algorithm.qlayer import to_qlayer
        from spinqit.algorithm.loss.measurement import expval
        from spinqit.model.parameter import Parameter

        @to_qlayer(backend_mode='spinq', grad_method='param_shift', measure=expval([('ZZ', 1)]))
        def build_circuit(x_shape, y_shape):
            circuit = Circuit()
            circuit.allocateQubits(2)
            x = circuit.add_params(shape=x_shape) #, argnum=(0,))
            y = circuit.add_params(shape=y_shape) #, argnum=(1,))
            circuit << (U,  [0], [y[0], np.pi, y[2]])
            circuit << (Rx, [0], x[0])
            circuit << (Ry, [1], x[0] ** 2 + y[1])
            return circuit
        circuit = build_circuit(3, 3)
        x = Parameter([1., 2, 3], trainable=True)
        y = Parameter([4., 5, 6,], trainable=False)
        print(circuit(x, y))
        # -0.3390986890824953
    """

    def __init__(self, name='circuit'):
        self.name = name
        self.__argnum = 0
        self.place_holder = []
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
    def argnum(self):
        return self.__argnum

    @property
    def instructions(self):
        return self.__instructions

    @instructions.setter
    def instructions(self, new_instructions):
        self.__instructions = new_instructions

    def add_params(self, shape, backend='spinq') -> PlaceHolder:
        """
        Add the parameter's information for the parameterized circuit.
        It will return a PlaceHolder(LazyParameter) to record the functions for this added params.
        Notice that it is not a true parameter for circuit.

        Args:
            shape(int, tuple): The shape for the parameter
            backend(str): choose the backend for quantum circuit.

        Example:
            from spinqit import Circuit
            from spinqit.model.parameter import Parameter

            circuit = Circuit()
            x = circuit.add_params(shape=(3,))
            print(x)
            # <PlaceHolder(fn=None, shape=(3,), dtype=None, backend='autograd')>
        """
        if isinstance(shape, int):
            shape = (shape,)
        elif isinstance(shape, Iterable):
            shape = tuple(shape)
        else:
            raise ValueError(
                f'The shape should be type`int` or type`Iterable`, but got {type(shape)}'
            )
        argnum = (self.__argnum,)
        self.__argnum += 1
        place_holder = PlaceHolder(shape, backend)
        self.place_holder.append((argnum, place_holder))
        return place_holder

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

    def __lshift__(self, other: Tuple):
        gate = other[0]
        qubits = to_list(other[1])
        param = other[2:]
        self.append(gate, qubits, [], *param)

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
        inst = Instruction(gate, qubits, clbits, *params)
        self.__instructions.append(inst)

    def append_instruction(self, inst: Instruction):
        self.__instructions.append(inst)

    def extend(self, inst_list: List):
        for inst in inst_list:
            self.append_instruction(inst)

    # def to_gate(self):
    #     """
    #     Convert circuit to gate. This function is for the circuit concatenate
    #     """
    #     circuit = GateBuilder(self.qubits_num, self.name)
    #     place_holder = tuple(x[1] for x in sorted(self.place_holder, key=lambda x: x[0]))
    #     for inst in self.instructions:
    #         new_param = []
    #         if inst.params is not None:
    #             for param in inst.params:
    #                 if isinstance(param, LazyParameter):
    #                     plambda = param.get_function(place_holder)                        
    #                     new_param.append(plambda)
    #                 else:
    #                     new_param.append(param)
    #         circuit.append(inst.gate, inst.qubits, new_param)
    #     return circuit.to_gate()

    def catenate(self, circuit, qubit_map = None):
        if self.__qubits_num < circuit.qubits_num:
            self.__qubits_num = circuit.qubits_num
            self.__qureg_list = circuit.qureg_list
        if self.__clbits_num < circuit.clbits_num:
            self.__clbits_num = circuit.clbits_num
            self.__clreg_list = circuit.clreg_list
        # update argnum
        for nt, holder in circuit.place_holder:
            self.place_holder.append(((nt[0]+self.__argnum,), holder))
        self.__argnum += circuit.argnum
        # update qubit index
        if qubit_map is not None:
            for inst in circuit.instructions:
                inst.qubits = [qubit_map[q] for q in inst.qubits]
                inst.clbits = [qubit_map[q] for q in inst.clbits]
        self.instructions.extend(circuit.instructions)


