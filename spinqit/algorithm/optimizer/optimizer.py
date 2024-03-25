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


class Optimizer:

    def optimize(self, *args, **kwargs):
        """
        The whole optimization process
        """
        return

    def step_and_cost(self, *args, **kwargs):
        """
        Every single step for gradients and loss calculation
        """
        return

    def reset(self, *args, **kwargs):
        """
        reset the optimizer step and other arguments
        """
        return

    def check_optimize_done(self, *args, **kwargs):
        """
        Check whether the optimization process has reached the end.
        """
        return