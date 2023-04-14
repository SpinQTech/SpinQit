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

#ifndef NMR_H
#define NMR_H

#include "model/result.h"
#include "operation.h"
#include "util/constants.h"
using namespace constants;

#include <Python.h>
#include <pybind11/embed.h>
#include <pybind11/pybind11.h>
namespace py = pybind11;

#include <cstring>
#include <vector>
#include <set>
#include <unordered_map>
#include <map>
#include <queue>
#include <sstream>
#include <iostream>
#include <thread>
#include <future>
#include <algorithm>
#include <math.h>
using namespace std;

#ifdef _WIN64
#include "SpinQuasar.h"
#endif

extern "C" {
#include "util/graph_attributes.h"
#include "igraph/igraph.h"
}

inline string convert_to_binary(size_t i, size_t n)
{
    std::ostringstream oss;
    for (size_t j=n; j>=1; j--) {
        size_t pos = n - j;
        oss << ((i>>(j-1)) & 1);
    }
    return oss.str();
}

class Nmr
{
public:
    Nmr() {}
    Result execute(py::capsule graph, py::dict config)
    {
        Result re;
        string ip = "127.0.0.1";
        if (config.contains("ip")) {
            py::object iobj = config["ip"];
            ip = iobj.cast<string>();
        }

        unsigned short port = 55444;
        if (config.contains("port")) {
            py::object pobj = config["port"];
            port = pobj.cast<uint16_t>();
        }

        string username = "";
        if (config.contains("username")) {
            py::object uobj = config["username"];
            username = uobj.cast<string>();
        }

        string password = "";
        if (config.contains("password")) {
            py::object wobj = config["password"];
            password = wobj.cast<string>();
        }

        string task_name = "taskX";
        if (config.contains("task_name")) {
            py::object tnobj = config["task_name"];
            task_name = tnobj.cast<string>();
        }

        string task_desc = "";
        if (config.contains("task_desc")) {
            py::object tdobj = config["task_desc"];
            task_desc = tdobj.cast<string>();
        }

        bool verbose = false;
        if (config.contains("print_circuit")) {
            py::object pcobj = config["print_circuit"];
            verbose = pcobj.cast<bool>();
        }
        
        igraph_t *gptr = (igraph_t *)graph.get_pointer();
        vector<Operation> gate_map; 
        int qnum = translate(gptr, gate_map);

        stringstream ss;
        ss << "[";
        for (size_t j = 0; j < gate_map.size()-1; j++) {
            ss << gate_map[j].to_string();
            ss << ",\n";
        }
        ss << gate_map[gate_map.size()-1].to_string();
        ss << "]";
        string circuit_str = ss.str();
        if (verbose)
            cout<< circuit_str << endl;
        
        vector<double> probabilities;
        #ifdef _WIN64
            SpinQuasar::init(ip, port, username, password);
            probabilities = SpinQuasar::nmr_run(task_name, task_desc, circuit_str, qnum);
        #endif
        size_t sz = probabilities.size();
        for (size_t i = 0; i < sz; i++) {
            string key = convert_to_binary(i, qnum);
            re.probabilities[key] = probabilities[i];
        }

        return re;
    }
private:
    set<int> decompose(const igraph_t* g);
    int update_timelist(vector<int> & time_list, initializer_list<int> qil);
    void expand_caller(const igraph_t *g, const char *gate_name, igraph_vector_t *qubits, igraph_vector_t *params, 
                    vector<int> & time_list, vector<Operation> & gate_map);
    int translate(const igraph_t *g, vector<Operation> & gate_map);
};

#endif