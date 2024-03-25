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
from .random_circuit import generate_random_circuit
from .hhl import HHL
from .qaoa import QAOA
from .vqe import VQE
from .quantum_counting import QuantumCounting
from .optimizer import *
from .shor import Shor
from .grover_seach import QSearching
from .amplitude_estimation import AmplitudeEstimation
from .iterative_amplitude_estimation import IterativeAmplitudeEstimation
from .ml_amplitude_estimation import MaximumLikelihoodAmplitudeEstimation
from .qsvc import QSVC
from .coined_quantum_walk import CoinedQuantumWalk