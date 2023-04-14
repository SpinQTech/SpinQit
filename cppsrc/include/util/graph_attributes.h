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

#pragma once
#include <vector>
#include <string.h>
#include <Python.h>
#include <igraph/igraph.h>
#include <igraph/igraph_error.h>

#define PyBaseString_Check(o) (PyUnicode_Check(o) || PyBytes_Check(o))
#define ATTR_STRUCT(graph) ((igraphmodule_i_attribute_struct*)((graph)->attr))
#define ATTR_STRUCT_DICT(graph) ((igraphmodule_i_attribute_struct*)((graph)->attr))->attrs

#define ATTRHASH_IDX_GRAPH  0
#define ATTRHASH_IDX_VERTEX 1
#define ATTRHASH_IDX_EDGE   2

typedef struct {
    PyObject* attrs[3];
    PyObject* vertex_name_index;
} igraphmodule_i_attribute_struct;

/*
 * Copy unicode bytes to a string
 */
static char* PyUnicode_CopyAsString(PyObject* string) {
    PyObject* bytes;
    char* result;

    if (PyBytes_Check(string)) {
        bytes = string;
        Py_INCREF(bytes);
    } else {
        bytes = PyUnicode_AsUTF8String(string);
    }

    if (bytes == 0)
        return 0;
  
    result = strdup(PyBytes_AS_STRING(bytes));
    Py_DECREF(bytes);

    if (result == 0)
        PyErr_NoMemory();

    return result;
}

/*
 * Convert a python string to a C string
 */
static char* PyObject_ConvertToCString(PyObject* string) {
    char* result;

    if (string == 0)
        return 0;

    if (!PyBaseString_Check(string)) {
        string = PyObject_Str(string);
        if (string == 0)
            return 0;
    } else {
        Py_INCREF(string);
    }

    result = PyUnicode_CopyAsString(string);
    Py_DECREF(string);

    return result;
}

static igraph_real_t get_numeric_graph_attr(const igraph_t *graph, 
                                     const char *name) {
    PyObject *dict, *o;
    dict = ATTR_STRUCT_DICT(graph)[ATTRHASH_IDX_GRAPH];
    o = PyDict_GetItemString(dict, name);
    igraph_real_t value = PyFloat_AsDouble(o);
    return value;
}

static int get_string_vertex_attr(const igraph_t *graph,
                           const char *name, 
                           igraph_integer_t vid,
                           char** value) {
    PyObject *dict, *list, *result;
    dict = ATTR_STRUCT_DICT(graph)[ATTRHASH_IDX_VERTEX];
    list = PyDict_GetItemString(dict, name);
    if (!list)
        IGRAPH_ERROR("No such attribute", IGRAPH_EINVAL);
    
    result = PyList_GetItem(list, vid);
    if (result == 0)
        IGRAPH_ERROR("null element in PyList", IGRAPH_EINVAL);

    *value = PyObject_ConvertToCString(result);
    if (*value == 0)
        IGRAPH_ERROR("error while calling PyObject_ConvertToCString", IGRAPH_EINVAL);

    return 0;
}

static int get_numeric_vertex_attr(const igraph_t *graph,
                            const char *name,
                            igraph_integer_t vid,
                            igraph_real_t *value) {
    PyObject *dict, *list, *result;
    dict = ATTR_STRUCT_DICT(graph)[ATTRHASH_IDX_VERTEX];
    list = PyDict_GetItemString(dict, name);
    if (list == NULL)
        return IGRAPH_EINVAL;

    result = PyList_GetItem(list, vid);
    if (result == Py_None)
        return IGRAPH_EINVAL;

    *value = PyFloat_AsDouble(result);    
    return 0;
}

static int exec_callable_vertex_attr(const igraph_t *graph,
                                        const char *name,
                                        igraph_integer_t vid,
                                        igraph_vector_t *params,
                                        igraph_vector_t *indexes,
                                        long int index_size,
                                        igraph_vector_t *value) {
    PyObject *dict, *list, *functions, *result;
    dict = ATTR_STRUCT_DICT(graph)[ATTRHASH_IDX_VERTEX];
    list = PyDict_GetItemString(dict, name);
    if (list == NULL)
        return 0;

    functions = PyList_GetItem(list, vid);
    if (functions == Py_None)
        return 0;

    Py_ssize_t length = PyList_Size(functions);
    if (length <= 0) {
        return 0;
    }

    IGRAPH_CHECK(igraph_vector_resize(value, length));    
    long i,j;
    for (i=0,j=0; i<length; i++) {
        PyObject *fn = PyList_GetItem(functions, i);
        PyCodeObject *code = (PyCodeObject*)PyFunction_GET_CODE(fn);
        int argcount = code->co_argcount;

        if (argcount == 0) {
            result = PyObject_CallObject(fn, NULL);
        } else {
            if (j > index_size-1) {
                // cout<<argcount<<"    "<<index_size<<endl;
                return IGRAPH_EINVAL; 
            }
            igraph_integer_t index = VECTOR(*indexes)[j];
            if (index == -1) {
                PyObject *pArgs = PyTuple_New(1);
                Py_ssize_t psize = (Py_ssize_t)igraph_vector_size(params);
                PyObject *plist = PyList_New(psize);
                for (Py_ssize_t k=0; k<psize; k++) {
                    PyList_SetItem(plist, k, PyFloat_FromDouble(VECTOR(*params)[k]));
                }
                PyTuple_SetItem(pArgs, 0, plist);
                result = PyObject_CallObject(fn, pArgs);
            } else {
                PyObject *pArgs = PyTuple_New(argcount);
                for (int k=0; k<argcount; k++) {
                    if (j+k > index_size-1) return IGRAPH_EINVAL;
                    index = VECTOR(*indexes)[j+k];
                    PyTuple_SetItem(pArgs, k, Py_BuildValue("d", VECTOR(*params)[index]));
                }

                result = PyObject_CallObject(fn, pArgs);
                Py_XDECREF(pArgs);
            }
        }
        j += argcount;
        VECTOR(*value)[i] = PyFloat_AsDouble(result);
    } 
   
    return 0;
}

static int get_numeric_list_vertex_attr(const igraph_t *graph,
                                 const char *name,
                                 igraph_integer_t vid,
                                 igraph_vector_t *value) {
    PyObject *dict, *list, *result;
    dict = ATTR_STRUCT_DICT(graph)[ATTRHASH_IDX_VERTEX];
    list = PyDict_GetItemString(dict, name);    
    if (list == NULL) {
        return IGRAPH_EINVAL;
    }

    result = PyList_GetItem(list, vid);
    if (result == Py_None)
        return IGRAPH_EINVAL;
   
    Py_ssize_t length = PyList_Size(result);
    if (length <= 0) {
        return IGRAPH_EINVAL;
    }
    
    IGRAPH_CHECK(igraph_vector_resize(value, length));    
    long i;
    for (i=0; i<length; i++) {
        PyObject *tmp = PyNumber_Float(PyList_GetItem(result, i));
        VECTOR(*value)[i] = PyFloat_AsDouble(tmp);    
        Py_XDECREF(tmp);    
    }
    
    return 0;
}

static int get_string_vertex_attrs(const igraph_t *graph, 
                            const char *name, 
                            igraph_vs_t vs,
                            igraph_strvector_t *value) {
    PyObject *dict, *list, *result;
    dict = ATTR_STRUCT_DICT(graph)[ATTRHASH_IDX_VERTEX];
    list = PyDict_GetItemString(dict, name);
    if (!list)
        IGRAPH_ERROR("No such attribute", IGRAPH_EINVAL);

    igraph_vit_t it;
    long int i=0;
    IGRAPH_CHECK(igraph_vit_create(graph, vs, &it));
    IGRAPH_FINALLY(igraph_vit_destroy, &it);
    IGRAPH_CHECK(igraph_strvector_resize(value, IGRAPH_VIT_SIZE(it)));
    
    while (!IGRAPH_VIT_END(it)) {
        int v=(int)IGRAPH_VIT_GET(it);
        char* str;

        result = PyList_GetItem(list, v);
        if (result == 0)
            IGRAPH_ERROR("null element in PyList", IGRAPH_EINVAL);

        str = PyObject_ConvertToCString(result);
        if (str == 0)
            IGRAPH_ERROR("error while calling PyObject_ConvertToCString", IGRAPH_EINVAL);

        igraph_strvector_set(value, i, str);
        free(str);

        IGRAPH_VIT_NEXT(it);
        i++;
    }
    igraph_vit_destroy(&it);
    IGRAPH_FINALLY_CLEAN(1);

    return 0;        
}

static igraph_real_t get_numeric_edge_attrs(const igraph_t *graph, 
                                    const char *name, 
                                    igraph_es_t es,
                                    igraph_vector_t *value) {
    PyObject *dict, *list, *result, *o;
    igraph_vector_t eids;
    dict = ATTR_STRUCT_DICT(graph)[ATTRHASH_IDX_EDGE];
    list = PyDict_GetItemString(dict, name);
    if (!list) 
        IGRAPH_ERROR("No such attribute", IGRAPH_EINVAL);

    igraph_eit_t it;
    long int i=0;
    IGRAPH_CHECK(igraph_eit_create(graph, es, &it));
    IGRAPH_FINALLY(igraph_eit_destroy, &it);
    IGRAPH_CHECK(igraph_vector_resize(value, IGRAPH_EIT_SIZE(it)));
    igraph_vector_init(&eids, IGRAPH_EIT_SIZE(it));

    while (!IGRAPH_EIT_END(it)) {
        VECTOR(eids)[i] = (Py_ssize_t)IGRAPH_EIT_GET(it);
        IGRAPH_EIT_NEXT(it);
        i++;
    }
    igraph_eit_destroy(&it);
    igraph_vector_sort(&eids); // sort to ensure the order of control and target qubits

    long int count = 0;
    for (i = 0; i < igraph_vector_size(&eids); i++)
    {
        o = PyList_GetItem(list, VECTOR(eids)[i]);
        if (o != Py_None) {
            result = PyNumber_Float(o);
            VECTOR(*value)[count] = PyFloat_AsDouble(result);
            Py_XDECREF(result);
            count++;
        } 
    }
    IGRAPH_CHECK(igraph_vector_resize(value, count));
    
    igraph_vector_destroy(&eids);
    IGRAPH_FINALLY_CLEAN(1);

    return 0;
}

static int get_vertex_id_by_attr(const igraph_t *graph, 
                          const char* attr_name, 
                          const char* attr_value, 
                          igraph_integer_t* vid) {
    Py_ssize_t n = 0;
    PyObject *dict, *attr_list, *value, *id;
    
    dict = ATTR_STRUCT_DICT(graph)[ATTRHASH_IDX_VERTEX];
    attr_list = PyDict_GetItemString(dict, attr_name);
    if (attr_list == NULL)
        return IGRAPH_EINVAL;
    
    n = PyList_Size(attr_list) - 1;
    while (n >= 0) {
        value = PyList_GetItem(attr_list, n);
        if (value != Py_None) {
            char *str = PyObject_ConvertToCString(value);
            if (strcmp(str, attr_value) == 0) {
                *vid = n;
                return 0;
            }
        }
        n--;
    }

    return IGRAPH_EINVAL;
}

static int get_vertex_id_list_by_attr(const igraph_t *graph, 
                          const char* attr_name, 
                          int attr_value, 
                          std::vector<int> & vids) {
    Py_ssize_t n = 0;
    PyObject *dict, *attr_list, *value, *id;
    
    dict = ATTR_STRUCT_DICT(graph)[ATTRHASH_IDX_VERTEX];
    attr_list = PyDict_GetItemString(dict, attr_name);
    if (attr_list == NULL)
        return IGRAPH_EINVAL;
    
    while (n < PyList_Size(attr_list)) {
        value = PyList_GetItem(attr_list, n);
        if (value != Py_None) {
            if (attr_value == (int)PyLong_AsLong((value))) {
                vids.push_back((int)n);
            }
        }
        n++;
    }

    return 0;
}

static int get_vertex_num_by_attr(const igraph_t *graph,
                           const char* attr_name,
                           int attr_value,
                           igraph_integer_t* vids,
                           int length) {
    int n = 0;
    PyObject *dict, *attr_list, *value, *id;
    
    dict = ATTR_STRUCT_DICT(graph)[ATTRHASH_IDX_VERTEX];
        
    attr_list = PyDict_GetItemString(dict, attr_name);
    if (attr_list == NULL)
        return 0;
    
    Py_ssize_t sz = PyList_Size(attr_list);
    int count = 0;
    
    while (n < length) {
        Py_ssize_t idx = *(vids + n);
        if (idx < sz) {
            value = PyList_GetItem(attr_list, idx);
            if (value != Py_None) {
                if (attr_value == (int)PyLong_AsLong((value))) {
                    count++;
                }
            }
        }
        
        n++;
    }

    return count;
}

static int topological_sorting_from_vertex(const igraph_t *graph, 
                                    igraph_integer_t root, 
                                    igraph_vector_t *value) {
    igraph_vector_t dfs_res;
    igraph_vector_init(&dfs_res, 0);                                    
    igraph_dfs(graph, root, IGRAPH_OUT, 0, NULL, &dfs_res, NULL, NULL, NULL, NULL, NULL);

    int i;
    for (i = 0; i < igraph_vector_size(&dfs_res); i++) {
        igraph_integer_t v = VECTOR(dfs_res)[i];
        if (v == root) break;
    }
    igraph_vector_resize(value, i);
    for (int j = 0; j < i; j++) {
        VECTOR(*value)[j] = VECTOR(dfs_res)[i-1-j];
    }

    igraph_vector_destroy(&dfs_res);
    return 0;
}