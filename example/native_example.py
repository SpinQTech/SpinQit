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

from spinqkit import get_basic_simulator, get_compiler, Circuit, BasicSimulatorConfig
from spinqkit import H, CX, Rx
from math import pi

engine = get_basic_simulator()
comp = get_compiler("native")

circ = Circuit()
q = circ.allocateQubits(2)
circ << (Rx, q[0], pi)
circ << (H, q[1])
circ << (CX, (q[0], q[1]))

optimization_level = 0
exe = comp.compile(circ, optimization_level)
config = BasicSimulatorConfig()
config.configure_shots(1024)

result = engine.execute(exe, config)
print(result.probabilities)
print(result.counts)
print(result.states)

