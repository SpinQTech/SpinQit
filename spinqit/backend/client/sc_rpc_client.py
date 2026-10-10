# Copyright 2024 SpinQ Technology Co., Ltd.
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
from typing import List
import json
import enum
import time
import zerorpc

class Operation:
    def __init__(self, name: str, timeslot: int, qubits: List, params = None):
        self.name = name
        self.timeslot = timeslot
        self.qubits = qubits
        self.params = params

    def to_dict(self):
        op_dict = {"type": self.name, "timeslot": self.timeslot, "controlQubit": -1}
        if len(self.qubits) == 1:
            op_dict["qubitIndex"] = self.qubits[0]
        elif len(self.qubits) == 2:
            op_dict["controlQubit"] = self.qubits[0]
            op_dict["qubitIndex"] = self.qubits[1]
        if self.params is not None and len(self.params)>0:
            op_dict["angle"] = self.params[0]
        return op_dict

class TaskStatus(enum.Enum):
    finished = 0
    failed = 1
    running = 2
    queueing = 3
    notfound = 4
    
class SC_Client:
    MAX_RETRIES = 3
    def __init__(self, ip, port):
        self.client = zerorpc.Client()
        self.ip = ip
        self.port = str(port)
        self.client.connect("tcp://"+self.ip+":"+self.port)

    def connect_to_machine(self, username, password):
        self.username = username
        retry_count = 0
        return_code = 1
        while retry_count < self.MAX_RETRIES:
            try:
                rep_msg = self.client.request_login(username, password)
                rep = json.loads(rep_msg)
                return_code = rep["return_code"]
                break
            except (zerorpc.exceptions.LostRemote, zerorpc.exceptions.RemoteError) as e:
                self.client.close()
                time.sleep(1)
                self.client.connect("tcp://"+self.ip+":"+self.port)
                retry_count += 1
            except Exception as e:
                print(f"A RPC error occurred: {e}")
                raise 
        
        if return_code == 1:
            raise ValueError("Failed to log into the superconducting quantum computer.")
        self.session_id = rep["session_id"]
        self.chip_name = rep["chip_name"]
        phy_qubit_list = rep["qubits_list"]
        qnum = rep["qubits_num"]
        coupling_list = [tuple(pair) for pair in rep["coupling_list"]]
        
        return phy_qubit_list, coupling_list

    def submit_task(self, task_name: str, operations: List, measures: List, task_desc: str, shots: int) -> int:      
        # op_json = json.dumps([obj.to_dict() for obj in operations])
        task_gates = [obj.to_dict() for obj in operations]
        retry_count = 0
        while retry_count < self.MAX_RETRIES:
            try:
                status, task_id = self.client.push_task(task_name, task_gates, measures, task_desc, shots, self.session_id)
                if status == 0:
                    return task_id
                else:
                    time.sleep(1)
                    retry_count += 1
            except (zerorpc.exceptions.LostRemote, zerorpc.exceptions.RemoteError) as e:
                self.client.close()
                time.sleep(1)
                self.client.connect("tcp://"+self.ip+":"+self.port)
                retry_count += 1
            except Exception as e:
                print(f"A RPC error occurred: {e}")
                raise 
        raise TimeoutError("Task submission failed.")

    def get_task_status(self, task_id):
        flag = TaskStatus.failed
        retry_count = 0
        while retry_count < self.MAX_RETRIES:
            try:
                flag = self.client.get_task_status(task_id, self.session_id)
                return flag
            except (zerorpc.exceptions.LostRemote, zerorpc.exceptions.RemoteError) as e:
                self.client.close()
                time.sleep(1)
                self.client.connect("tcp://"+self.ip+":"+self.port)
                retry_count += 1
            except Exception as e:
                print(f"A RPC error occurred: {e}")
                break
        raise TimeoutError("Cannot get the task status from the quantum computer.")

    def get_task_result(self, task_id):
        result = {}
        retry_count = 0
        while retry_count < self.MAX_RETRIES:
            try:
                res_json = self.client.get_task_result(task_id, self.session_id)
                result = json.loads(res_json)
                return result
            except (zerorpc.exceptions.LostRemote, zerorpc.exceptions.RemoteError) as e:
                self.client.close()
                time.sleep(1)
                self.client.connect("tcp://"+self.ip+":"+self.port)
                retry_count += 1
            except Exception as e:
                print(f"A RPC error occurred: {e}")
                break
        raise TimeoutError("Cannot get the task result from the quantum computer.")

    def logout_machine(self):
        self.client.request_logout(self.username, self.session_id)
        self.client.close()