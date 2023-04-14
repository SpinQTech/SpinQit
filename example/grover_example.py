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
from spinqit import get_basic_simulator, get_compiler, Circuit, BasicSimulatorConfig
from spinqit import AmplitudeAmplification, GateBuilder, RepeatBuilder
from spinqit import H, X, Z
from spinqit.primitive import MultiControlledGateBuilder
from math import pi

circ = Circuit()
q = circ.allocateQubits(4)

hbuilder = RepeatBuilder(H, 4)
circ << (hbuilder.to_gate(), q)

# Build the oracle for 1100
oracle_builder = GateBuilder(4)
oracle_builder.append(X, [2])
oracle_builder.append(X, [3])

mcz_builder = MultiControlledGateBuilder(3, gate=Z)
oracle_builder.append(mcz_builder.to_gate(), list(range(4)))

oracle_builder.append(X, [2])
oracle_builder.append(X, [3])

grover = AmplitudeAmplification(oracle_builder.to_gate(), q)
circ.extend(grover.build())

# Set up the backend and the compiler
engine = get_basic_simulator()
comp = get_compiler("native")
optimization_level = 0
exe = comp.compile(circ, optimization_level)
config = BasicSimulatorConfig()
config.configure_shots(1024)

# Run
result = engine.execute(exe, config)
print(result.counts)

