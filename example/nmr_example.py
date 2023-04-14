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

from spinqit import get_nmr, get_compiler, Circuit, NMRConfig
from spinqit import H, CX

engine = get_nmr()
comp = get_compiler("native")

circ = Circuit()

q = circ.allocateQubits(3)
circ << (H, q[0])
circ << (CX, (q[0], q[1]))
circ << (CX, (q[1], q[2]))

exe = comp.compile(circ, 0)
config = NMRConfig()
config.configure_shots(1024)
config.configure_ip("192.168.1.113")
config.configure_port(55444)
config.configure_account("user9", "123456")
config.configure_task("task1", "GHZ")

result = engine.execute(exe, config)
print(result.probabilities)
