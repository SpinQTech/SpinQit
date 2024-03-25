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
from spinqit.algorithm import HHL
from spinqit import get_basic_simulator, BasicSimulatorConfig
import numpy as np

# Input the linear equations
mat = np.array([[2.5, -0.5], [-0.5, 2.5]])
vec = np.array([1, 0])

# Set up the backend
engine = get_basic_simulator()
config = BasicSimulatorConfig()
config.configure_shots(1024)

# Run
solver = HHL(mat, vec)
solver.run(engine, config)
print(solver.get_state())
print(solver.get_measurements())
