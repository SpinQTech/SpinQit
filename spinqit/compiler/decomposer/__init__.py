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

from .ZYZdecomposer import decompose_zyz
from .magic_basis_decomposer import decompose_two_qubit_gate
from .isometry_decomposer import build_gate_for_isometry
from .uniformly_controlled_rotation_gate import generate_uc_rot_gates
from .diagonal import generate_diagonal_gates
from .uniformly_controlled_gate import generate_ucg_diagonal
from .multi_controlled_gate import generate_mcg_diagonal