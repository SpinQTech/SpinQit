cmake_minimum_required(VERSION 3.12)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED True)
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED True)
set(CMAKE_CXX_EXTENSIONS OFF)
if (CMAKE_HOST_APPLE)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fms-extensions")
endif ()

project(spinqit VERSION 0.0.1)

add_subdirectory(cppsrc)

set(WRAPPER_DIR "spinqit/backend/wrapper")
set(SOURCES "${WRAPPER_DIR}/backend_binding.cpp")

find_package(PythonLibs 3 REQUIRED)
set(_find_pybind_cmake_command "
import sys
import pybind11
sys.stdout.write(pybind11.get_cmake_dir())
")

execute_process(COMMAND "${PYTHON_EXECUTABLE}" -c "${_find_pybind_cmake_command}"
                OUTPUT_VARIABLE _pybind_cmake
                RESULT_VARIABLE _pybind_cresult)

message(STATUS "PYBIND CMAKE: ${_pybind_cmake}")

set(pybind11_DIR "${_pybind_cmake}")

message(STATUS "PYBIND11 dir: ${pybind11_DIR}")
find_package(pybind11 REQUIRED)

pybind11_add_module(spinq_backends ${SOURCES})
target_include_directories(spinq_backends PRIVATE "${CMAKE_CURRENT_LIST_DIR}/cppsrc/include"
				               "${CMAKE_CURRENT_LIST_DIR}/cppsrc/basic_simulator/include"
				               "${CMAKE_CURRENT_LIST_DIR}/cppsrc/nmr/include")

set_target_properties(spinq_backends PROPERTIES 
                      BUILD_WITH_INSTALL_RPATH TRUE 
                      INSTALL_RPATH "\$ORIGIN"
                      BUILD_RPATH "\$ORIGIN"
                      )

target_link_libraries(spinq_backends PRIVATE spinq-simulator)