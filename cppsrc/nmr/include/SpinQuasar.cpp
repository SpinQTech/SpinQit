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

#include "SpinQuasar.h"
#include "nlohmann/json.hpp"
using json = nlohmann::json;

bool  SpinQuasar::running = true;
bool  SpinQuasar::loggedon = false;
vector<double> SpinQuasar::probabilities;
string SpinQuasar::username = "";
string SpinQuasar::password = "";

void SpinQuasar::init(const string& ip, const unsigned short port, const string& user, const string& pwd) {
    set_on_closed_callback(SpinQuasar::on_close);
    set_on_failed_callback(SpinQuasar::on_failed);
    set_on_opened_callback(SpinQuasar::on_opened);
    set_login_response_callback(SpinQuasar::on_login_response);
    set_push_task_response_callback(SpinQuasar::on_push_task_response);
    set_task_finished_post_callback(SpinQuasar::on_task_finished_post_callback);
    
    username = user;
    password = pwd;
    connect_to_server(ip.c_str(), port);
    int wait_sec = 0;
    const int login_timeout = 20;
    for (wait_sec=0; wait_sec<login_timeout && loggedon == false; wait_sec++) {
        this_thread::sleep_for(chrono::seconds(1));
    }
    if (wait_sec == login_timeout) {
        std::cerr << "Login timeout!" << std::endl;
        throw std::runtime_error("Login timeout!");
    }
}

vector<double> SpinQuasar::nmr_run(const string& task_name, const string& task_desc, const string& circuit, int qnum) {
    running = true;
    if (qnum > 3) {
        std::cerr << "Currently the quantum computer supports no more than 3 qubits." << std::endl;
        throw std::runtime_error("Currently the quantum computer supports no more than 3 qubits.");
    }

    probabilities.clear();
    unsigned long long status = push_task_request(task_name.c_str(), task_desc.c_str(), circuit.c_str(), qnum);
    if (status == -1) {
        std::cerr << "Sending message failed! Please check your network and try again later." << std::endl;
        throw std::runtime_error("Sending message failed! Please check your network and try again later.");
    }

    while(running) {
        this_thread::sleep_for(chrono::seconds(1));
    }
   
    disconnect_from_server();
    this_thread::sleep_for(chrono::seconds(1));
    return probabilities;
}

void SpinQuasar::on_opened()
{
    std::cout << "Connect to server successfully!" << std::endl;
    if (request_login(username.c_str(), password.c_str()) != 0) {
        std::cout << __FUNCTION__ << "Send request-login message failed!" << std::endl;
    }
}

void SpinQuasar::on_close()
{
    std::cout << "The connection has been closed!" << std::endl;
    running = false;
    loggedon = false;
}

void SpinQuasar::on_failed()
{
    std::cerr << "Connect to server failed!" << std::endl;
    throw std::runtime_error("Connect to server failed!");
}

void SpinQuasar::on_login_response(const char *msg)
{
    string result_msg(msg);
    json jsonData = json::parse(result_msg);
    int code = jsonData["return_code"];
    if (code != 0) {
        std::cerr << "Login failed!" << std::endl;
        throw std::runtime_error("Login failed!");
    }
    loggedon = true;       
}

void SpinQuasar::on_push_task_response(const char *msg)
{
    string result_msg(msg);
    json jsonData = json::parse(result_msg);
    int code = jsonData["return_code"];
    if (code != 0) {
        std::cerr << "The machine is not ready for the task." << std::endl;
        throw std::runtime_error("The machine is not ready for the task.");
    }
}

void SpinQuasar::on_task_finished_post_callback(const char *msg)
{
    string result_msg(msg);
    json jsonData = json::parse(result_msg);
    probabilities.clear();
    string state = jsonData["task_state"];
    if (state=="S") {
        auto resObj = jsonData["task_result"];
        std::vector<double> res = resObj["execution"];
        probabilities = res; 
    } else {
        string task_id = jsonData["task_id"];
        std:cerr << "The task " << task_id << " failed!" << std::endl;
        throw std::runtime_error("Task failed!");
    }
        
    SpinQuasar::running = false;
}