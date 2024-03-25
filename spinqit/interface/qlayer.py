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
from copy import deepcopy

from spinqit import Circuit
from spinqit.backend import check_backend_and_config
from spinqit.compiler import get_compiler, IntermediateRepresentation

class QLayer:
    """
    QLayer is specific for the Quantum machine learning or classic-quantum hybrid machine learning in spinqit.
    With different backend and interface to run the quantum circuit.

    Args:
        circuit (Circuit, IntermediateRepresentation): The quantum circuit. Support class `Circuit` or `IR`.
        measure (MeasureOp): Defined which type of measured results will return.
        interface (str): Default to `spinq`, For now, support `spinq`, `torch`, `paddle`, `tf` interface.
        grad_method (str):
            For `torch` backend support `backprop`
            For `spinq` backend, support `param_shift`, `adjoint_differentiation`
        optimization_level(int): Defined the level for optimize the IR while compiling. Default to 0
    """

    def __init__(self,
                 circuit,
                 measure,
                 backend_mode='spinq',
                 optimization_level=0,
                 interface='spinq',
                 grad_method=None,
                 **kwargs):
        # init backend
        backend, config = check_backend_and_config(backend_mode, **kwargs)
        self.config = config
        self.backend = backend
        opt_config = kwargs.get('config', None)
        if opt_config is not None:
            self.config = opt_config

        ir = self.compile_circuit(circuit, optimization_level)
        self.place_holder = tuple(x[1] for x in sorted(circuit.place_holder, key=lambda x: x[0]))
        self.ir = deepcopy(ir)
        self.measure_op = measure
        self.backend_mode = backend_mode
        self.interface = interface
        self.qubits_num = ir.qnum
        self.grad_method = grad_method
        self.dtype = None
        self.optimzation_level = optimization_level

    def __call__(self, *new_params):
        interface = self.interface

        if interface == 'spinq':
            from spinqit.interface.spinq_interface import execute as _execute

        elif interface == 'torch':
            from spinqit.interface.torch_interface import execute as _execute

        elif interface == 'paddle':
            from spinqit.interface.paddle_interface import execute as _execute

        elif interface == 'tf':
            from spinqit.interface.tf_interface import execute as _execute
        else:
            raise ValueError
        return self.process_with_measure_op(_execute, *new_params)

    def process_with_measure_op(self, execute, *new_params):
        if isinstance(self.measure_op, list):
            origin_measure_op = self.measure_op
            res = []
            for op in self.measure_op:
                self.measure_op = op
                res.append(execute(self, *new_params))
            self.measure_op = origin_measure_op
            return res
        else:
            return execute(self, *new_params)

    def set_device(self, new_device):
        """
        For now, only set the `torch` backend on 'cpu' or 'cuda' device

        For further details, see pytorch documentations.
        Args:
            new_device (str): 'cpu' or 'cuda'
        """
        if self.backend_mode == 'torch':
            self.config.set_device(new_device)

        elif self.backend_mode == 'spinq':
            raise NotImplementedError(
                'The `spinq` are only support cpu backend.'
            )

    def set_dtype(self, new_dtype):
        self.config.set_dtype(new_dtype)

    @staticmethod
    def compile_circuit(circuit, optimization_level):
        if isinstance(circuit, IntermediateRepresentation):
            return circuit
        elif isinstance(circuit, Circuit):
            compiler = get_compiler('native')
        elif isinstance(circuit, str):
            compiler = get_compiler('qasm')
        elif 'qiskit' in circuit.__class__.__name__:
            compiler = get_compiler('qiskit')
        else:
            raise ValueError(
                f'Expected circuit type `IR`, `spinqit.Circuit`, '
                f'But got type {type(circuit)}.'
            )
        ir = compiler.compile(circuit, optimization_level)
        return ir

    def get_measurement_result(self, params):
        new_params = self.backend.process_params(params)
        self.backend.check_node(self.ir, self.place_holder)
        self.backend.update_param(self.ir, new_params)
        return self.backend.execute(self.ir, self.config)

def to_qlayer(**kwargs):
    def decorator(f):
        def inner(*args, **inner_kwargs):
            res = f(*args, **inner_kwargs)
            return QLayer(res, **kwargs)

        return inner

    return decorator
