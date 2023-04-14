# Copyright 2022 SpinQ Technology Co., Ltd.
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

from .basic_simulator_backend import BasicSimulatorBackend
from .nmr_backend import NMRBackend
from .spinq_cloud_backend import SpinQCloudBackend
from .pytorch_backend import TorchSimulatorBackend
from .qasm_backend import QasmBackend

BS = BasicSimulatorBackend()
TB = NMRBackend()
TSB = TorchSimulatorBackend()

def get_basic_simulator():
    return BS

def get_nmr():
    return TB

def get_torch_simulator():
    return TSB

def get_qasm_backend(func):
    return QasmBackend(func)

def get_spinq_cloud(username, signStr):
    return SpinQCloudBackend(username, signStr)