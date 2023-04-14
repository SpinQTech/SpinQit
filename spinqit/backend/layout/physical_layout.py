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
from spinqit.backend.layout.layout import Layout
from typing import List, Tuple
from time import time
from constraint import RecursiveBacktrackingSolver, Problem, AllDifferentConstraint
from spinqit.model import InappropriateBackendError

class CSPSolver(RecursiveBacktrackingSolver):
    def __init__(self, iteration_limit: int = None, timeout: float = None):
        self.iteration_limit = iteration_limit
        self.timeout = timeout
        self.iteration = 0
        self.time_start = None
        self.time_sofar = None
        super().__init__()

    def check_limits(self) -> bool:
        if self.iteration_limit is not None:
            self.iteration += 1
            if self.iteration > self.iteration_limit:
                return True
        if self.timeout is not None:
            self.time_sofar = time() - self.time_start
            if self.time_sofar > self.timeout:
                return True
        return False

    def getSolution(self, domains, constraints, vconstraints):
        if self.iteration_limit is not None:
            self.iteration = 0
        if self.timeout is not None:
            self.time_start = time()
        return super().getSolution(domains, constraints, vconstraints)

    def recursiveBacktracking(self, solutions, domains, vconstraints, assignments, single):
        if self.check_limits():
            return None
        return super().recursiveBacktracking(solutions, domains, vconstraints, assignments, single)
    

def generate_direct_layout(logical_qubit_num: int, logical_connections: List[Tuple], physical_qubit_num: int, coupling_map: List[Tuple], iteration_limit: int = 1000, timeout: float = None) -> Tuple[Layout, str]:
    '''Each tuple in logical_connections may have 2 or 3 qubits.
    '''
    if logical_qubit_num > physical_qubit_num:
        raise InappropriateBackendError('There is no enough qubits.')

    solver = CSPSolver(iteration_limit, timeout)
    problem = Problem(solver)
    logical_qubits = list(range(logical_qubit_num))
    physical_qubits = list(range(physical_qubit_num))

    problem.addVariables(logical_qubits, physical_qubits)
    problem.addConstraint(AllDifferentConstraint())
    def constraint_func(qa,qb):
        return (qa, qb) in coupling_map or (qb, qa) in coupling_map
    for pair in logical_connections:
        problem.addConstraint(constraint_func, [pair[0], pair[1]])
        if len(pair) == 3:
            problem.addConstraint(constraint_func, [pair[0], pair[2]])
            problem.addConstraint(constraint_func, [pair[1], pair[2]])
    
    solution = problem.getSolution()

    mesg = 'OK'
    if solution is None:
        if solver.iteration > iteration_limit:
            mesg = 'Maximum iteration reached.'
        elif timeout is not None and solver.time_sofar > timeout:
            mesg = 'Layout execution timeout.'
        else:
            mesg = 'There is no available layout.'
        return None, mesg

    layout = Layout()
    for k in logical_qubits:
        layout.add_log_to_phy(k, solution[k])
    
    return layout, mesg
