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

import json
import time, datetime
from typing import Optional
from .circuit import Circuit
from spinqit.backend.client.spinq_cloud_client import SpinQCloudClient
from ..exceptions import *
from math import log
import enum

SRC_TYPE_SPINQIT = "spinqit"

class TaskStatus(enum.Enum):
    pending = "PEN"
    queue = "Q"
    processing = "PRO"
    sccueeded = "S"
    failed = "F"
    deleted = "DELETED"

def intToBinary(n, digits=-1):
    b = [] 
    while True:  
        s = n // 2  
        y = n % 2  
        b = b + [y]  
        if s == 0:
            break  
        n = s
    b.reverse() 
    b = [ str(i) for i in b ]
    res = ''.join(b)
    while digits > 0 and len(res) < digits:
        res = "0" + res
    return res

def phy_to_log_model_key_mapping(model_key: str, phy_to_log_mapping: dict):
    res = '0'*len(model_key)
    for i in range(len(model_key)):
        log_bit = phy_to_log_mapping[i]
        res = res[:log_bit] + model_key[i] + res[log_bit+1:len(res)]
    return res

class Task:
    def __init__(self, name: str = "Untitled Task", platform_code: Optional[str] = None, circuit: Optional[Circuit] = None, phy_to_log_mapping: dict = None, calc_matrix: bool = False, shots: Optional[int] = None, process_now: bool = True, description: str = None, api_client: Optional[SpinQCloudClient] = None):
        self._api_client = api_client
        self.task_name = name
        self._bitnum = 0
        self._active_bits = []
        self._platform_code = platform_code
        if phy_to_log_mapping is not None:
            # mapping between logic and physical qubits
            # bitnum and active bits get from this mapping
            # if get from circuit, has problem than bitnum acutally less than registed
            self.set_phy_to_log_mapping(phy_to_log_mapping)
        self._calc_matrix = calc_matrix
        self._shots = shots
        self._source_type = SRC_TYPE_SPINQIT
        self._processNow = process_now
        self.description = description
        self._circuit = None
        self._circuit = circuit
        # Properties should not have value before sending to the cloud server
        self._task_code = None
        self._status = None
        self._created_time = None

    @property
    def platform_code(self):
        return self._platform_code

    @property
    def circuit(self):
        return self.circuit

    @property
    def task_code(self):
        return self._task_code

    @property
    def phy_to_log_mapping(self):
        return self._phy_to_log_mapping

    @property
    def created_time(self):
        return self._created_time

    @property
    def calc_matrix(self):
        return self._calc_matrix

    @property
    def shots(self):
        return self._shots

    @property
    def status(self):
        return self._status

    def set_api_client(self, api_client: SpinQCloudClient):
        self._api_client = api_client

    def set_platform_code(self, platform_code: str):
        self._platform_code = platform_code

    def set_circuit(self, circuit: Circuit):
        self._circuit = circuit

    def set_calc_matrix(self, calc_matrix: bool):
        self._calc_matrix = calc_matrix

    def set_shots(self, shots: int):
        self._shots = shots
    
    def set_phy_to_log_mapping(self, phy_to_log_mapping: dict):
        self._phy_to_log_mapping = phy_to_log_mapping
        self._bitnum = len(phy_to_log_mapping)
        self._active_bits = [i+1 for i in list(phy_to_log_mapping.keys())]

    def set_task_code(self, code: str):
        self._task_code = code

    def set_status(self, status: str):
        self._status = status

    def set_created_time(self, created_time: Optional[datetime.datetime]):
        self._created_time = created_time

    def get_status(self):
        res = self._api_client.task_status(self._task_code)
        if res:
            res_entity = json.loads(res.content)
            return res_entity["taskStatus"]
        else:
            raise SpinQCloudServerError("Retrieve task status failed")

    def get_result(self, hanging:bool = True, timeout:Optional[int] = None):
        start_time = datetime.datetime.now()
        if timeout is not None:
            end_time = start_time + datetime.timedelta(seconds=timeout)
        count = 0
        while (timeout is None or datetime.datetime.now() < end_time):
            count = count + 1
            try:
                res = self._get_result()
                return res
            except TaskStatusError as eo:
                if hanging:
                    time.sleep(5)
                    continue
                else:
                    raise Exception(str(eo))
            except Exception as eo :
                raise Exception(str(eo))
        raise RequestTimeoutError("Find result timeout.")

    def _get_result(self):
        res = self._api_client.task_result(self._task_code)
        res_entity = json.loads(res.content)
        if res.status_code == 200:
            module_list = res_entity["run"]["module"]
            bitnum = int(log(len(module_list), 2))
            module_map = {}
            for idx, m in enumerate(module_list):
                k = intToBinary(idx, bitnum)
                k = phy_to_log_model_key_mapping(k, self._phy_to_log_mapping)
                module_map[k] = m
            return module_map
        elif res.status_code == 202:
            raise SpinQCloudServerError("Task failed while processing.")
        elif res.status_code == 206:
            raise SpinQCloudServerError(res_entity["msg"])
        elif res.status_code == 412:
            raise TaskStatusError(res_entity["msg"])
        else:
            if res_entity is not None and res_entity["msg"] is not None:
                raise SpinQCloudServerError(res_entity["msg"])
            else:
                raise SpinQCloudServerError("Retrieve task status failed")

    def to_dict(self):
        task_dict = {
            "tcode": self._task_code,
            "tname": self.task_name,
            "description": self.description,
            "created_time": self._created_time.strftime('%Y-%m-%d %H:%M:%S.%f%z') if self._created_time is not None else None,
            "bitNum": self._bitnum,
            "calc_matrix": self._calc_matrix,
            "platform_code": self._platform_code,
            "circuit": self._circuit,
            "active_bits": self._active_bits
        }
        return task_dict

    def to_request(self):
        task_dict = {
            "tname": self.task_name,
            "bitNum": self._bitnum,
            "sourceType": self._source_type,
            "calcMatrix": self._calc_matrix,
            "simulator": False,
            "proceedNow": self._processNow,
            "platformCode": self._platform_code,
            "description": self.description,
            "circuit": self._circuit.to_dict(),
            "activeBits": self._active_bits,
            "shots": self._shots
        }
        return task_dict
