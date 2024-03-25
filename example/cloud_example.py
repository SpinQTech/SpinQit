# Copyright 2023 SpinQ Technology Co., Ltd.
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

from spinqit import get_compiler
from spinqit.backend import get_spinq_cloud, SpinQCloudConfig
from spinqit.model import Circuit
from spinqit import H, CZ

username = "username"
keyfile = "/path/to/.ssh/id_rsa"

# login to SpinQCloudBackend
backend = get_spinq_cloud(username, keyfile)

gemini = backend.get_platform("gemini_vp")
print("gemini has " + str(gemini.machine_count) + " active machines.")

if gemini.available():
    comp = get_compiler("native")
    circ = Circuit()
    q = circ.allocateQubits(2)
    circ << (H, q[0])
    circ << (CZ, (q[1], q[0]))
    circ << (CZ, (q[0], q[1]))
    ir = comp.compile(circ, 0)

    config = SpinQCloudConfig()
    config.configure_platform('gemini_vp')
    config.configure_shots(1024)
    config.configure_task('newapitest1', 'newapi')

    res = backend.execute(ir, config)
    print(res.probabilities)
else:
    print("No machine available for this platform.")

