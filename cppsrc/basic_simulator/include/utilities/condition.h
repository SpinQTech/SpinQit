/*
 * File:	condition.h
 * Author:	Cong Guo
 * Email:	cguo@spinq.cn
 * Company:	SpinQ Inc
 * Date：	09/2021
 *
 */

#ifndef _CONDITION_H_
#define _CONDITION_H_

#include <vector>
#include <functional>
using namespace std;

enum RELATION {
    EQ,
    NE,
    LT,
    GT,
    LE,
    GE
};

class condition {
public:
    condition();
    condition(const vector<size_t>& clbits, RELATION sym, int val);
    bool isValid() const;
    bool operator==(const condition & c) const;

    vector<size_t> m_clbits;
    RELATION m_symbol;
    int m_value;    
};

struct hash_condition{
    size_t operator()(const condition & c) const {
        size_t code = hash<int>()(c.m_value);
        for (auto it = c.m_clbits.begin(); it != c.m_clbits.end(); ++it) {
            code ^= hash<size_t>()(*it);
        }
        return code;
    }
};

#endif