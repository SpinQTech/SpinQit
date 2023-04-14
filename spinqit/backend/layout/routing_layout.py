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
from typing import List, Tuple
from .layout import Layout

def generate_routing_layout(logical_qubit_num: int, edges: List, physical_qubit_num: int, coupling_map: List[Tuple]) -> List:
    #trivial layout
    init_layout = Layout()
    for i in range(logical_qubit_num):
        init_layout.add_log_to_phy(i, i)
    return init_layout