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

from ..ir import IntermediateRepresentation
from .cancel_redundant_gates import CancelRedundantGates
from .collapse_single_qubit_gates import CollapseSingleQubitGates
from .collapse_two_qubit_gates import CollapseTwoQubitGates
from .quantum_basis_state_optimization import ConstantsStateOptimization
from .quantum_pure_state_optimization import PureStateOnU

class PassManager(object):
    def __init__(self, level: int):
        self.passes = []
        if level == 1:
            self.passes.append(CancelRedundantGates())
            self.passes.append(CollapseSingleQubitGates())
        elif level == 2:
            self.passes.append(CancelRedundantGates())
            self.passes.append(CollapseSingleQubitGates())
            self.passes.append(CollapseTwoQubitGates())
        elif level == 3:
            self.passes.append(CancelRedundantGates())
            self.passes.append(ConstantsStateOptimization())
            self.passes.append(PureStateOnU())
            self.passes.append(CollapseSingleQubitGates())
            self.passes.append(CollapseTwoQubitGates())
    
    def append(self, optimizer):
        self.passes.append(optimizer)

    def run(self, ir: IntermediateRepresentation):
        for optimizer in self.passes:
            optimizer.run(ir)
