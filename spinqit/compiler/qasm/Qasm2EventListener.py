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
import os

import traceback
from typing import Dict

from spinqit.model.gates import MEASURE
from math import *
from .Qasm2Lexer import Qasm2Lexer
from .Qasm2Listener import Qasm2Listener
from .Qasm2Parser import *
from ..ir import IntermediateRepresentation, NodeType
from ..translator import qasm_basis_map
import warnings

ln = log


class Qasm2EventListener(Qasm2Listener):
    def __init__(self, ir: IntermediateRepresentation,
                 gate_sym_table: Dict[str, int], param_num_table=None):
        # For QuantumCall which is in the QuantumBlock
        self.__in_block = False
        # For `qelib1.inc` standard gates
        self.__standard_gate = False
        # For recursively called gate
        self.signature_gate_name = None
        if param_num_table is None:
            param_num_table = {}
        self.ir = ir
        self.gate_sym_table = gate_sym_table
        self.param_num_table = param_num_table
        self.qregister_table = {}
        self.cregister_table = {}
        self.local_qubits = {}
        self.local_params = {}
        self.branching = False
        self.conditional_gates = []
        self.errors = []
        self.total_qubits = 0
        self.total_clbits = 0

    def exitQuantumDeclaration(self, ctx: Qasm2Parser.QuantumDeclarationContext):
        try:
            id = ctx.Identifier()
            des_ctx = ctx.designator()
            exp_ctx = des_ctx.expression()
            exp_term_ctx = exp_ctx.expressionTerminator()
            index = exp_term_ctx.Integer()
            reg_size = int(index.getText())
            self.qregister_table[id.getText()] = [self.total_qubits + i for i in range(reg_size)]
            self.ir.add_init_nodes(self.total_qubits, reg_size, NodeType.init_qubit)
            self.total_qubits += reg_size
        except Exception as e:
            self.errors.append(ctx.start.line)

    def exitBitDeclaration(self, ctx: Qasm2Parser.BitDeclarationContext):
        try:
            id = ctx.Identifier()
            des_ctx = ctx.designator()
            exp_ctx = des_ctx.expression()
            exp_term_ctx = exp_ctx.expressionTerminator()
            index = exp_term_ctx.Integer()
            reg_size = int(index.getText())
            self.cregister_table[id.getText()] = [self.total_clbits + i for i in range(reg_size)]
            self.ir.add_init_nodes(self.total_clbits, reg_size, NodeType.init_clbit)
            self.total_clbits += reg_size
        except Exception as e:
            self.errors.append(ctx.start.line)

    def exitQuantumGateDefinition(self, ctx: Qasm2Parser.QuantumGateDefinitionContext):
        self.__standard_gate = False
        self.local_qubits.clear()
        self.local_params.clear()

    def exitQuantumGateSignature(self, ctx: Qasm2Parser.QuantumGateSignatureContext):
        try:
            gate_name_ctx = ctx.Identifier()
            gate_name = gate_name_ctx.getText()

            # If user redefine the basic gate，warn and ignore the content
            if gate_name in qasm_basis_map:
                warnings.warn(
                    'The gate {} is standard gate, should not be declared or used as a signature'.format(gate_name)
                )
                self.__standard_gate = True
                return

            if gate_name in self.gate_sym_table:
                raise Exception(
                    'Gate `{}` already defined above or in include file. '
                    'You may change it another signature gate name'.format(gate_name)
                )
            self.signature_gate_name = gate_name
            qargs_ctx = ctx.identifierList()
            qargs_list = qargs_ctx.Identifier()
            self.gate_sym_table[gate_name] = len(qargs_list)
            for index in range(len(qargs_list)):
                if qargs_list[index].getText() in self.local_qubits:
                    raise Exception(
                        f'The qubits `{qargs_list[index].getText()}` is redeclared again in gate `{gate_name}` '
                        f'in line {ctx.start.line}'
                    )
                self.local_qubits[qargs_list[index].getText()] = index

            param_ctx = ctx.quantumGateParameter()
            if param_ctx is not None:
                param_list_ctx = param_ctx.identifierList()
                param_list = param_list_ctx.Identifier()
                self.param_num_table[gate_name] = len(param_list)
                for index in range(len(param_list)):
                    if param_list[index].getText() in self.local_params:
                        raise Exception(
                            f'The param name {param_list[index].getText()} is repeated in '
                            f'gate {gate_name} in line {ctx.start.line}'
                        )
                    if param_list[index].getText() in self.local_qubits:
                        raise Exception(
                            f'The qubit signature `{qargs_list[index].getText()}` should not be the same '
                            f'as parameter signature `{param_list[index].getText()}` in gate `{gate_name} '
                            f'in line {ctx.start.line}'
                        )
                    self.local_params[param_list[index].getText()] = index

            self.ir.add_def_node(gate_name,
                                 len(self.local_params),
                                 len(self.local_qubits), 0)

        except Exception as e:
            traceback.print_exc()
            self.errors.append(ctx.start.line)

    def collectExpressionTerminators(self, ctx: ParserRuleContext):
        terminators = []
        while ctx.getChildCount() == 1:
            ctx = ctx.getChild(0)

        count = ctx.getChildCount()
        if count == 0:
            if ctx.getText() in self.local_params:
                terminators.append(ctx.getText())
            return terminators

        for i in range(count):
            child = ctx.getChild(i)
            terminators.extend(self.collectExpressionTerminators(child))
        return terminators

    def enterQuantumBlock(self, ctx: Qasm2Parser.QuantumBlockContext):
        self.__in_block = True

    def exitQuantumBlock(self, ctx: Qasm2Parser.QuantumBlockContext):
        self.__in_block = False
        self.signature_gate_name = None

    @staticmethod
    def _is_param_valid(param_list, plambda):
        test_param = [pi for _ in range(len(param_list))]
        try:
            eval(plambda)(*test_param)
            return True
        except:
            return False

    def exitQuantumGateCall(self, ctx: Qasm2Parser.QuantumGateCallContext):
        if self.__standard_gate:
            return
        try:
            gate_name_ctx = ctx.quantumGateName()
            gate_name = gate_name_ctx.getText()

            # check if the gate is declared
            if gate_name not in self.gate_sym_table:
                raise Exception(
                    f'Unknown gate `{gate_name}` in line {ctx.start.line}'
                )

            # check the parameters like theta or constants
            if gate_name not in self.param_num_table and ctx.expressionList() is not None:
                raise Exception(
                    f'Gate `{gate_name}` has no parameter in line {ctx.start.line}'
                )

            if self.__in_block:
                if self.signature_gate_name == gate_name:
                    raise Exception(
                        f'The gate `{gate_name}` has been recursively called in line {ctx.start.line}. '
                        f'For now this operation is not supported'
                    )

            gate_params = []
            param_index = []
            expression_list = []
            if gate_name in self.param_num_table:
                param_ctx = ctx.expressionList()
                if param_ctx is None:
                    raise Exception(
                        f'Missing gate parameter in gate `{gate_name}` in line {ctx.start.line}. '
                    )
                param_list = param_ctx.expression()
                if self.param_num_table[gate_name] != len(param_list):
                    raise Exception(
                        f'The number of parameter of gate `{gate_name}` should be {self.param_num_table[gate_name]}, '
                        f'but got {len(param_list)} in line {ctx.start.line}'
                    )

                for p in param_list:
                    pexp = p.getText()
                    pexp = pexp.replace('lambda', 'lam')
                    if self.__in_block:
                        ptlist = self.collectExpressionTerminators(p)
                        if len(ptlist) > 0:
                            argstr = ','.join(ptlist)
                            # replace the lambda instead of lam
                            argstr = argstr.replace('lambda', 'lam')
                            lexp = "lambda " + argstr + ": " + pexp
                            for x in argstr.split(','):
                                pexp = pexp.replace(x, '{}')
                            expression = f'lambda {argstr}: "{pexp}".format({argstr})'
                            param_index.extend([self.local_params[pt] for pt in ptlist])
                        else:
                            lexp = "lambda *args: " + pexp
                            expression = f'lambda *args: "{pexp}"'
                        if self._is_param_valid(ptlist, lexp):
                            expression_list.append(expression)
                            gate_params.append(eval(lexp))
                        else:
                            raise Exception(
                                f'The expression `{pexp}` in QuantumBlock have some problems in line {ctx.start.line}'
                            )
                    else:
                        gate_params.append(eval(pexp))

            # check the qargs
            index_id_list_ctx = ctx.indexIdentifierList()
            index_id_list = index_id_list_ctx.indexIdentifier()
            if self.gate_sym_table[gate_name] != len(index_id_list):
                raise Exception(
                    f'The qubit number of gate `{gate_name}` should be {self.gate_sym_table[gate_name]}, '
                    f'but got {len(index_id_list)} in line {ctx.start.line}'
                )

            gate_qargs = []
            if self.__in_block:
                for index_id_ctx in index_id_list:
                    id = index_id_ctx.Identifier().getText()
                    if not id in self.local_qubits:
                        raise Exception(
                            f'Unknown qubit argument `{id}` in gate `{gate_name}` in line {ctx.start.line}'
                        )
                    gate_qargs.append(self.local_qubits[id])

                if gate_name.lower() in qasm_basis_map.keys():
                    vindex = self.ir.add_callee_node(qasm_basis_map[gate_name.lower()].label, gate_params, gate_qargs, [],
                                                     param_index, False, expression_list)
                else:
                    vindex = self.ir.add_callee_node(gate_name, gate_params, gate_qargs, [], param_index,
                                                     True, expression_list)  # call another custom function
                if self.branching:
                    self.conditional_gates.append(vindex)
            else:
                duplicates = set()
                for index_id_ctx in index_id_list:
                    id = index_id_ctx.Identifier().getText()
                    if not id in self.qregister_table:
                        raise Exception(
                            f'Unknown qubit register `{id}` in line {ctx.start.line}. '
                        )

                    qubits = self.qregister_table[id]
                    exp_list_ctx = index_id_ctx.expressionList()
                    if exp_list_ctx is None:
                        gate_qargs.extend(qubits)
                    else:
                        exp_list = exp_list_ctx.expression()
                        if len(exp_list) > 1:
                            raise Exception(
                                f'Illegal register index {len(exp_list)} in line {ctx.start.line}. '
                            )

                        index_ctx = exp_list[0].expressionTerminator()
                        index = int(index_ctx.getText())

                        id_index = index_id_ctx.getText()
                        if id_index in duplicates:
                            raise Exception(
                                f'The register index {id_index} is duplicated in line {ctx.start.line}. '
                            )
                        else:
                            duplicates.add(id_index)

                        if index < 0 or index >= len(qubits):
                            raise Exception(
                                f'The register index is out of range in line {ctx.start.line}. '
                            )
                        gate_qargs.append(qubits[index])
                if len(gate_qargs) != self.gate_sym_table[gate_name.lower()]:
                    start = 0
                    while start < len(gate_qargs):
                        if gate_name.lower() in qasm_basis_map.keys():
                            vindex = self.ir.add_op_node(qasm_basis_map[gate_name.lower()].label,
                                                         gate_params,
                                                         gate_qargs[
                                                         start:start + self.gate_sym_table[gate_name.lower()]],
                                                         [])
                        else:
                            vindex = self.ir.add_caller_node(gate_name,
                                                             gate_params,
                                                             gate_qargs[
                                                             start:start + self.gate_sym_table[gate_name.lower()]],
                                                             [])
                        if self.branching:
                            self.conditional_gates.append(vindex)
                        start += self.gate_sym_table[gate_name.lower()]
                else:
                    if gate_name.lower() in qasm_basis_map.keys():
                        vindex = self.ir.add_op_node(qasm_basis_map[gate_name.lower()].label, gate_params, gate_qargs, [])
                    else:
                        vindex = self.ir.add_caller_node(gate_name, gate_params, gate_qargs, [])
                    if self.branching:
                        self.conditional_gates.append(vindex)
        except Exception as e:
            traceback.print_exc()
            self.errors.append(ctx.start.line)

    def exitQuantumMeasurementAssignment(self, ctx: Qasm2Parser.QuantumMeasurementAssignmentContext):
        gate_qargs = []
        gate_cargs = []
        duplicates = set()

        try:
            quantumMeasurementCtx = ctx.quantumMeasurement()
            qindex_id_list_ctx = quantumMeasurementCtx.indexIdentifierList()
            qindex_id_list = qindex_id_list_ctx.indexIdentifier()

            for index_id_ctx in qindex_id_list:
                id = index_id_ctx.Identifier().getText()
                if not id in self.qregister_table:
                    raise Exception('Unknown qubit register')

                qubits = self.qregister_table[id]
                exp_list_ctx = index_id_ctx.expressionList()
                if exp_list_ctx is not None:
                    exp_list = exp_list_ctx.expression()
                    if len(exp_list) > 1:
                        raise Exception('Illegal register index')

                    index_ctx = exp_list[0].expressionTerminator()
                    index = int(index_ctx.getText())

                    id_index = index_id_ctx.getText()
                    if id_index in duplicates:
                        raise Exception('The register index is duplicated')
                    else:
                        duplicates.add(id_index)

                    if index < 0 or index >= len(qubits):
                        raise Exception('The register index is out of range')
                    gate_qargs.append(qubits[index])
                else:
                    gate_qargs.extend(qubits)

            cindex_id_list_ctx = ctx.indexIdentifierList()
            cindex_id_list = cindex_id_list_ctx.indexIdentifier()
            for index_id_ctx in cindex_id_list:
                id = index_id_ctx.Identifier().getText()
                if not id in self.cregister_table:
                    raise Exception('Unknown classical register')

                clbits = self.cregister_table[id]
                exp_list_ctx = index_id_ctx.expressionList()
                if exp_list_ctx is not None:
                    exp_list = exp_list_ctx.expression()
                    if len(exp_list) > 1:
                        raise Exception('Illegal register index')

                    index_ctx = exp_list[0].expressionTerminator()
                    index = int(index_ctx.getText())

                    id_index = index_id_ctx.getText()
                    if id_index in duplicates:
                        raise Exception('The register index is duplicated')
                    else:
                        duplicates.add(id_index)

                    if index < 0 or index >= len(clbits):
                        raise Exception('The register index is out of range')
                    gate_cargs.append(clbits[index])
                else:
                    gate_cargs.extend(clbits)

            if len(gate_qargs) != len(gate_cargs):
                raise Exception('The number of qubits does not match the number of classical bits.')
            self.ir.add_op_node(MEASURE.label, [], gate_qargs, gate_cargs)
        except Exception as e:
            traceback.print_exc()
            self.errors.append(ctx.start.line)

    def enterBranchingStatement(self, ctx: Qasm2Parser.BranchingStatementContext):
        self.branching = True

    def exitBranchingStatement(self, ctx: Qasm2Parser.BranchingStatementContext):
        try:
            expCtx = ctx.expression()
            logicalAndCtx = expCtx.logicalAndExpression()
            bitOrCtx = logicalAndCtx.bitOrExpression()
            xOrCtx = bitOrCtx.xOrExpression()
            bitAndCtx = xOrCtx.bitAndExpression()
            eqCtx = bitAndCtx.equalityExpression()

            eqOpCtx = eqCtx.equalityOperator()
            if eqOpCtx is not None:
                relation = eqOpCtx.getText()
                val = int(eqCtx.comparisonExpression().getText())
                clCtx = eqCtx.equalityExpression()
            else:
                cmpCtx = eqCtx.comparisonExpression()
                relation = cmpCtx.comparisonOperator().getText()
                val = int(cmpCtx.bitShiftExpression().getText())
                clCtx = cmpCtx

            cmexpCtx = clCtx.comparisonExpression()
            bsexpCtx = cmexpCtx.bitShiftExpression()
            adexpCtx = bsexpCtx.additiveExpression()
            muexpCtx = adexpCtx.multiplicativeExpression()
            termCtx = muexpCtx.expressionTerminator()

            idxExpCtx = termCtx.expression()
            if idxExpCtx is not None:
                nameExpCtx = termCtx.expressionTerminator()
                idx = int(idxExpCtx)
                clbits = [self.cregister_table[nameExpCtx.getText()][idx]]
            else:
                clbits = self.cregister_table[termCtx.getText()]

            if val >= 2 ** len(clbits) or val < 0:
                raise Exception(
                    f'The conditional statement is wrong in line {ctx.start.line}. '
                    f'Max classical register value ({2 ** len(clbits) - 1}) is lower than {val}'
                )
            for v in self.conditional_gates:
                self.ir.add_node_condition(v, clbits, relation, val)
            self.conditional_gates = []
        except Exception as e:
            traceback.print_exc()
            self.errors.append(ctx.start.line)

        self.branching = False

    def exitQuantumBarrier(self, ctx: Qasm2Parser.QuantumBarrierContext):
        duplicates = set()

        try:
            if self.__in_block:
                raise Exception(
                    f'For now, the `barrier` in QuantumBlock is not supported. line {ctx.start.line}'
                )

            id_list_ctx = ctx.indexIdentifierList()
            id_list = id_list_ctx.indexIdentifier()

            for index_id_ctx in id_list:
                id = index_id_ctx.Identifier().getText()
                if not id in self.qregister_table:
                    raise Exception(
                        f'Unknown qubit register `{id}` in line {ctx.start.line}'
                    )

                qubits = self.qregister_table[id]
                exp_list_ctx = index_id_ctx.expressionList()
                if exp_list_ctx is not None:
                    exp_list = exp_list_ctx.expression()
                    if len(exp_list) > 1:
                        raise Exception(
                            f'Illegal register index {len(exp_list)} in line {ctx.start.line}'
                        )

                    index_ctx = exp_list[0].expressionTerminator()
                    index = int(index_ctx.getText())

                    id_index = index_id_ctx.getText()
                    if id_index in duplicates:
                        raise Exception(
                            f'The register index `{id_index}` is duplicated in line {ctx.start.line}'
                        )
                    else:
                        duplicates.add(id_index)

                    if index < 0 or index >= len(qubits):
                        raise Exception(
                            f'The register index {index} is out of range in line {ctx.start.line}'
                        )
        except Exception as e:
            traceback.print_exc()
            self.errors.append(ctx.start.line)

    def exitInclude(self, ctx: Qasm2Parser.IncludeContext):
        """
        Read the Include File "qelib1.inc", and add the quantum gate into IR.
        """

        include_file = ctx.StringLiteral().__str__()

        current_dir = os.path.dirname(os.path.realpath(__file__))
        filepath = current_dir + '/include/' + include_file[1:-1]
        input_stream = FileStream(filepath)
        include_lexer = Qasm2Lexer(input_stream)
        include_stream = CommonTokenStream(include_lexer)
        include_parser = Qasm2Parser(include_stream)
        include_parser_listener = Qasm2EventListener(self.ir, self.gate_sym_table, self.param_num_table)

        include_parser.addParseListener(include_parser_listener)
        # read “qelib1.inc” file, ignore the basic gate warnings。
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            include_parser.program()
        for v in self.ir.dag.vs:
            self.ir.include_gate.add(v.index)

    def exitHeader(self, ctx: Qasm2Parser.HeaderContext):
        if not ctx.version():
            warnings.warn(
                'The `OPENQASM` version is not defined in the qasm file.'
                'Note that the version `OPENQASM 2.0` should be used.'
            )
        else:
            version = ctx.version().Integer() if ctx.version().Integer() else ctx.version().RealNumber()
            if float(version.getText()) == 2.:
                pass
            else:
                warnings.warn(
                    'Only support `OPENQASM 2.0`, '
                    f'but got `OPENQASM {version}`. '
                )
