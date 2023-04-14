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

#include "result.h"
int Result::repeat = 1024;

Result::Result(/* args */)
{
}

Result::~Result()
{
}

string Result::to_string(long key, size_t qnum)
{
    std::ostringstream oss;
    for (size_t j=qnum; j>=1; j--) {
        oss << ((key>>(j-1)) & 1);
    }
    return oss.str();
}

string Result::get_random_reading()
{
    // vector<string> readings;
    // if (counts.size() != 0) {
    //     for (auto it = counts.begin(); it != counts.end(); ++it) {
    //         for (int i=0; i<it->second; ++i) {
    //             readings.push_back(it->first);
    //         }
    //     }
    // } 
    auto it = probabilities.begin();
    size_t qubit_num = it->first.length();
    random_device seed;
    mt19937_64 engine(seed());
    uniform_int_distribution<long> distrib(0, (long)(pow(2, qubit_num)) - 1);
    uniform_real_distribution<double> prob_gen(0.0, 1.0);
    int run = 0;
    while (run < repeat) {
        long binary = distrib(engine);
        double dist_bound = 0.0;
        string binstr = to_string(binary, qubit_num);
        if (probabilities.find(binstr) != probabilities.end()) {
            dist_bound = probabilities[binstr];
        }
        double ran_val = prob_gen(engine);
        if (ran_val <= dist_bound) {
            return binstr; 
        }
        run += 1;
    }
   
    return it->first;
}