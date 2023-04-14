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

#define _USE_MATH_DEFINES
#include "include/nmr.h"

inline double radian_to_angle(double radian)
{
    return fmod(radian, 4 * M_PI) / M_PI * 180;
}

set<int> Nmr::decompose(const igraph_t* g)
{
    set<int> backbone;
    vector<int> registers;
    set<int> visited;
    igraph_vs_t adj_vs;
    igraph_vit_t adj_vit;

    get_vertex_id_list_by_attr(g, node_type_attr, node_type_register, registers);
    for (auto ite = registers.begin(); ite != registers.end(); ++ite) {
        if (visited.find(*ite) == visited.end()) {
            queue<int> vid_queue;
            vid_queue.push(*ite);
            while (!vid_queue.empty()) {
                int v = vid_queue.front();
                vid_queue.pop();
                if (visited.find(v) == visited.end()) {
                    backbone.insert(v);
                    visited.insert(v);
                    igraph_vs_adj(&adj_vs, v, IGRAPH_ALL);
                    igraph_vit_create(g, adj_vs, &adj_vit);
                    while (!IGRAPH_VIT_END(adj_vit)) {
                        vid_queue.push((int)IGRAPH_VIT_GET(adj_vit));
                        IGRAPH_VIT_NEXT(adj_vit);
                    }
                    igraph_vit_destroy(&adj_vit);
                    igraph_vs_destroy(&adj_vs);
                }
            }
        }
    }
    return backbone;
}

int Nmr::update_timelist(vector<int> & time_list, initializer_list<int> qil)
{
    size_t qsz = qil.size();

    int gate_time_slot = -1;
    auto qit = qil.begin();
    if (qsz == 1) {
        gate_time_slot = time_list[*qit];
        time_list[*qit] = gate_time_slot + 1;
    } else if (qsz == 2) {
        int last0 = time_list[*qit];
        int last1 = time_list[*(qit+1)];
        gate_time_slot = last0 > last1 ? last0 : last1;
        time_list[*qit] = time_list[*(qit+1)] = gate_time_slot + 1;
    } else if (qsz == 3) {
        int last0 = time_list[*qit];
        int last1 = time_list[*(qit+1)];
        int last2 = time_list[*(qit+2)];
        gate_time_slot = max({last0, last1, last2});
        time_list[*qit] = time_list[*(qit+1)] = time_list[*(qit+2)] = gate_time_slot + 1;
    }

    return gate_time_slot;
}

void Nmr::expand_caller(const igraph_t *g, const char *gate_name, igraph_vector_t *qubits, igraph_vector_t *params, 
                            vector<int> & time_list, vector<Operation> & gate_map)
{
    igraph_integer_t root;
    get_vertex_id_by_attr(g, gate_def, gate_name, &root);

    igraph_vector_t callees;
    igraph_vector_init(&callees, 0);
    topological_sorting_from_vertex(g, root, &callees);

    char *callee_name;
    igraph_es_t callee_es;
    igraph_vector_t qindex_list;
    igraph_vector_t qubit_list;
    igraph_vector_t pindex_list;
    igraph_vector_t param_list;
    
    int gate_time_slot = -1;
    int i;
    for (i = 0; i < igraph_vector_size(&callees); i++) {
        igraph_integer_t callee = VECTOR(callees)[ (long int)i ];
        
        get_string_vertex_attr(g, node_name_attr, callee, &callee_name);

        igraph_es_incident(&callee_es, callee, IGRAPH_IN);       
        igraph_vector_init(&qindex_list, 0);
        igraph_vector_init(&pindex_list, 0);
        igraph_vector_init(&param_list, 0);

        get_numeric_edge_attrs(g, edge_qubit_attr, callee_es, &qindex_list);

        gate_time_slot = -1;
        long int qsize = igraph_vector_size(&qindex_list);
        igraph_vector_init(&qubit_list, qsize); 

        for (long i = 0; i < qsize; i++) {
            igraph_integer_t index = VECTOR(qindex_list)[i];
            VECTOR(qubit_list)[i] = VECTOR(*qubits)[index]; 
        }
    
        get_numeric_list_vertex_attr(g, node_params_index, callee, &pindex_list);
        long int psize = igraph_vector_size(&pindex_list);
        
        int err_code = exec_callable_vertex_attr(g, node_params_attr, callee, params, &pindex_list, psize, &param_list);
        if (err_code != 0) {
            throw std::runtime_error("Something is wrong with callee parameters.");
        }
        
        igraph_real_t type = node_type_callee;
        get_numeric_vertex_attr(g, node_type_attr, callee, &type);
        if (((igraph_integer_t)type) == node_type_caller) {
            expand_caller(g, callee_name, &qubit_list, &param_list, time_list, gate_map);
        } else {
            int qb0 = (int)VECTOR(qubit_list)[0];
            if (qsize == 1) {
                gate_time_slot = time_list[qb0];
                if (igraph_vector_size(&param_list) > 0) {
                    igraph_real_t theta = VECTOR(param_list)[0];
                    double angle = radian_to_angle((double)theta);
                    gate_map.emplace_back(callee_name, gate_time_slot, qb0, angle);
                } else {
                    gate_map.emplace_back(callee_name, gate_time_slot, qb0);
                }
            } else if (qsize == 2) {
                int qb1 = (int)VECTOR(qubit_list)[1];
            
                gate_time_slot = update_timelist(time_list, {qb0, qb1});
                gate_map.emplace_back(callee_name, gate_time_slot, qb0, qb1);
            } else if (qsize == 3) {
                int qb1 = (int)VECTOR(qubit_list)[1];
                int qb2 = (int)VECTOR(qubit_list)[2];
                gate_time_slot = update_timelist(time_list, {qb0, qb1, qb2});
                gate_map.emplace_back(callee_name, gate_time_slot, qb0, qb1, qb2);
            }
        }
    }

    free(callee_name);
    igraph_es_destroy(&callee_es);
    igraph_vector_destroy(&qindex_list);
    igraph_vector_destroy(&pindex_list);
}

int Nmr::translate(const igraph_t *g, vector<Operation> & gate_map)
{
    igraph_vector_t vs_res;
    igraph_vector_init(&vs_res, 0);

    set<int> backbone = decompose(g);
    vector<int> vids;
    igraph_topological_sorting(g, &vs_res, IGRAPH_OUT);
    for (int j = 0; j < igraph_vector_size(&vs_res); j++)
    {
        int vid = VECTOR(vs_res)[j];
        if (backbone.find(vid) != backbone.end()) {
            vids.push_back(vid);
        }
    }
    
    int qnum = (int)get_numeric_graph_attr(g, qubit_num_attr);
    if (qnum <= 0) return qnum;

    vector<int> time_list(qnum, 0);

    igraph_es_t es;
    igraph_vector_t qubit_res;
    igraph_vector_t params_res;

    for (size_t i = 0; i < vids.size(); i++) {
        int vid = vids[i];

        igraph_vector_init(&qubit_res, 0);
        igraph_vector_init(&params_res, 0);
    
        char *gate_name;
        get_string_vertex_attr(g, node_name_attr, vid, &gate_name);

        igraph_real_t type = node_type_op;
        get_numeric_vertex_attr(g, node_type_attr, vid, &type);

        igraph_es_incident(&es, vid, IGRAPH_IN);
        get_numeric_edge_attrs(g, edge_qubit_attr, es, &qubit_res);
        get_numeric_list_vertex_attr(g, node_params_attr, vid, &params_res);

        int gate_time_slot = -1;
        if ( (igraph_integer_t)type == node_type_op) {
            
            long int qsize = igraph_vector_size(&qubit_res);
            int qb0 = (int)VECTOR(qubit_res)[0];

            if (qsize == 1) {
                gate_time_slot = update_timelist(time_list, {qb0});
                
                if (igraph_vector_size(&params_res) > 0) {
                    igraph_real_t theta = VECTOR(params_res)[0];
                    double angle = radian_to_angle((double)theta);
                    gate_map.emplace_back(gate_name, gate_time_slot, qb0, angle);  
                } else {
                    gate_map.emplace_back(gate_name, gate_time_slot, qb0);
                }
            } else if (qsize == 2) {
                int qb1 = (int)VECTOR(qubit_res)[1];
                
                gate_time_slot = update_timelist(time_list, {qb0, qb1});
                gate_map.emplace_back(gate_name, gate_time_slot, qb0, qb1);
            } else if (qsize == 3) {
                int qb1 = (int)VECTOR(qubit_res)[1];
                int qb2 = (int)VECTOR(qubit_res)[2];

                gate_time_slot = update_timelist(time_list, {qb0, qb1, qb2});
                gate_map.emplace_back(gate_name, gate_time_slot, qb0, qb1, qb2);
            }
        } else if ( (igraph_integer_t)type == node_type_caller) {
            expand_caller(g, gate_name, &qubit_res, &params_res, time_list, gate_map);
        }
    
        free(gate_name);
        igraph_es_destroy(&es);
        igraph_vector_destroy(&qubit_res);
        igraph_vector_destroy(&params_res);
    }

    return qnum;
}