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
from .amplitude_amplification import AmplitudeAmplification
from .phase_estimation import PhaseEstimation
from .qft import QFT
from .pauli_builder import PauliBuilder
from .reciprocal import Reciprocal
from .vector_encoding import amplitude_encoding, angle_encoding, iqp_encoding
from .power import generate_power_gate
from .pauli_expectation import calculate_pauli_expectation, generate_hamiltonian_matrix, pauli_decompose
from .ae_Q_builder import QOperatorBuilder
from .multi_controlled_gate_builder import MultiControlledGateBuilder
from .uniformly_controlled_gate_builder import UniformlyControlledGateBuilder
from .two_qubit_state_preparation import TwoQubitStatePreparationGateBuilder
from .tapering import taper_off_qubits, generate_symmetry_generator, generate_sector