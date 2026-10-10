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
import functools
import time
import numpy as onp
from copy import deepcopy
from typing import List, Dict, Optional
from math import pi
from autoray import numpy as ar
from scipy import sparse

from .basebackend import BaseBackend
from ..grad import grad_func_hardware
from .layout import Layout, collect_gate_qubits, generate_direct_layout, check_layout
from ..model import Instruction
from ..model.parameter import LazyParameter
from ..model.spinqCloud.circuit import topological_sort_by_dfs
from ..model import H, X, Y, Z, Rx, Ry, Rz, P, T, S, Td, Sd, SWAP, CX, CY, CZ, CCX, MEASURE, StateVector
from ..model.exceptions import CircuitOperationValidationError, RequestTimeoutError, RoutingError, TaskStatusError
from ..compiler.ir import IntermediateRepresentation, NodeType
from .backend_util import _basis_rotation_ir, lazy_property
from ..utils.function import requires_grad
from ..primitive import PauliBuilder, calculate_pauli_expectation, pauli_decompose

from .client.sc_rpc_client import Operation, SC_Client, TaskStatus

class SCConfig:
    def __init__(self):
        self.metadata = {}
        self.metadata['shots'] = 1000

    def configure_shots(self, shots: int):
        self.metadata['shots'] = shots

    def configure_keep_layout(self, flag: bool):
        self.metadata['keep_layout'] = flag

    def configure_ip(self, addr: str):
        self.metadata['ip'] = addr

    def configure_port(self, port: int):
        self.metadata['port'] = port

    def configure_account(self, username: str, password: str):
        self.metadata['username'] = username
        self.metadata['password'] = password

    def configure_task(self, task_name: str, task_desc: str):
        self.metadata['task_name'] = task_name
        self.metadata['task_desc'] = task_desc

    def configure_qubit_mapping(self, physical_qubits: List):
        log_to_phy = {}
        for i in range(len(physical_qubits)):
            log_to_phy[i] = physical_qubits[i]
        self.metadata['qubit_mapping'] = log_to_phy

    def configure_measure_qubits(self, mqubits: List):
        self.metadata['mqubits'] = mqubits

    def configure_print_circuit(self, verbose: bool = True):
        self.metadata['print_circuit'] = verbose

class SCResult:
    def __init__(self, sample_dict: Dict) -> None:
        self.counts = sample_dict["task_result"]
        self.shots = sample_dict["task_execute_num"]
    
    @lazy_property
    def probabilities(self):
        prob_dict = {}
        for key, counts in self.counts.items():
            prob_dict[key] = counts / self.shots
        return prob_dict


class SCBackend(BaseBackend):
    TASK_TIMEOUT = 3600
    def __init__(self):
        super().__init__()

    def replace_nodes(self, ir, v, subgates):
        if v['type'] == NodeType.op.value:
            ir.substitute_nodes([v.index], subgates, v['type'])
            ir.remove_nodes([v.index], False)
        else:
            new_nodes = ir.substitute_nodes([v.index], subgates, v['type'])
            if v['pindex'] is not None:
                nv = ir.dag.vs[new_nodes[1]]
                nv['pindex'] = v['pindex']
            ir.remove_nodes([v.index], False)

    def assemble(self, ir: IntermediateRepresentation):
        if ir.qnum > len(self.physical_qubit_list):
            raise Exception("The superconduct backend does not have enough qubits for this circuit.")
        i = 0
        EPS = 1e-10
        while i < ir.dag.vcount():
            v = ir.dag.vs[i]
            if v['type'] == NodeType.op.value or v['type'] == NodeType.callee.value:
                if 'cmp' in v.attributes() and v['cmp'] is not None:
                    raise Exception('Current backend does not support conditional gates.')
                if v['name'] in [MEASURE.label, StateVector.label]: #, CCX.label]:
                    raise CircuitOperationValidationError("Current backend does not support " + v['name'] + " gate.")
                elif v['name'] == X.label:
                    v['name'] = Rx.label
                    v['params'] = [pi]
                elif v['name'] == Y.label:
                    v['name'] = Ry.label
                    v['params'] = [pi]
                elif v['name'] == Z.label:
                    v['name'] = Rz.label
                    v['params'] = [pi]
                elif v['name'] == P.label:
                    v['name'] = Rz.label
                elif v['name'] == T.label:
                    v['name'] = Rz.label
                    v['params'] = [pi / 4]
                elif v['name'] == S.label:
                    v['name'] = Rz.label
                    v['params'] = [pi / 2]
                elif v['name'] == Td.label:
                    v['name'] = Rz.label
                    v['params'] = [-pi / 4]
                elif v['name'] == Sd.label:
                    v['name'] = Rz.label
                    v['params'] = [-pi / 2]
                elif v['name'] == CX.label:
                    subgates = []
                    subgates.append(Instruction(H, v['qubits'][1:2], []))
                    subgates.append(Instruction(CZ, v['qubits'], []))
                    subgates.append(Instruction(H, v['qubits'][1:2], []))
                    self.replace_nodes(ir, v, subgates)
                    i -= 1
                elif v['name'] == CY.label:
                    subgates = []
                    subgates.append(Instruction(Rx, v['qubits'][1:2], [], pi/2))
                    subgates.append(Instruction(CZ, v['qubits'], []))
                    subgates.append(Instruction(Rx, v['qubits'][1:2], [], -pi/2))
                    self.replace_nodes(ir, v, subgates)
                    i -= 1
                elif v['name'] == SWAP.label:
                    subgates = []
                    subgates.append(Instruction(H, v['qubits'][1:2], []))
                    subgates.append(Instruction(CZ, v['qubits'], []))
                    subgates.append(Instruction(H, v['qubits'][1:2], []))
                    subgates.append(Instruction(H, v['qubits'][0:1], []))
                    subgates.append(Instruction(CZ, v['qubits'][::-1], []))
                    subgates.append(Instruction(H, v['qubits'][0:1], []))
                    subgates.append(Instruction(H, v['qubits'][1:2], []))
                    subgates.append(Instruction(CZ, v['qubits'], []))
                    subgates.append(Instruction(H, v['qubits'][1:2], []))
                    self.replace_nodes(ir, v, subgates)
                    i -= 1
                elif v['name'] == CCX.label:
                    subgates = []
                    for sg, qidx in CCX.factors:
                        subgates.append(Instruction(sg, [v['qubits'][i] for i in qidx], []))
                    self.replace_nodes(ir, v, subgates)
                    i -= 1
            i += 1

    def update_timelist(self, timelist: List, qubits: List) -> int:
        gate_timeslot = -1
        if len(qubits) == 1:
            gate_timeslot = timelist[qubits[0]]
            timelist[qubits[0]] += 1
        elif len(qubits) == 2:
            gate_timeslot = max(timelist)
            for i in qubits:
                timelist[i] = gate_timeslot+1
        return gate_timeslot

    def get_callee_list(self, def_name: str, graph):
        def_v = graph.vs.find(def_name, type=NodeType.definition.value)
        callee_idx_list = topological_sort_by_dfs([def_v.index], graph)
        callee_idx_list = callee_idx_list[1:]
        vertex_list = [graph.vs[idx] for idx in callee_idx_list]
        return vertex_list

    def expand_caller(self, caller_index, caller_qubits, caller_params, graph, timelist, qubit_mapping):
        if isinstance(caller_index, tuple):
            caller_name = graph.vs[caller_index[-1]]['name']
        else:
            caller_name = graph.vs[caller_index]['name']
        callee_operations = []
        callee_list = self.get_callee_list(caller_name, graph)
        
        for callee in callee_list:
            sub_qubits = [caller_qubits[i] for i in callee['qubits']]
            sub_params = []
            if callee['params'] is not None and len(callee['params']) > 0:
                start = 0
                for p in callee['params']:
                    if isinstance(p, (int, float)):
                        sub_params.append(p)
                    else:
                        if len(callee['pindex']) == 1 and callee['pindex'][0] == -1:
                            final_arg = p(caller_params)
                        else:
                            local_args = []
                            arg_count = p.__code__.co_argcount
                            local_args = [] if arg_count == 0 else callee['pindex'][start:start + arg_count]
                            start += arg_count
                            arg_inputs = []
                        
                            for x in local_args:
                                if x >= len(caller_params):
                                    raise ValueError("Global args with idx = " + str(x) + " does not exists.")
                                else:
                                    arg_inputs.append(caller_params[x])
                            final_arg = p(*arg_inputs)
                        sub_params.append(final_arg)
            
            if isinstance(caller_index, tuple):
                gate_index = (*caller_index, callee.index)
            else:
                gate_index = (caller_index, callee.index)

            if callee["type"] == NodeType.caller.value:
                rec_ops = self.expand_caller(gate_index, sub_qubits, sub_params, graph, timelist, 
                                                qubit_mapping)
                callee_operations.extend(rec_ops)
            else:
                gate_timeslot = self.update_timelist(timelist, sub_qubits)
                gate_qubits = [qubit_mapping[k] for k in sub_qubits]
                callee_operations.append(Operation(callee['name'], gate_timeslot, gate_qubits, sub_params))
        return callee_operations

    def vertex_to_operation(self, v, timelist, qubit_mapping):
        params = None
        if 'params' in v.attributes() and v['params'] is not None and len(v['params']) > 0:
            params = v['params']
        
        gate_qubits = v['qubits']
        gate_timeslot = self.update_timelist(timelist, gate_qubits)
        gate_qubits = [qubit_mapping[k] for k in gate_qubits]
        return Operation(v['name'], gate_timeslot, gate_qubits, params)

    # def swaps_to_operations(self, vindex: int, timelist: List, qubit_mapping: Dict, swap_fixes: Dict) -> List:
    #     swap_list = []
    #     if swap_fixes is not None and vindex in swap_fixes:
    #         swap_qubits_list = swap_fixes[vindex]
    #         for swap_qubits in swap_qubits_list:
    #             gate_timeslot = self.update_timelist(timelist, swap_qubits)
    #             swap_phy_qubits = [qubit_mapping[q] for q in swap_qubits]
    #             swap_list.append(Operation(SWAP.label, gate_timeslot, swap_phy_qubits))
    #     return swap_list

    def translate(self, ir: IntermediateRepresentation, qubit_mapping: Dict):
        registers = ir.dag.vs.select(type = NodeType.register.value)
        reg_indices = [node.index for node in registers]
        main_thread_vidx_list = topological_sort_by_dfs(reg_indices, ir.dag)
        main_thread_vx_list = [ir.dag.vs[vidx] for vidx in main_thread_vidx_list]
        
        operations = []
        timelist = [0] * ir.qnum
        for v in main_thread_vx_list:
            if v['type'] == NodeType.op.value:
                operation = self.vertex_to_operation(v, timelist, qubit_mapping)
                operations.append(operation)
            elif v['type'] == NodeType.caller.value:
                callee_operations = self.expand_caller(v.index, v['qubits'], v['params'], ir.dag, timelist, qubit_mapping)
                operations.extend(callee_operations)
        return operations
       
    def transpile(self, ir: IntermediateRepresentation, config: SCConfig):
        self.assemble(ir)
        gate_list = collect_gate_qubits(ir)
        
        gate_qubits = [qubits for _, qubits in gate_list if len(qubits) > 1]
        
        qmapping = False
        if 'qubit_mapping' in config.metadata and len(config.metadata['qubit_mapping']) == ir.qnum:
            qubit_mapping = config.metadata['qubit_mapping']
            gate_phy_qubits = [tuple(qubit_mapping[n] for n in pair) for pair in gate_qubits]
            qmapping = True
        keep_layout = False
        if 'keep_layout' in config.metadata:
            keep_layout = config.metadata['keep_layout']

        if keep_layout and not qmapping:
            raise RoutingError("The qubit mapping is illegal.")
        elif keep_layout and qmapping:
            valid = check_layout(gate_phy_qubits, ir.qnum, len(self.physical_qubit_list), self.coupling_list)
            if not valid:
                raise RoutingError("The topology of the superconducting computer cannot execute this circuit.")
        
        if not keep_layout:
            mapping, message = generate_direct_layout(ir.qnum, gate_qubits, self.physical_qubit_list, self.coupling_list)

            if mapping is None:
                raise RoutingError("The topology of the superconducting computer cannot execute this circuit.")
            qubit_mapping = mapping.log_to_phy
        
        operations = self.translate(ir, qubit_mapping)
        return operations, qubit_mapping

    def execute(self, ir: IntermediateRepresentation, config: SCConfig):
        self.client = SC_Client(config.metadata['ip'], config.metadata['port'])
        account = config.metadata['username']
        password = config.metadata['password']
        self.physical_qubit_list, self.coupling_list = self.client.connect_to_machine(account, password)

        operations, qubit_mapping = self.transpile(ir, config)
        task_name = 'Untitled Task' if 'task_name' not in config.metadata else config.metadata['task_name']
        task_desc = 'No description' if 'task_desc' not in config.metadata else config.metadata['task_desc']
        if 'mqubits' in config.metadata:
            measures = [qubit_mapping[q] for q in config.metadata['mqubits']]
        else:
            measures = [qubit_mapping[q] for q in range(ir.qnum)]

        task_id = self.client.submit_task(task_name, operations, measures, task_desc, config.metadata['shots'])

        click = 0
        while click < self.TASK_TIMEOUT:
            status = self.client.get_task_status(task_id)
            print("get task status", status)
            if status == TaskStatus.finished.value:
                res = self.client.get_task_result(task_id)
                result = SCResult(res)
                self.client.logout_machine()
                return result
            elif status == TaskStatus.failed.value:
                raise TaskStatusError("There is a server error.")
            elif status == TaskStatus.notfound.value:
                raise TaskStatusError("The task is not found.")
            else:
                click += 1
                if status == TaskStatus.queueing.value:
                    time.sleep(10)
                else:
                    time.sleep(1)
        raise RequestTimeoutError("Task Execution Timeout!")

    def get_value_and_grad_fn(self, ir, config, measure_op=None, place_holder=None, grad_method=None):
        def value_and_grad_fn(params):
            params_for_grad = self.process_params(params)
            self.check_node(ir, place_holder)
            self.update_param(ir, params_for_grad)
            val, res = self.evaluate(ir, config, measure_op)
            backward_fn = grad_func_hardware(deepcopy(ir), params_for_grad, config, self, measure_op, res, grad_method)
            return val, backward_fn

        return value_and_grad_fn

    def evaluate(self, ir, config, measure_op):
        if measure_op is None:
            raise ValueError(
                'The measure_op should not be None.'
            )
        if measure_op.mqubits is not None:
            config.configure_measure_qubits(measure_op.mqubits)
        
        if measure_op.mtype == 'expval':
            hamiltonian = measure_op.hamiltonian
            if isinstance(hamiltonian, (onp.ndarray, sparse.csr_matrix)):
                if isinstance(hamiltonian, sparse.csr_matrix):
                    hamiltonian = hamiltonian.A
                hamiltonian = pauli_decompose(hamiltonian)
            value = 0.0
            mqubits = config.metadata['mqubits'] if 'mqubits' in config.metadata else list(range(ir.qnum))
            for pstr, coeff in hamiltonian:
                measurement_ir = _basis_rotation_ir(pstr, mqubits, ir)
                result = self.execute(measurement_ir, config)
                value += coeff * calculate_pauli_expectation(pstr, result.probabilities)
            return value, None
        elif measure_op.mtype == 'prob':
            res = self.execute(ir, config)
            if 'mqubits' in config.metadata:
                np_probs = onp.zeros(2 ** (len(config.metadata['mqubits'])))
            else:
                np_probs = onp.zeros(2**ir.qnum, dtype=float)
            for k, v in res.probabilities.items():
                idx = int(k, 2)
                np_probs[idx] = v
            value = np_probs
        else:
            raise ValueError(
                f'The wrong measure_op.mtype expected `prob`, `expval`, `count`, `state`, but got {measure_op.mtype}'
            )
        return value, res

    @staticmethod
    def update_param(ir, new_params):
        """
        Updating the trainable params
        """
        if new_params is not None:
            for v in ir.dag.vs:
                if 'func' in v.attributes() and v['func'] is not None:
                    func = v['func']
                    _params = []
                    for f in func:
                        if callable(f):
                            _p = f(new_params)
                        else:
                            _p = f
                        _params.append(_p)
                    v['params'] = _params

    @staticmethod
    def process_params(new_params):
        execute_params = []
        for param in new_params:
            execute_params.append(ar.asarray(param, like='spinq', trainable=requires_grad(param)))
        return execute_params

    @functools.lru_cache
    def check_node(self, ir, place_holder):
        # self.assemble(ir)
        if place_holder is not None:
            for v in ir.dag.vs:
                if v['type'] in [0, 1] and 'params' in v.attributes() and v['params'] is not None \
                        and any(isinstance(p, LazyParameter) for p in v['params']):
                    params = v['params']
                    record_function = []
                    for p in params:
                        if isinstance(p, LazyParameter):
                            record_function.append(p.get_function(place_holder))
                        else:
                            record_function.append(p)
                    v['func'] = record_function if len(record_function) > 0 else None

