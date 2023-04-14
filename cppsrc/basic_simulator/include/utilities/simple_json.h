#ifndef _SIMPLE_JSON_H_
#define _SIMPLE_JSON_H_

#include <vector>
#include <string>

#define INVALID_INT  0xFFFFFFFF
#define INVALID_DOUBLE 0xFFFFFFFF

class simple_json {
private:
    std::string   m_json;

private:
    std::vector<size_t> getPairPosition( const std::string & json
                                       , char c1, char c2, size_t pos);

public:
    simple_json(const std::string & str_json);

    std::string getSubJSON(char c1, char c2, uint8_t start_pos);
    std::string getString(const std::string & key);
    int getInteger(const std::string & key);
    double getDouble(const std::string & key);
    std::vector<std::string> getJSONArray(const std::string & key);
};

#endif // _SIMPLE_JSON_H_
