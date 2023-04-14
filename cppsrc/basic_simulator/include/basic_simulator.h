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

#ifndef BASIC_SIMULATOR_H
#define BASIC_SIMULATOR_H

#include "model/result.h"
#include "utilities/circuit.h"
#include "algorithm/state_manager.h"
#include "utilities/gates.h"
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
#include <queue>
#include <iostream>
#include <thread>
#include <future>
#include <algorithm>
#include <initializer_list>

using namespace std;

extern "C" {
#include "util/graph_attributes.h"
#include "igraph/igraph.h"
}

class BasicSimulator
{
public:
    BasicSimulator();
    ~BasicSimulator();

    Result execute(py::capsule graph, py::dict config)
    {
        Result re;
        vector<StateType> sv;
        vector<double> ps;

        igraph_t *gptr = (igraph_t *)graph.get_pointer();
        igraph_vector_t vs_res;
        igraph_vector_init(&vs_res, 0);
        igraph_topological_sorting(gptr, &vs_res, IGRAPH_OUT);

        bool parallel = false;
        if (config.contains("parallel")) {
            py::object pobj = config["parallel"];
            parallel = pobj.cast<bool>();
        }

        bool verbose = false;
        if (config.contains("print_circuit")) {
            py::object pcobj = config["print_circuit"];
            verbose = pcobj.cast<bool>();
        }

        if (parallel) {
            vector<set<int>> complist = decompose(gptr);
        
            vector<future<vector<double>>> results;
            for (int i = 0; i < complist.size(); i++) {
                vector<int> vids;
                for (int j = 0; j < igraph_vector_size(&vs_res); j++) {
                    int vid = VECTOR(vs_res)[j];
                    if (complist[i].find(vid) != complist[i].end()) {
                        vids.push_back(vid);
                    }
                }

                int qnum = get_vertex_num_by_attr(gptr, node_type_attr, node_type_init_qubit, 
                                            (igraph_integer_t*)vids.data(), vids.size());

                int cnum = get_vertex_num_by_attr(gptr, node_type_attr, node_type_init_clbit,
                                            (igraph_integer_t*)vids.data(), vids.size());

                if (qnum > 0) {
                    results.push_back(std::async(launch::async, &BasicSimulator::simulate, this, gptr, std::ref(vids), 
                                      qnum, cnum, std::ref(sv), verbose));
                }
            }
            
            //ToDo: combine the parallel results
            ps = results[0].get();
        } else {
            vector<set<int>> complist = decompose(gptr);
            vector<int> vids;
            for (size_t i = 0; i < complist.size(); i++) {
                for (int j = 0; j < igraph_vector_size(&vs_res); j++) {
                    int vid = VECTOR(vs_res)[j];
                    if (complist[i].find(vid) != complist[i].end()) {
                        vids.push_back(vid);
                    }
                }
            }
            int qnum = get_numeric_graph_attr(gptr, qubit_num_attr);
            int cnum = get_numeric_graph_attr(gptr, clbit_num_attr);

            ps = std::move(simulate(gptr, vids, qnum, cnum, sv, verbose));
        }
       
        igraph_vector_destroy(&vs_res);
        
        int shots = 1024;
        if (config.contains("shots")) {
            py::object sobj = config["shots"];
            shots = sobj.cast<int>();
        }
        set<int> bitpos;
        if (config.contains("mqubits")) {
            py::list mlist = config["mqubits"];
            for (auto item: mlist) bitpos.insert(item.cast<int>());
        }
        
        re.probabilities = std::move(pack_probabilities(ps, bitpos));
        re.counts = std::move(calc_counts(re.probabilities, shots));
        re.states = std::move(sv);
    
        return re;
    }
    
private:
    map<string, double> pack_probabilities(const vector<double>& probabilities, const set<int>& mqubits);
    map<string, int> calc_counts(const map<string, double>& probabilities, int shots);
    vector<set<int>> decompose(const igraph_t* g);
    size_t append_to_timelist(vector<vector<gate_unit>> & time_list, const char* gate_name, const initializer_list<size_t> & qil, const initializer_list<double> & pil, const condition & cond);
    size_t add_measurement(vector<vector<gate_unit>> & time_list, const vector<size_t> & qubits, const vector<size_t> & clbits);
    size_t add_element(const igraph_t *g, igraph_integer_t vid, unordered_map<int, size_t> & qreg_map, 
                    unordered_map<int, size_t> & creg_map, vector<vector<gate_unit>> & time_list);
    size_t expand_caller(const igraph_t *g, const char *gate_name, igraph_vector_t *qubits, igraph_vector_t *params, const condition & cond, 
                    unordered_map<int, size_t> & qreg_map, unordered_map<int, size_t> & creg_map, vector<vector<gate_unit>> & time_list);
    circuit translate(const igraph_t *g, vector<int> & component, int qnum, int cnum);
    vector<double> simulate(const igraph_t *g, vector<int>& component, int qnum, int cnum, vector<StateType>& state, bool verbose);
};


#endif