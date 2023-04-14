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
#
# This file is based on the implementation in https://github.com/1ucian0/rpo.
# The original notice is as follows.
#
# (C) Copyright Ji Liu and Luciano Bello 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

from typing import List
from igraph import Vertex
import math
import numpy as np
from .util import get_qubits
from ..ir import IntermediateRepresentation, NodeType
from ..decomposer import decompose_zyz
from spinqit.model import Instruction, OptimizerError
from spinqit.model import H, X, Y, Z, S, Sd, T, Td, P, Rx, Ry, Rz, CX, CY, CZ, CCX, SWAP

_CHOP_THRESHOLD = 1e-15

class PureStateOnU(object):
    single_gates = {X.label, Y.label, Z.label, H.label, S.label, Sd.label, T.label, Td.label, P.label, Rx.label, Ry.label, Rz.label}
    controlled_gates = {CX.label, CY.label, CZ.label, CCX.label} 

    def __init__(self) -> None:
        self.wire_state = None

    def run(self, ir: IntermediateRepresentation):
        self.wire_state = PureState(ir.dag['qnum'])
        keep_list = []
        non_keep_list = []
        vs = ir.dag.topological_sorting()
        for v in vs:
            if ir.dag.vs[v]['type'] == NodeType.caller.value:
                break
            if ir.dag.vs[v]['type'] == NodeType.op.value:
                if 'cmp' in ir.dag.vs[v].attributes() and ir.dag.vs[v]['cmp'] is not None:
                    break
                gname = ir.dag.vs[v]['name']
                qargs = ir.dag.vs[v]['qubits']
                if 'params' in ir.dag.vs[v].attributes() and ir.dag.vs[v]['params'] is not None:    
                    params = ir.dag.vs[v]['params']
                else:
                    params = None
                if gname in self.controlled_gates:
                    for qarg in qargs:
                        self.wire_state[qarg] = None
                elif gname == SWAP.label:
                    if self.wire_state.swap_can_be_removed(qargs[0], qargs[1]):
                        keep_list.append(v)
                        continue

                    prev = ir.dag.predecessors(ir.dag.vs[v])
                    which_swap = self.wire_state.swap_can_be_replaced(qargs[0], qargs[1])
                    if which_swap == 'both':
                        new_dag = self.swap_to_u_dag(qargs[0], qargs[1])
                        ir.substitute_nodes([v], new_dag, ir.dag.vs[v]['type'])
                        non_keep_list.append(v)
                    elif which_swap in ['left', 'right']:
                        new_dag = self.aswap_to_u_dag(qargs[0], qargs[1], which_swap)
                        ir.substitute_nodes([v], new_dag, ir.dag.vs[v]['type'])
                        non_keep_list.append(v)
                        self.wire_state.swap(qargs[0], qargs[1])
                    else:
                        self.wire_state.swap(qargs[0], qargs[1])
                        continue
                elif gname in self.single_gates:
                    self.single_gates_wire_status(gname, qargs, params)
                else:
                    for qarg in qargs:
                        self.wire_state[qarg] = None
                        
        ir.remove_nodes(keep_list, True)
        ir.remove_nodes(non_keep_list, False)

    def check_single_qubit_gate(self, v: Vertex):
        if (v['type'] == NodeType.op.value or v['type'] == NodeType.callee.value) \
            and v['name'] in self.single_gates:
            return True
        return False

    def check_zero_state(self, qubit: int):
        ws = self.wire_state[qubit]
        if ws[0] == 0 and ws[1] == 0 and ws[2] == 0:
            return True
        else:
            return False

    def swap_to_u_dag(self, qubit1, qubit2):
        new_dag = []
        if not self.check_zero_state(qubit1):
            new_dag.append(Instruction(Rz, [qubit1], [], -1*self.wire_state[qubit1][2]))
            new_dag.append(Instruction(Ry, [qubit1], [], -1*self.wire_state[qubit1][0]))
            new_dag.append(Instruction(Rz, [qubit1], [], -1*self.wire_state[qubit1][1]))
            new_dag.append(Instruction(Rz, [qubit2], [], self.wire_state[qubit1][2]))
            new_dag.append(Instruction(Ry, [qubit2], [], self.wire_state[qubit1][0]))
            new_dag.append(Instruction(Rz, [qubit2], [], self.wire_state[qubit1][1]))
        if not self.check_zero_state(qubit2):
            new_dag.append(Instruction(Rz, [qubit2], [], -1*self.wire_state[qubit2][2]))
            new_dag.append(Instruction(Ry, [qubit2], [], -1*self.wire_state[qubit2][0]))
            new_dag.append(Instruction(Rz, [qubit2], [], -1*self.wire_state[qubit2][1]))
            new_dag.append(Instruction(Rz, [qubit1], [], self.wire_state[qubit2][2]))
            new_dag.append(Instruction(Ry, [qubit1], [], self.wire_state[qubit2][0]))
            new_dag.append(Instruction(Rz, [qubit1], [], self.wire_state[qubit2][1]))
        return new_dag

    def aswap_to_u_dag(self, qubit1, qubit2, which_swap):
        if which_swap == 'left':
            q1, q2 = qubit1, qubit2
        elif which_swap == 'right':
            q1, q2 = qubit2, qubit1

        new_dag = []
        if not self.check_zero_state(q1):
            new_dag.append(Instruction(Rz, [q1], [], -1*self.wire_state[q1][2]))
            new_dag.append(Instruction(Ry, [q1], [], -1*self.wire_state[q1][0]))
            new_dag.append(Instruction(Rz, [q1], [], -1*self.wire_state[q1][1]))
        new_dag.append(Instruction(CX, [q2, q1]))
        new_dag.append(Instruction(CX, [q1, q2]))
        if not self.check_zero_state(q1):
            new_dag.append(Instruction(Rz, [q2], [], self.wire_state[q1][2]))
            new_dag.append(Instruction(Ry, [q2], [], self.wire_state[q1][0]))
            new_dag.append(Instruction(Rz, [q2], [], self.wire_state[q1][1]))
        return new_dag

    def single_gates_wire_status(self, gate: str, qargs: List, params: List = None):
        if self.wire_state[qargs[0]] is None:
            return
        if gate == X.label:
            self.wire_state.u3(qargs[0], [np.pi, 0, np.pi])
        elif gate == Y.label:
            self.wire_state.u3(qargs[0], [np.pi, np.pi / 2, np.pi / 2])
        elif gate == Z.label:
            self.wire_state.u1(qargs[0], [np.pi])
        elif gate == H.label:
            self.wire_state.u2(qargs[0], [0, np.pi])
        elif gate == S.label:
            self.wire_state.u1(qargs[0], [np.pi / 2])
        elif gate == Sd.label:
            self.wire_state.u1(qargs[0], [3 * np.pi / 2])
        elif gate == T.label:
            self.wire_state.u1(qargs[0], [np.pi / 4])
        elif gate == Td.label:
            self.wire_state.u1(qargs[0], [7 * np.pi / 4])
        elif gate == Rx.label:
            self.wire_state.u3(qargs[0], [params[0], 3 * np.pi / 2, np.pi / 2])
        elif gate == Ry.label:
            self.wire_state.u3(qargs[0], [params[0], 0, 0])
        elif gate == Rz.label or gate == P.label:
            self.wire_state.u1(qargs[0], [params[0]])
        else:
            raise OptimizerError('Unexpected single qubit gate')

class PureState():
    def __init__(self, qnum) -> None:
        self._dict = {qubit: [0.0, 0.0, 0.0] for qubit in range(qnum)}

    def __setitem__(self, key, item):
        self._dict[key] = item

    def __getitem__(self, key):
        return self._dict[key]

    def __repr__(self):
        return repr(self._dict)

    def swap(self, qubit1, qubit2):
        self._dict[qubit1], self._dict[qubit2] = self._dict[qubit2], self._dict[qubit1]

    def swap_can_be_removed(self, qubit1, qubit2):
        if self._dict[qubit1] is None or self._dict[qubit2] is None:
            return False
        elif self._dict[qubit1] == self._dict[qubit2]:
            return True
        else:
            return False

    def swap_can_be_replaced(self, qubit1, qubit2):
        if self._dict[qubit1] is not None and self._dict[qubit2] is not None:
            swap_id = 'both'
        elif self._dict[qubit1] is not None:
            swap_id = 'left'
        elif self._dict[qubit2] is not None:
            swap_id = 'right'
        else:
            swap_id = None
        return swap_id

    def u1(self, qubit, parameters):
        self.u3(qubit, [0, 0, parameters[0]])

    def u2(self, qubit, parameters):
        self.u3(qubit, [np.pi/2, parameters[0], parameters[1]])

    def u3(self, qubit, parameters):
        theta1 = parameters[0]
        phi1 = parameters[1]
        lambda1 = parameters[2]
        theta2 = self._dict[qubit][0]
        phi2 = self._dict[qubit][1]
        lambda2 = self._dict[qubit][2]
        thetap, phip, lambdap = PureState.yzy_to_zyz((lambda1 + phi2), theta1, theta2)
        self._dict[qubit][0], self._dict[qubit][1], self._dict[qubit][2] = PureState.round_to_half_pi(thetap, phi1 + phip, lambda2 + lambdap)


    def check_Zero_state(self, qubit):
        if self._dict[qubit] is None:
            return False
        elif np.isclose(self._dict[qubit][0], 0):
            return True
        else:
            return False

    def check_One_state(self, qubit):
        if self._dict[qubit] is None:
            return False
        elif np.isclose(self._dict[qubit][0], np.pi):
            return True
        else:
            return False

    def check_Plus_state(self, qubit):
        if self._dict[qubit] is None:
            return False
        elif np.isclose(self._dict[qubit][0], np.pi/2) and np.isclose(self._dict[qubit][1], 0):
            return True
        else:
            return False

    def check_Minus_state(self, qubit):
        if self._dict[qubit] is None:
            return False
        elif np.isclose(self._dict[qubit][0], np.pi/2) and np.isclose(self._dict[qubit][1], np.pi):
            return True
        else:
            return False

    @staticmethod
    def yzy_to_zyz(xi, theta1, theta2):
        """Express a Y.Z.Y single qubit gate as a Z.Y.Z gate.
        Solve the equation
        .. math::
        Ry(theta1).Rz(xi).Ry(theta2) = Rz(phi).Ry(theta).Rz(lambda)
        for theta, phi, and lambda.
        Return a solution theta, phi, and lambda.
        """
        yzy_matrix = Ry.matrix([theta1]) @ Rz.matrix([xi]) @ Ry.matrix([theta2])
        lambd, theta, phi, phase = decompose_zyz(yzy_matrix)
        output = (theta, phi, lambd)
        out_angles = tuple(0 if np.abs(angle) < _CHOP_THRESHOLD else angle
                           for angle in output)
        return out_angles
        

    @staticmethod
    def round_to_half_pi(thetar, phir, lambdar):
        # if thetar > np.pi:
        #     raise TranspilerError('Unexpected theta value')
        
        if abs(math.fmod(thetar, math.pi/2)) < _CHOP_THRESHOLD:
            thetar = int(round(thetar/(math.pi/2))) * math.pi/2
        if abs(math.fmod(phir, math.pi/2)) < _CHOP_THRESHOLD:
            phir = int(round(phir/(math.pi/2))) * math.pi/2
        if abs(math.fmod(lambdar, math.pi/2)) < _CHOP_THRESHOLD:
            lambdar = int(round(lambdar/(math.pi/2))) * math.pi/2
        phir = phir % (2 * math.pi)
        lambdar = lambdar % (2 * math.pi)
        return thetar, phir, lambdar