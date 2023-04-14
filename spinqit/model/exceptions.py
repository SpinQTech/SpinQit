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


class SpinQError(Exception):

    def __init__(self, *message):
        super().__init__(" ".join(message))
        self.message = " ".join(message)
    
    def __str__(self):
        return repr(self.message)

class UnsupportedGateError(SpinQError):
    pass

class UnsupportedQiskitInstructionError(SpinQError):
    pass

class InappropriateBackendError(SpinQError):
    pass

class SpinQCloudServerError(SpinQError):
    pass

class RequestPreconditionFailedError(SpinQError):
    pass

class NotFoundError(SpinQError):
    pass

class TaskStatusError(SpinQError):
    pass

class CircuitOperationValidationError(SpinQError):
    pass

class CircuitOperationParsingError(SpinQError):
    pass

class RequestTimeoutError(SpinQError):
    pass

class OptimizerError(SpinQError):
    pass

class DecomposerError(SpinQError):
    pass

class RoutingError(SpinQError):
    pass