/**
 * Copyright 2021 SpinQ Technology Co., Ltd.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifndef SPINQUASAR_H
#define SPINQUASAR_H
#include "SpinQUser.h"
#include "SpinQInterface.h"

#include <cstring>
#include <stdlib.h>
#include <vector>
#include <string>
#include <sstream>
#include <thread>
#include <chrono>
#include <iostream>
using namespace std;

class SpinQuasar {
private:
    static bool running;
    static vector<double> probabilities;
    static string username;
    static string password;
public:
    static void init(const string& ip, const unsigned short port, const string& user, const string& pwd);
    static vector<double> nmr_run(const string& task_name, const string& task_desc, const string& circuit, int qnum);
    static void on_opened();
    static void on_close();
    static void on_failed();
    static void on_login_response(const char *msg);
    static void on_push_task_response(const char *msg);
    static void on_task_finished_post_callback(const char *msg);
};
#endif