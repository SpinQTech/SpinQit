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

from antlr4 import *
from .ir import IntermediateRepresentation
from .qasm.Qasm2ErrorListener import Qasm2ErrorListener
from .qasm.Qasm2EventListener import Qasm2EventListener
from .qasm.Qasm2Lexer import Qasm2Lexer
from .qasm.Qasm2Parser import Qasm2Parser
from spinqit.compiler.compiler import Compiler


class QASMCompiler(Compiler):
    def __init__(self):
        super().__init__()

    def compile(self, filepath: str, level: int):
        ir = IntermediateRepresentation()
        input_stream = FileStream(filepath)
        lexer = Qasm2Lexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = Qasm2Parser(stream)
        error_listener = Qasm2ErrorListener()
        gate_sym_table = {'U': 1, 'CX': 2, 'id': 1, 'h': 1, 'x': 1, 'y': 1, 'z': 1, 'rx': 1, 'ry': 1, 'rz': 1, 't': 1,
                          'tdg': 1, 's': 1, 'sdg': 1, 'p': 1, 'cx': 2, 'cy': 2, 'cz': 2, 'swap': 2, 'ccx': 3, 'u': 1}
        param_num_table = {'U': 3, 'u': 3, 'rx': 1, 'ry': 1, 'rz': 1, 'p': 1}
        parser_listener = Qasm2EventListener(ir, gate_sym_table, param_num_table)
        parser.addErrorListener(error_listener)
        parser.addParseListener(parser_listener)
        parser.program()

        if len(error_listener.errors) > 0 or len(parser_listener.errors) > 0:
            return None

        ir.build_dag()
        return ir
