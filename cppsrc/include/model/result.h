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

#ifndef MODEL_RESULT_H
#define MODEL_RESULT_H
#include <map>
#include <vector>
#include <string>
#include <complex>
#include <random>
#include <math.h>
using namespace std;

class Result
{
public:
    map<string, double> probabilities;
    vector<complex<double>> states;
    int shots;
public:
    Result();
    ~Result();
    map<string, int> get_counts();
    string get_random_reading();
private:
    static int repeat;
    map<string, int> counts;
    string to_string(long key, size_t qnum);
};
#endif