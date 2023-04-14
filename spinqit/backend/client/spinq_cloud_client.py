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

from .spinq_session import SpinQSession
import json
from typing import Optional

HOST = "http://cloud.spinq.cn:6060"

USER_URI_PREFIX = "/user/spinqit"
PLATFORM_URI_PREFIX = "/platform/spinqit"
TASK_URI_PREFIX = "/task/user"
RETRY_COUNT = 3

class SpinQCloudClient():

    def __init__(self, username, signature, session: Optional[SpinQSession] = None):
        """SipinQCloudClient constructor"""
        self.username = username
        self.signature = signature
        self._session = session if session is not None else SpinQSession()

    @property
    def session(self):
        return self._session

    def _retry_request(self, rquest_func, retry_count, *args):
        res = rquest_func(*args)
        while res.status_code == 401 and retry_count > 0:
            self.login()
            print("Access token timeout. Automatically refreshed identity.")
            res = rquest_func(*args)
            retry_count = retry_count - 1
        return res

    '''
    User API
    '''

    def login(self):
        userinfo = {"username": self.username, "signature": self.signature}
        res = self._session.post(HOST + USER_URI_PREFIX + "/login", data=json.dumps(userinfo))
        res_entity = json.loads(res.content)
        if res:
            access_token = res_entity["token"]
            self.session.setHeader("token", access_token)
        else:
            err_msg = "Authentication failed: " + res_entity["msg"] if res_entity.__contains__("msg") and res_entity["msg"] is not None else "Authentication failed"
            raise Exception(err_msg)

    '''
    Platform API
    '''

    def retrieve_remote_platforms(self):
        return self._session.get(HOST + PLATFORM_URI_PREFIX + "/getPlatformList")

    '''
    Task API
    '''
    def _create_task(self, newTask):
        return self._session.post(HOST + TASK_URI_PREFIX + "/create", data=json.dumps(newTask))

    def create_task(self, newTask, retry_count:int = RETRY_COUNT):
        return self._retry_request(self._create_task, retry_count, newTask)

    def _get_task_by_code(self, task_code: str):
        taskinfo = {"taskCode": task_code}
        return self._session.get(HOST + TASK_URI_PREFIX + "/retrieveTaskInfoByTcode", params=taskinfo)

    def get_task_by_code(self, task_code: str, retry_count:int = RETRY_COUNT):
        return self._retry_request(self._get_task_by_code, retry_count, task_code)

    def _task_status(self, task_code: str):
        taskinfo = {"taskCode": task_code}
        return self._session.get(HOST + TASK_URI_PREFIX + "/retrieveCurrentTaskStatus", params=taskinfo)

    def task_status(self, task_code: str, retry_count:int = RETRY_COUNT):
        return self._retry_request(self._task_status, retry_count, task_code)

    def _task_result(self, task_code: str):
        taskinfo = {"taskCode": task_code}
        return self._session.get(HOST + TASK_URI_PREFIX + "/getTaskRunResultByTcode", params=taskinfo)

    def task_result(self, task_code: str, retry_count:int = RETRY_COUNT):
        return self._retry_request(self._task_result, retry_count, task_code)
    