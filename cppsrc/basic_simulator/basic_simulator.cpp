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
#include "include/basic_simulator.h"
#include <stdio.h>
#include <sstream>
#include <cmath>
#include <stdlib.h>

inline double radian_to_angle(double radian)
{
    return fmod(radian, 4 * M_PI) / M_PI * 180;
}

BasicSimulator::BasicSimulator(/* args */) {    
}

BasicSimulator::~BasicSimulator() {
}

// vector<set<int>> BasicSimulator::decompose(const igraph_t* g) 
// {
//     vector<set<int>> results;
//     std::set<int> all_nodes;
//     igraph_vs_t vs;
//     igraph_vit_t vit;
//     igraph_vs_t adj_vs;
//     igraph_vit_t adj_vit;

//     igraph_vs_all(&vs);
//     igraph_vit_create(g, vs, &vit);

//     while (!IGRAPH_VIT_END(vit)) {
//         all_nodes.insert((int)IGRAPH_VIT_GET(vit));
//         IGRAPH_VIT_NEXT(vit);
//     }
    
//     while(!all_nodes.empty()) {
//         std::set<int> component;
//         std::set<int>::iterator it = all_nodes.begin();
        
//         queue<int> vid_queue;
//         vid_queue.push(*it);
//         while (!vid_queue.empty()) {
//             int v = vid_queue.front();
//             vid_queue.pop();
//             if (all_nodes.find(v) != all_nodes.end()) {
//                 component.insert(v);
//                 all_nodes.erase(v);
//                 igraph_vs_adj(&adj_vs, v, IGRAPH_ALL);
//                 igraph_vit_create(g, adj_vs, &adj_vit);
//                 while (!IGRAPH_VIT_END(adj_vit)) {
//                     vid_queue.push((int)IGRAPH_VIT_GET(adj_vit));
//                     IGRAPH_VIT_NEXT(adj_vit);
//                 }
//                 igraph_vit_destroy(&adj_vit);
//                 igraph_vs_destroy(&adj_vs);
//             }
//         }

//         results.push_back(component);
//     }

//     igraph_vit_destroy(&vit);
//     igraph_vs_destroy(&vs);
    
//     return results;
// }

vector<set<int>> BasicSimulator::decompose(const igraph_t* g) {
    vector<set<int>> results;
    vector<int> registers;
    set<int> visited;
    igraph_vs_t adj_vs;
    igraph_vit_t adj_vit;

    get_vertex_id_list_by_attr(g, node_type_attr, node_type_register, registers);
    for (auto ite = registers.begin(); ite != registers.end(); ++ite) {
        if (visited.find(*ite) == visited.end()) {
            queue<int> vid_queue;
            vid_queue.push(*ite);
            std::set<int> component;
            while (!vid_queue.empty()) {
                int v = vid_queue.front();
                vid_queue.pop();
                if (visited.find(v) == visited.end()) {
                    component.insert(v);
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
            results.push_back(component);
        }
    }

    return results;
}


inline void append_I_gate(vector<vector<gate_unit>> & time_list, size_t qubit, int timeslot, int last)
{
    for (int k = 0; k < (timeslot - last); k++) {
        time_list[qubit].emplace_back("I", qubit);
    }
    time_list[qubit].emplace_back(INVALID_GATE, qubit);
}

inline size_t BasicSimulator::append_to_timelist(vector<vector<gate_unit>> & time_list, const char* gate_name, const initializer_list<size_t> & qil, const initializer_list<double> & pil, const condition & cond)
{
    size_t qsz = qil.size();
    size_t psz = pil.size();

    size_t gate_time_slot = 0;
    auto qit = qil.begin();
    gate_unit g;
    if (qsz == 1) {
        gate_time_slot = time_list[*qit].size();
        if (psz > 0) {
            g = gate_unit(gate_name, *qit, *(pil.begin()));
        } else {
            g = gate_unit(gate_name, *qit);
        }
        if (cond.isValid()) {
            g.setCondition(cond);
        }
        time_list[*qit].push_back(g);
    } else if (qsz == 2) {
        int last0 = time_list[*qit].size();
        int last1 = time_list[*(qit+1)].size();
        gate_time_slot = last0 > last1 ? last0 : last1;
        
        g = gate_unit(gate_name, *qit, *(qit+1));
        if (cond.isValid()) g.setCondition(cond);
        if (gate_time_slot == last0) {  
            time_list[*qit].push_back(g);
            append_I_gate(time_list, *(qit+1), gate_time_slot, last1);
        } else {
            time_list[*(qit+1)].push_back(g);
            append_I_gate(time_list, *qit, gate_time_slot, last0);
        }
    } else if (qsz == 3) {
        int last0 = time_list[*qit].size();
        int last1 = time_list[*(qit+1)].size();
        int last2 = time_list[*(qit+2)].size();
        gate_time_slot = max({last0, last1, last2});
        g = gate_unit(gate_name, *qit, *(qit+1), *(qit+2));
        if (cond.isValid()) g.setCondition(cond);
        if (gate_time_slot == last0) {
            time_list[*qit].push_back(g);
            append_I_gate(time_list, *(qit+1), gate_time_slot, last1);
            append_I_gate(time_list, *(qit+2), gate_time_slot, last2);
        } else if (gate_time_slot == last1) {
            time_list[*(qit+1)].push_back(g);
            append_I_gate(time_list, *qit, gate_time_slot, last0);
            append_I_gate(time_list, *(qit+2), gate_time_slot, last2);
        } else {
            time_list[*(qit+2)].push_back(g);
            append_I_gate(time_list, *qit, gate_time_slot, last0);
            append_I_gate(time_list, *(qit+1), gate_time_slot, last1);
        }
    }
    
    return gate_time_slot;
}

inline size_t BasicSimulator::add_measurement(vector<vector<gate_unit>> & time_list, const vector<size_t> & qubits, const vector<size_t> & clbits)
{
    size_t gate_time_slot = 0;
    for (auto q: qubits) {
        if (gate_time_slot < time_list[q].size()) {
            gate_time_slot = time_list[q].size();
        }        
    }

    size_t sz = qubits.size();
    for (size_t i = 0; i < sz; i++) {
        size_t last = time_list[qubits[i]].size();
        for (int k = 0; k < (gate_time_slot - last); k++) {
            time_list[qubits[i]].emplace_back("I", qubits[i]);
        }
        gate_unit m(measurement, qubits[i]);
        m.setClbitTarget(clbits[i]);
        time_list[qubits[i]].push_back(m);
    }
    
    for (size_t j=0; j<time_list.size(); j++) {
        size_t lsz = time_list[j].size();
        if (lsz <= gate_time_slot) {
            for (size_t k=0; k<(gate_time_slot+1-lsz); k++) {
                time_list[j].emplace_back("I", j);
            }
        }
    }

    return gate_time_slot;
}

inline condition get_condition_from_vertex(const igraph_t *g, igraph_integer_t vid, igraph_es_t es, igraph_integer_t relation)
{
    igraph_real_t constant;
    get_numeric_vertex_attr(g, node_constant_attr, vid, &constant);
    igraph_vector_t conbit_res;
    igraph_vector_init(&conbit_res, 0);
    get_numeric_edge_attrs(g, edge_conbit_attr, es, &conbit_res);
    vector<size_t> clbits;
    for (int i = 0; i < igraph_vector_size(&conbit_res); i++) {
        clbits.push_back(VECTOR(conbit_res)[i]);
    }
   
    condition cond(clbits, RELATION(relation), (int)constant);
    igraph_vector_destroy(&conbit_res);
    return cond;
}

/**
 * Handle normal op nodes
 */
inline size_t BasicSimulator::add_element(const igraph_t *g, 
                                 igraph_integer_t vid, 
                                 unordered_map<int, size_t> & qreg_map,
                                 unordered_map<int, size_t> & creg_map,
                                 vector<vector<gate_unit>> & time_list) 
{
    igraph_es_t es;
    igraph_vector_t qubit_res;
    igraph_vector_t params_res;
    
    igraph_vector_init(&qubit_res, 0);
    igraph_vector_init(&params_res, 0);
    
    char *gate_name;
    get_string_vertex_attr(g, node_name_attr, vid, &gate_name);
    // get qargs
    igraph_es_incident(&es, vid, IGRAPH_IN);
    // get_numeric_edge_attrs(g, edge_qubit_attr, es, &qubit_res);
    get_numeric_list_vertex_attr(g, node_qubits_attr, vid, &qubit_res);

    // get params
    get_numeric_list_vertex_attr(g, node_params_attr, vid, &params_res);

    condition cond;
    igraph_real_t relation;
    int ret = get_numeric_vertex_attr(g, node_cmp_attr, vid, &relation);
    if (ret == 0) {
        cond = std::move(get_condition_from_vertex(g, vid, es, relation));
        for (auto ite = cond.m_clbits.begin(); ite != cond.m_clbits.end(); ++ite) {
            *ite = creg_map.at(*ite);
        }
    }
     
    size_t gate_time_slot = 0;
    long int qsize = igraph_vector_size(&qubit_res);
    
    // // the size of qubit_res is 0 for an init vertex ( 1 or 2 for an op vertex)
    int ori_qubit0 = (int)VECTOR(qubit_res)[0];        
    size_t qb0 = qreg_map.at(ori_qubit0);

    if (strcmp(gate_name, measurement) == 0) {
        igraph_vector_t clbit_res;
        igraph_vector_init(&clbit_res, 0);
        get_numeric_edge_attrs(g, edge_clbit_attr, es, &clbit_res);

        vector<size_t> mqubits;
        vector<size_t> mclbits;
        for (long int i = 0; i < qsize; i++) {
            int ori_qubit = (int)VECTOR(qubit_res)[i];        
            size_t qb = qreg_map.at(ori_qubit);
            int ori_clbit = (int)VECTOR(clbit_res)[i];
            size_t cb = creg_map.at(ori_clbit);
            mqubits.push_back(qb);
            mclbits.push_back(cb);
        }
        gate_time_slot = add_measurement(time_list, mqubits, mclbits);
    } else if (qsize == 1) {
        gate_time_slot = time_list[qb0].size();
        
        if (igraph_vector_size(&params_res) > 0) {
            double angle = radian_to_angle(VECTOR(params_res)[0]);
            gate_time_slot = append_to_timelist(time_list, gate_name, {qb0}, {angle}, cond); 
        } else {
            gate_time_slot = append_to_timelist(time_list, gate_name, {qb0}, {}, cond);
        }
    } else if (qsize == 2) {
        int ori_qubit1 = (int)VECTOR(qubit_res)[1];
        size_t qb1 = qreg_map[ori_qubit1];

        gate_time_slot = append_to_timelist(time_list, gate_name, {qb0, qb1}, {}, cond);
    } else if (qsize == 3) {
        int ori_qubit1 = (int)VECTOR(qubit_res)[1];
        size_t qb1 = qreg_map[ori_qubit1];
        int ori_qubit2 = (int)VECTOR(qubit_res)[2];
        size_t qb2 = qreg_map[ori_qubit2];
        gate_time_slot = append_to_timelist(time_list, gate_name, {qb0, qb1, qb2}, {}, cond);
    }

    free(gate_name);
    igraph_es_destroy(&es);
    igraph_vector_destroy(&qubit_res);
    igraph_vector_destroy(&params_res);

    return gate_time_slot;
}

/**
 * Expand a caller node by its definition.
 */
inline size_t BasicSimulator::expand_caller(const igraph_t *g, 
                                 const char *gate_name, 
                                 igraph_vector_t *qubits, 
                                 igraph_vector_t *params, 
                                 const condition & cond,
                                 unordered_map<int, size_t> & qreg_map,
                                 unordered_map<int, size_t> & creg_map,
                                 vector<vector<gate_unit>> & time_list)
{
    size_t max_time_slot = 0;

    igraph_integer_t root;
    get_vertex_id_by_attr(g, gate_def, gate_name, &root);

    igraph_vector_t callees;
    igraph_vector_init(&callees, 0);
    topological_sorting_from_vertex(g, root, &callees);

    char *callee_name;
    igraph_es_t callee_es;
    igraph_vector_t qubit_list;
    igraph_vector_t qindex_list;
    igraph_vector_t param_list;
    igraph_vector_t pindex_list;
    int i;
    
    for (i = 0; i < igraph_vector_size(&callees); i++) {
        igraph_integer_t callee = VECTOR(callees)[ (long int)i ];
        
        get_string_vertex_attr(g, node_name_attr, callee, &callee_name);

        igraph_es_incident(&callee_es, callee, IGRAPH_IN);      
        igraph_vector_init(&qindex_list, 0);
        igraph_vector_init(&param_list, 0);
        igraph_vector_init(&pindex_list, 0);

        get_numeric_list_vertex_attr(g, node_qubits_attr, callee, &qindex_list);
        get_numeric_list_vertex_attr(g, node_params_index, callee, &pindex_list);

        size_t gate_time_slot = 0;
        long qsize = igraph_vector_size(&qindex_list);
        igraph_vector_init(&qubit_list, qsize); 

        for (long i = 0; i < qsize; i++) {
            igraph_integer_t index = VECTOR(qindex_list)[i];
            VECTOR(qubit_list)[i] = VECTOR(*qubits)[index]; 
        }

        long int psize = igraph_vector_size(&pindex_list);
        // cout<<gate_name<<"  "<<callee_name<<"  "<<psize<<"  "<<VECTOR(*params)[0]<<endl;
        int err_code = exec_callable_vertex_attr(g, node_params_attr, callee, params, &pindex_list, psize, &param_list);
        if (err_code != 0) {
            throw std::runtime_error("Something is wrong with callee parameters.");
        }

        condition callee_cond;
        if (cond.isValid()) {
            callee_cond = cond;
        } else {
            igraph_real_t rel;
            int ret = get_numeric_vertex_attr(g, node_cmp_attr, callee, &rel);
            if (ret == 0) {
                callee_cond = std::move(get_condition_from_vertex(g, callee, callee_es, rel));
                for (auto ite = callee_cond.m_clbits.begin(); ite != callee_cond.m_clbits.end(); ++ite) {
                    *ite = creg_map.at(*ite);
                }
            }
        }

        igraph_real_t type = node_type_callee;
        get_numeric_vertex_attr(g, node_type_attr, callee, &type);
        if (((igraph_integer_t)type) == node_type_caller) {
            gate_time_slot = expand_caller(g, callee_name, &qubit_list, &param_list, callee_cond, qreg_map, creg_map, time_list);
        } else {
            int ori_qubit0 = (int)VECTOR(qubit_list)[0];
            size_t qb0 = qreg_map[ori_qubit0];
            if (qsize == 1) {
                if (igraph_vector_size(&param_list) > 0) {
                    double angle = radian_to_angle(VECTOR(param_list)[0]);
                    gate_time_slot = append_to_timelist(time_list, callee_name, {qb0}, {angle}, callee_cond);
                } else {
                    gate_time_slot = append_to_timelist(time_list, callee_name, {qb0}, {}, callee_cond);
                }
            } else if (qsize == 2) {
                int ori_qubit1 = (int)VECTOR(qubit_list)[1];
                size_t qb1 = qreg_map[ori_qubit1];
                gate_time_slot = append_to_timelist(time_list, callee_name,{qb0, qb1}, {}, callee_cond);
            } else if (qsize == 3) {
                int ori_qubit1 = (int)VECTOR(qubit_list)[1];
                size_t qb1 = qreg_map[ori_qubit1];

                int ori_qubit2 = (int)VECTOR(qubit_list)[2];
                size_t qb2 = qreg_map[ori_qubit2];
                gate_time_slot = append_to_timelist(time_list, callee_name,{qb0, qb1, qb2}, {}, callee_cond);
            }
        }
       
        if (gate_time_slot > max_time_slot) {
            max_time_slot = gate_time_slot;
        }

        free(callee_name);
        igraph_es_destroy(&callee_es);
        igraph_vector_destroy(&qindex_list);
        igraph_vector_destroy(&qubit_list);
        igraph_vector_destroy(&pindex_list);
        igraph_vector_destroy(&param_list);
    }
    
    return max_time_slot;
} 

circuit BasicSimulator::translate(const igraph_t *g, vector<int> & component, int qnum, int cnum) 
{
    vector<vector<gate_unit>> time_list(qnum, vector<gate_unit>());
    size_t max_time_slot = 0;
    
    size_t qcounter = 0;
    size_t ccounter = 0;
    unordered_map<int, size_t> qreg_map;
    unordered_map<int, size_t> creg_map;
    for (int i = 0; i < component.size(); i++) {
        int vid = component[i];
        igraph_real_t type = node_type_op;
        get_numeric_vertex_attr(g, node_type_attr, vid, &type);
        
        if ((igraph_integer_t)type == node_type_register) {
            char *reg_name;
            get_string_vertex_attr(g, node_name_attr, vid, &reg_name);
            
            int reg_start = atoi(strtok(reg_name+1, "_"));
            int reg_len = atoi(strtok(NULL, "_"));
            
            if (reg_name[0] == 'q') {
                for (int j = 0; j < reg_len; j++) {
                    qreg_map[reg_start + j] = qcounter++;
                }
            } else {
                for (int j = 0; j < reg_len; j++) {
                    creg_map[reg_start + j] = ccounter++;
                }
            }
            
            free(reg_name); 
        }
        
        int gate_time_slot = 0;
        if (((igraph_integer_t)type) == node_type_op) 
            gate_time_slot = add_element(g, vid, qreg_map, creg_map, time_list); 
        else if (((igraph_integer_t)type) == node_type_caller) {
            igraph_es_t es;
            igraph_vector_t qubit_res;
            igraph_vector_t params_res;
            
            igraph_vector_init(&qubit_res, 0);
            igraph_vector_init(&params_res, 0);
            
            char *gate_name;
            get_string_vertex_attr(g, node_name_attr, vid, &gate_name);

            // get qargs
            igraph_es_incident(&es, vid, IGRAPH_IN);
            // get_numeric_edge_attrs(g, edge_qubit_attr, es, &qubit_res);
            get_numeric_list_vertex_attr(g, node_qubits_attr, vid, &qubit_res);

            // get params
            get_numeric_list_vertex_attr(g, node_params_attr, vid, &params_res);

            condition cond;
            igraph_real_t relation;
            int ret = get_numeric_vertex_attr(g, node_cmp_attr, vid, &relation);
            if (ret == 0) {
                cond = std::move(get_condition_from_vertex(g, vid, es, relation));
                for (auto ite = cond.m_clbits.begin(); ite != cond.m_clbits.end(); ++ite) {
                    *ite = creg_map.at(*ite);
                }
            }

            gate_time_slot = expand_caller(g, gate_name, &qubit_res, &params_res, cond, qreg_map, creg_map, time_list);
            free(gate_name);
            igraph_es_destroy(&es);
            igraph_vector_destroy(&qubit_res);
            igraph_vector_destroy(&params_res);
        }

        if (gate_time_slot > max_time_slot) max_time_slot = gate_time_slot;
    }

    vector<circuit_unit> circuits;
    
    set<int> measured_qubits;
    for (int t = 0; t <= max_time_slot; t++) {
        vector<gate_unit> cunit;
        for (int q = 0; q < qnum; q++) {
            if (measured_qubits.find(q) != measured_qubits.end()) {
                    if (t < time_list[q].size()) {
                        gate_unit& gu = time_list[q][t];        
                        if (gu.getGateIndex() != I) {
                            string msg = "Qubit ";
                            msg += std::to_string(q);
                            msg += " has been measured.";
                            throw std::runtime_error(msg);
                        }
                    }
                    continue;
            }
            if (t < time_list[q].size()) {
                gate_unit& gu = time_list[q][t];          
                if (gu.getGateIndex() != INVALID_GATE){
                    cunit.push_back(gu); 
                }
                if (strcmp(measurement,gu.getGateName().c_str()) == 0) {
                    measured_qubits.insert(q);
                }        
            } else {
                cunit.emplace_back("I", q);
            }    
        }
        circuits.emplace_back(cunit);   
    }

    circuit circ(circuits, cnum);

    return circ;
}

vector<double> BasicSimulator::simulate(const igraph_t *g, vector<int>& component, int qnum, int cnum, vector<StateType>& state, bool verbose)
{
    circuit circ = translate(g, component, qnum, cnum);
    if (verbose) {
        string cc = circ.toJSON();
        cout << cc << endl;
    }
    
    state_manager mgr;
    mgr.execute_inplace(circ);
    vector<double> ps = mgr.getProbabilities();
    state = mgr.getStateVector();

    return ps;
}

/*
 * The program may just need to get the result of some qubits. Some ancillary qubits may be ignored.
 */
inline string convert_to_binary(size_t i, size_t n, const set<int>& mqubits)
{
    std::ostringstream oss;
    for (size_t j=n; j>=1; j--) {
        size_t pos = n - j;
        if (mqubits.empty() || mqubits.find(pos) != mqubits.end()) {
            oss << ((i>>(j-1)) & 1);
        }
    }
    return oss.str();
}

map<string, double> BasicSimulator::pack_probabilities(const vector<double>& probabilities, const set<int>& mqubits)
{
    map<string, double> prob_map;
    size_t sz = probabilities.size();
    size_t n = (size_t)(log(sz)/log(2));
    
    double sum = 0.0;
    for (size_t i = 0; i < sz; i++) {
        double p = probabilities[i];
        if(fabs(p-0.0) > epsilon) {
            string key = convert_to_binary(i, n, mqubits);
            if (prob_map.find(key) != prob_map.end())
                prob_map[key] += p;
            else
                prob_map[key] = p;
            sum += p;
        }
    }
    if(fabs(1.0-sum) > epsilon) {
        auto rit = prob_map.rbegin();
        rit->second += (1.0 - sum);
    }
    
    return prob_map;
}

map<string, int> BasicSimulator::calc_counts(const map<string, double>& probabilities, int shots)
{
    map<string, int> counts;
    // vector<string> more;
    vector<string> less;

    int sum = 0;
    for (auto it = probabilities.begin(); it != probabilities.end(); ++it) {
        double p = it->second;
        double val = p * shots;
        int cnt = (int)val;
        double rval = round(val);
        if (cnt > 0) {
            counts[it->first] = cnt;
            sum += cnt;
        }
        if(rval > val) less.push_back(it->first); 
    }
    int total = shots - sum;
    if (total > 0) {
        for (size_t i = 0; i < less.size(); i++)
        {
            counts[less[i]] += 1;
            total--;
            if(total==0) break;
        }
    }
    
    while (total > 0) {
        for (auto it = counts.begin(); it != counts.end(); ++it ) {
            it->second += 1;
            total--;
            if(total==0) break;
        }
    }
    
    return counts;
}