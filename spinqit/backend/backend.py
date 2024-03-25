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
from spinqit.model.exceptions import InappropriateBackendError
from .basic_simulator_backend import BasicSimulatorBackend
from .nmr_backend import NMRBackend
from .spinq_cloud_backend import SpinQCloudBackend
from .pytorch_backend import TorchSimulatorBackend
from .qasm_backend import QasmBackend

BS = BasicSimulatorBackend()
NB = NMRBackend()
TSB = TorchSimulatorBackend()

avail_backends = ['spinq','torch','nmr','cloud','qasm']
sv_backends = ['spinq','torch']

def get_basic_simulator():
    return BS

def get_nmr():
    return NB

def get_torch_simulator():
    return TSB

def get_qasm_backend(func):
    return QasmBackend(func)

def get_spinq_cloud(username, keyfile):
    return SpinQCloudBackend(username, keyfile)

def check_backend_and_config(backend_mode, **kwargs):
    if backend_mode == 'spinq':
        from .basic_simulator_backend import BasicSimulatorConfig
        backend = BS
        config = BasicSimulatorConfig()
    elif backend_mode == 'torch':
        from .pytorch_backend import TorchSimulatorConfig
        backend = TSB
        config = TorchSimulatorConfig()
    elif backend_mode[:4] == 'qasm':
        from .qasm_backend import QasmConfig
        fn = kwargs.get('backend_fn', None) or kwargs.get('fn', None)
        backend = QasmBackend(fn)
        config = QasmConfig()
    elif backend_mode == 'nmr':
        from .nmr_backend import NMRConfig
        backend = NB
        config = NMRConfig()
        shots = kwargs.get('shot', 1024)
        ip = kwargs.get('ip', None)
        port = kwargs.get('port', None)
        account = kwargs.get('account', None)
        task_name = kwargs.get('task_name', 'NoName')
        task_desc = kwargs.get('task_desc', 'No description.')
        config.configure_shots(shots)
        config.configure_ip(ip)
        config.configure_port(port)
        config.configure_account(*account)
        config.configure_task(task_name, task_desc)
    elif backend_mode == 'cloud':
        from .spinq_cloud_backend import SpinQCloudConfig
        username = kwargs.get('username', None)
        keyfile = kwargs.get('keyfile', None)
        backend = SpinQCloudBackend(username, keyfile)
        config = SpinQCloudConfig()
        platform = kwargs.get('platform', 'triangulum_vp')
        shots = kwargs.get('shots', 1024)
        task_name = kwargs.get('task_name', 'NoName')
        task_desc = kwargs.get('task_desc', 'No description.')
        config.configure_platform(platform)
        config.configure_shots(shots)
        config.configure_task(task_name, task_desc)
    else:
        raise InappropriateBackendError(
            f'The backend mode `{backend_mode}` is not supported.')
    return backend, config
