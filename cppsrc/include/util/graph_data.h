#pragma once

#include <stdexcept>

#include <pybind11/pybind11.h>

extern "C" {
#include "igraph/igraph.h"
#include "util/graph_attributes.h"
}

class NativeGraph
{
public:
    explicit NativeGraph(pybind11::dict data) : data_(data)
    {
        pybind11::list edges = data_["edges"];
        igraph_vector_t edge_vector;
        if (igraph_vector_init(&edge_vector, edges.size() * 2) != IGRAPH_SUCCESS) {
            throw std::runtime_error("Could not allocate the native graph edge vector.");
        }

        int status;
        try {
            for (pybind11::ssize_t i = 0; i < edges.size(); ++i) {
                pybind11::sequence edge = edges[i];
                VECTOR(edge_vector)[i * 2] = edge[0].cast<igraph_integer_t>();
                VECTOR(edge_vector)[i * 2 + 1] = edge[1].cast<igraph_integer_t>();
            }

            status = igraph_create(
                &graph_,
                &edge_vector,
                data_["vertex_count"].cast<igraph_integer_t>(),
                data_["directed"].cast<bool>()
            );
        } catch (...) {
            igraph_vector_destroy(&edge_vector);
            throw;
        }
        igraph_vector_destroy(&edge_vector);
        if (status != IGRAPH_SUCCESS) {
            throw std::runtime_error("Could not create the native graph.");
        }

        attributes_.attrs[ATTRHASH_IDX_GRAPH] = data_["graph_attrs"].ptr();
        attributes_.attrs[ATTRHASH_IDX_VERTEX] = data_["vertex_attrs"].ptr();
        attributes_.attrs[ATTRHASH_IDX_EDGE] = data_["edge_attrs"].ptr();
        attributes_.vertex_name_index = nullptr;
        graph_.attr = &attributes_;
    }

    ~NativeGraph()
    {
        graph_.attr = nullptr;
        igraph_destroy(&graph_);
    }

    NativeGraph(const NativeGraph&) = delete;
    NativeGraph& operator=(const NativeGraph&) = delete;

    igraph_t* get()
    {
        return &graph_;
    }

private:
    pybind11::dict data_;
    spinqit_attribute_struct attributes_;
    igraph_t graph_;
};
