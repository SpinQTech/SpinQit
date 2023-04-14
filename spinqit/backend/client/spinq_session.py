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

from requests import Session, RequestException, Response
from requests.adapters import HTTPAdapter

class SpinQSession(Session):
    
    def __init__(self):
        """SipinQSession constructor"""
        super().__init__()
        self.headers.update({'Content-Type': 'application/json'})

    def setHeader(self, key: str, value: str):
        self.headers.update({key: value})