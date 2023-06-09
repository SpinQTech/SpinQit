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
from spinqit import get_basic_simulator, BasicSimulatorConfig
from spinqit import GateBuilder, RepeatBuilder
from spinqit import H, Z
from spinqit.algorithm import QuantumCounting
from math import pi

hbuilder = RepeatBuilder(H, 4)

# Build the oracle for ***1
oracle_builder = GateBuilder(4)
oracle_builder.append(Z, [3])

# Set up the backend
engine = get_basic_simulator()
config = BasicSimulatorConfig()
config.configure_shots(1024)

qc = QuantumCounting(4, 4, hbuilder.to_gate(), oracle_builder.to_gate())
ret = qc.run(engine, config)
print(ret)

