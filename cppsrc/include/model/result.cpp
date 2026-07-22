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
#include <algorithm>
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

map<string, int> Result::get_counts()
{
    if (!counts.empty() || probabilities.empty() || shots <= 0) return counts;

    double probability_total = 0.0;
    for (const auto& entry : probabilities) {
        probability_total += max(0.0, entry.second);
    }
    if (probability_total == 0.0) return counts;

    vector<pair<double, string>> remainders;
    int sum = 0;
    for (const auto& entry : probabilities) {
        double expected = max(0.0, entry.second) * shots / probability_total;
        int cnt = (int)floor(expected);
        if (cnt > 0) {
            counts[entry.first] = cnt;
        }
        sum += cnt;
        remainders.emplace_back(expected - cnt, entry.first);
    }

    sort(remainders.begin(), remainders.end(),
         [](const auto& left, const auto& right) { return left.first > right.first; });
    for (int i = 0; i < shots - sum; ++i) {
        counts[remainders[i % remainders.size()].second] += 1;
    }

    return counts;
}

string Result::get_random_reading()
{
    if (probabilities.empty()) {
        return "";
    }
    
    static random_device seed;
    static mt19937_64 engine(seed());
    static uniform_real_distribution<double> distrib(0.0, 1.0);
    
    double total = 1.0;
    double r = distrib(engine) * total;
    double cumulative = 0.0;
    for (const auto& entry : probabilities) {
        cumulative += entry.second;
        if (r < cumulative) {
            return entry.first;
        }
    }

    return probabilities.rbegin()->first;
}
