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
from typing import Tuple
from spinqit.compiler.compiler import Compiler
from spinqit.model import X, Y, Z, CX, CY, CZ, CCX
from spinqit.model import Gate, Circuit, MatrixGate, ControlledGate, InverseGate, MultiControlledMatrixGate
from spinqit.model import UnsupportedGateError
from spinqit.model.instruction import Instruction
from .ir import IntermediateRepresentation as IR, NodeType
from .translator.gate_converter import is_primary_gate, decompose_single_qubit_gate, decompose_multi_qubit_gate
from .optimizer import PassManager
from ..utils.function import _flatten
import numpy as np


class NativeCompiler(Compiler):
    def __init__(self):
        super().__init__()
        self.__gate_definitions = {}

    def add_definition_cluster(self, ir: IR, gate: Gate, n_params: int, n_qubits: int, n_clbits: int):
        if gate.label in self.__gate_definitions:
            return
        if len(gate.factors) <= 0:
            raise UnsupportedGateError('Gate ' + gate.label + ' cannot be decomposed.')
        for f in gate.factors:
            if f[0] not in IR.basis_set and f[0].label not in self.__gate_definitions:
                self.add_definition_cluster(ir, f[0], n_params, len(f[1]), 0)

        def_index = ir.add_def_node(gate.label, n_params, n_qubits, n_clbits)
        for f in gate.factors:
            # sub_qubits = [inst.qubits[i] for i in f[1]]
            plambda = [f[2]] if len(f)>2 else []
            # sub_params = [plambda(inst.params)] if plambda is not None else []
            if f[0] in IR.basis_set:
                ir.add_callee_node(f[0].label, plambda, f[1], [], [-1])
            else:
                ir.add_callee_node(f[0].label, plambda, f[1], [], [-1], True)
                    
        self.__gate_definitions[gate.label] = def_index

    def handle_primary_gate(self, ir: IR, inst: Instruction, condition: Tuple):
        gate = inst.gate
        if gate in IR.basis_set or gate.label in IR.label_set:
            vindex = ir.add_op_node(inst.get_op(), inst.params, inst.qubits, inst.clbits)
            if condition != None:
                ir.add_node_condition(vindex, condition[0], condition[1], condition[2])
        elif isinstance(gate, MatrixGate):
            unitary = gate.get_matrix(*inst.params)
            if len(gate.factors) == 0:      
                vindex = ir.add_unitary_node(gate.label, unitary, inst.qubits, 0, False)
            else:
                self.add_definition_cluster(ir, gate, len(inst.params), len(inst.qubits), len(inst.clbits))
                vindex = ir.add_caller_node(gate.label, inst.params, inst.qubits)
                ir.add_caller_matrix(vindex, unitary)
        elif isinstance(gate, ControlledGate) and (isinstance(gate.base_gate, MatrixGate) or 
            gate.base_gate in IR.basis_set):
            unitary = gate.base_gate.get_matrix(*inst.params)
            ctrl_bits = gate.control_bits
            if gate.base_gate == CX:
                unitary = X.get_matrix()
                ctrl_bits += 1
            elif gate.base_gate == CY:
                unitary = Y.get_matrix()
                ctrl_bits += 1
            elif gate.base_gate == CZ:
                unitary = Z.get_matrix()
                ctrl_bits += 1
            elif gate.base_gate == CCX:
                unitary = X.get_matrix()
                ctrl_bits += 2

            if len(gate.factors) == 0:    
                vindex = ir.add_unitary_node(gate.label, unitary, inst.qubits, gate.control_bits, False)
            else:
                self.add_definition_cluster(ir, gate, len(inst.params), len(inst.qubits), len(inst.clbits))
                vindex = ir.add_caller_node(gate.label, inst.params, inst.qubits)
                ir.add_caller_matrix(vindex, unitary, ctrl_bits)
        elif isinstance(gate, InverseGate) and isinstance(gate.base_gate, MatrixGate): 
            unitary = gate.base_gate.get_matrix(*inst.params)
            inverse_flag = True
            ctrl_bits = 0
            cur_gate = gate.sub_gate
            while cur_gate != gate.base_gate:
                if isinstance(cur_gate, InverseGate):
                    inverse_flag = not inverse_flag
                    cur_gate = cur_gate.sub_gate
                elif isinstance(cur_gate, ControlledGate):
                    ctrl_bits += cur_gate.control_bits
                    cur_gate = cur_gate.base_gate

            if gate.base_gate == CX:
                unitary = X.get_matrix()
                ctrl_bits += 1
            elif gate.base_gate == CY:
                unitary = Y.get_matrix()
                ctrl_bits += 1
            elif gate.base_gate == CZ:
                unitary = Z.get_matrix()
                ctrl_bits += 1
            elif gate.base_gate == CCX:
                unitary = X.get_matrix()
                ctrl_bits += 2
            
            if len(gate.factors) == 0:  
                ir.add_unitary_node(gate.label, unitary, inst.qubits, ctrl_bits, inverse_flag)
            else:
                self.add_definition_cluster(ir, gate, len(inst.params), len(inst.qubits), len(inst.clbits))
                vindex = ir.add_caller_node(gate.label, inst.params, inst.qubits)
                ir.add_caller_matrix(vindex, unitary, ctrl_bits, inverse_flag)

    def compile(self, circ: Circuit, level: int) -> IR:
        self.__gate_definitions = {}
        ir = IR()
        qnum = 0
        for qlen in circ.qureg_list:
            ir.add_init_nodes(qnum, qlen, NodeType.init_qubit)
            qnum += qlen

        cnum = 0
        for clen in circ.clreg_list:
            ir.add_init_nodes(cnum, clen, NodeType.init_clbit)
            cnum += clen

        for inst in circ.instructions:
            gate = inst.gate
            if is_primary_gate(gate):
                self.handle_primary_gate(ir, inst, inst.condition)
            else:
                if gate.qubit_num == 1:
                    ilist = decompose_single_qubit_gate(gate, inst.qubits, inst.params)
                else:
                    ilist = decompose_multi_qubit_gate(gate, inst.qubits, inst.params)

                if len(ilist) == 0:
                    raise UnsupportedGateError("The gate " + gate.label + " is not supported.")
                
                for i in ilist:
                    self.handle_primary_gate(ir, i, inst.condition)
                    # ir.add_op_node(i.get_op(), i.params, i.qubits, i.clbits)
                    # add condition

        ir.build_dag()

        manager = PassManager(level)
        manager.run(ir)
        return ir
