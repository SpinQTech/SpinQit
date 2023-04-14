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
from typing import Tuple, List
import numpy as np

from spinqit.model import Gate
from .uniformly_controlled_gate import generate_ucg_diagonal


def generate_mcg_diagonal(gate: np.ndarray, ctrl_num: int) -> Tuple[Gate, List]:
    gate_list = [np.eye(2, 2) for i in range(2 ** ctrl_num)]
    gate_list[-1] = gate
    mcg, diag = generate_ucg_diagonal(gate_list, True)
    return mcg, diag
