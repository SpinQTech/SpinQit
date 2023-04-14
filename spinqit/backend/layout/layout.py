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

from typing import Dict

class Layout(object):
    def __init__(self):
        self.log_to_phy = {}
        self.phy_to_log = {}

    def swap_by_physical(self, qubit1: int, qubit2: int):
        lq1 = self.phy_to_log[qubit1]
        lq2 = self.phy_to_log[qubit2]
        self.phy_to_log[qubit2] = lq1
        self.phy_to_log[qubit1] = lq2
        self.log_to_phy[lq1] = qubit2
        self.log_to_phy[lq2] = qubit1

    def add_log_to_phy(self, log: int, phy: int):
        self.log_to_phy[log] = phy
        self.phy_to_log[phy] = log

    def add_phy_to_log(self, phy: int, log: int):
        self.phy_to_log[phy] = log
        self.log_to_phy[log] = phy

    def copy(self):
        another = Layout()
        another.log_to_phy = self.log_to_phy.copy()
        another.phy_to_log = self.phy_to_log.copy()
        return another