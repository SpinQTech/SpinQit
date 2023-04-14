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

from spinqit import get_compiler
from spinqit.backend import get_spinq_cloud
from spinqit.model import Circuit
from spinqit import H, CZ
import time, datetime
from Crypto.Hash import SHA256
from Crypto.Signature import PKCS1_v1_5 as Signature_pkcs1_v1_5
from Crypto.PublicKey import RSA
import base64

username = "username"
message = username.encode(encoding="utf-8")

with open("/path/to/id_rsa") as f:
    key = f.read()

rsakey = RSA.importKey(key)
signer = Signature_pkcs1_v1_5.new(rsakey)
digest = SHA256.new()
digest.update(message)
printable = digest.hexdigest()
sign = signer.sign(digest)
signature = base64.b64encode(sign)
signStr = str(signature, encoding = "utf-8")

# login to SpinQCloudBackend
backend = get_spinq_cloud(username, signStr)

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
    newTask = backend.submit_task("gemini_vp", ir, "spinqittask1")

    print("=========== Task after submit ===========")
    print(newTask.to_dict())

    # status = newTask.status
    # while not (status == TaskStatus.sccueeded.value or status == TaskStatus.failed.value):
    #     time.sleep(10)
    #     status = newTask.get_status()
    #     print("task status = " + newTask.get_status() + " at " + str(datetime.datetime.now()))

    # print("=========== Track finished ===========")
    res = newTask.get_result()
    print(res)
else:
    print("No machine available for this platform.")

