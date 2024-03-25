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

from .optimizer import Optimizer
from .utils import optimizer_timer
from ..loss import probs
from spinqit.grad._grad import qgrad
from spinqit.model import Circuit, Instruction
from spinqit.compiler.ir import IntermediateRepresentation as IR
from spinqit.model.parameter import Parameter
from spinqit.primitive import PauliBuilder
from spinqit.utils.function import _topological_sort, requires_grad
from copy import deepcopy


def fubini_tensor(qlayer, *params):

    # def convert_ob(qubit, pstr, eigval, coeff):
    #     measure = probs(mqubits=qubit)
    #     if pstr == 'P':
    #         probabilities = backend.evaluate(qlayer.compile_circuit(temp_circ, 0), config, measure)[0]
    #     else:
    #         h_part = PauliBuilder(pstr).to_gate()
    #         temp_circ << (h_part, qubit)
    #         probabilities = backend.evaluate(qlayer.compile_circuit(temp_circ, 0), config, measure)[0]
    #         temp_circ.instructions.pop()
    #     probabilities = Parameter(probabilities.cpu().detach() if hasattr(probabilities, 'cpu') else probabilities)
    #     return (coeff * coeff) * (
    #                 (eigval * eigval @ probabilities) - (eigval @ probabilities) * (eigval @ probabilities))

    def convert_ob(qubit, pstr, eigval, coeff):
        measure = probs(mqubits=qubit)
        # zkey = '0' * len(qubit)
        if pstr == 'P':
            probabilities = backend.evaluate(qlayer.compile_circuit(temp_circ, 0), config, measure)[0]
            # probabilities = backend.execute(qlayer.compile_circuit(temp_circ, 0), config).probabilities[0]
        else:
            h_part = PauliBuilder(pstr).to_gate()
            temp_circ << (h_part, qubit)
            # probabilities = backend.execute(qlayer.compile_circuit(temp_circ, 0), config).raw_probabilities[0]
            probabilities = backend.evaluate(qlayer.compile_circuit(temp_circ, 0), config, measure)[0]
            temp_circ.instructions.pop()

        probabilities = Parameter(probabilities.cpu().detach() if hasattr(probabilities, 'cpu') else probabilities)
        return (coeff * coeff) * (
                    (eigval * eigval @ probabilities) - (eigval @ probabilities) * (eigval @ probabilities))

    generator = {'Rx': ('X', np.array([1, -1]), -0.5),
                 'Ry': ('Y', np.array([1, -1]), -0.5),
                 'Rz': ('Z', np.array([1, -1]), -0.5),
                 'P': ('P', np.array([0, 1]), 1)}

    qubit_num = qlayer.qubits_num
    ir = qlayer.ir
    backend = qlayer.backend
    config = deepcopy(qlayer.config)

    backend.check_node(ir, qlayer.place_holder)
    backend.update_param(ir, params)

    # Create a temporary circuit to construct the metric tensor
    temp_circ = Circuit()
    temp_circ.allocateQubits(qubit_num)
    Fubini_study_tensor = []
    for param in params:
        if not isinstance(param, Parameter):
            raise ValueError(
                f'The fubini_tensor is only support type:`spinqit.Parameter` params, but got {type(param)}'
            )
        Fubini_study_tensor.append(np.zeros(shape=param.shape))

    vids = _topological_sort(ir.dag)
    for i in vids:
        v = ir.dag.vs[i]

        if v['type'] in [0, 1]:
            label = v['name']
            if 'params' in v.attributes() and v['params'] is not None and v['func'] is not None:
                for j, _param in enumerate(v['params']):
                    if callable(v['func'][j]) and requires_grad(_param):
                        # The observables corresponding to the generators of the gates in the layer:
                        from autograd import elementwise_grad as egrad
                        coeff = egrad(v['func'][j])(params)
                        val = convert_ob(v['qubits'], *generator[label])
                        for k in range(len(Fubini_study_tensor)):
                            Fubini_study_tensor[k] += coeff[k] * coeff[k] * val

            temp_circ.append_instruction(Instruction(IR.get_basis_gate(label), v['qubits'], [], v['params']))
    return Fubini_study_tensor


class QuantumNaturalGradient(Optimizer):
    def __init__(self,
                 maxiter: int = 1000,
                 tolerance: float = 1e-6,
                 learning_rate: float = 0.01,
                 verbose=True, ):

        super().__init__()

        self.__maxiter = maxiter
        self.__tolerance = tolerance
        self.__learning_rate = learning_rate
        self._verbose = verbose
        self._step = 1

    def optimize(self, qlayer, *params):
        loss_list = []
        params = list(params)
        self.reset()
        while self._step <= self.__maxiter:
            loss = self.step_and_cost(qlayer, params)
            if self.check_optimize_done(loss, loss_list):
                break
            self._step += 1
        return loss_list

    @optimizer_timer
    def step_and_cost(self, qlayer, params):
        grad_fn = qgrad(qlayer)
        first_grads = grad_fn(*params)
        loss = grad_fn.forward
        Fubini_study_tensor = fubini_tensor(qlayer, *params, )

        for i, _tensor in enumerate(Fubini_study_tensor):
            _tensor[_tensor == 0] = np.inf
            params[i] -= self.__learning_rate * first_grads[i] / _tensor
        return loss

    def check_optimize_done(self, loss, loss_list):
        if loss_list and np.abs(loss - loss_list[-1]) < self.__tolerance:
            print(f'The loss difference less than {self.__tolerance}. Optimize done')
            check = True
        else:
            if self._step == self.__maxiter:
                print('The optimized process has been reached the max iteration number.')
            check = False
        loss_list.append(loss)
        return check

    def reset(self):
        self._step = 1
