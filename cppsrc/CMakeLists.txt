cmake_minimum_required(VERSION 3.18)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
if (CMAKE_HOST_APPLE)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fms-extensions")
endif ()

project(spinq-simulator VERSION 0.0.1)

# Source files
file(GLOB_RECURSE SOURCE_FILES CONFIGURE_DEPENDS "*.cpp" "*.h")

# Add library
message("CMAKE_HOST_APPLE = ${CMAKE_HOST_APPLE} and CMAKE_HOST_SYSTEM_PROCESSOR = ${CMAKE_HOST_SYSTEM_PROCESSOR}")

if(CMAKE_HOST_APPLE AND (CMAKE_HOST_SYSTEM_PROCESSOR STREQUAL "x86_64"))
    FIND_LIBRARY(CORE_LIB NAMES simulator-core HINTS ${CMAKE_CURRENT_LIST_DIR}/lib/mac_x86_64 REQUIRED)
elseif(CMAKE_HOST_APPLE AND (CMAKE_HOST_SYSTEM_PROCESSOR STREQUAL "arm64"))
    FIND_LIBRARY(CORE_LIB NAMES simulator-core HINTS ${CMAKE_CURRENT_LIST_DIR}/lib/mac_arm64 REQUIRED)
else()
    FIND_LIBRARY(CORE_LIB NAMES simulator-core HINTS ${CMAKE_CURRENT_LIST_DIR}/lib REQUIRED)
endif()
message("simulator-core found at ${CORE_LIB}")

if(CMAKE_HOST_APPLE AND (CMAKE_HOST_SYSTEM_PROCESSOR STREQUAL "x86_64"))
    FIND_LIBRARY(IGRAPH_LIB NAMES igraph HINTS ${CMAKE_CURRENT_LIST_DIR}/lib/mac_x86_64 REQUIRED)
elseif(CMAKE_HOST_APPLE AND (CMAKE_HOST_SYSTEM_PROCESSOR STREQUAL "arm64"))
    FIND_LIBRARY(IGRAPH_LIB NAMES igraph HINTS ${CMAKE_CURRENT_LIST_DIR}/lib/mac_arm64 REQUIRED)
else()
    FIND_LIBRARY(IGRAPH_LIB NAMES igraph HINTS ${CMAKE_CURRENT_LIST_DIR}/lib REQUIRED) 
endif()
message("igraph found at ${IGRAPH_LIB}")

if (CMAKE_HOST_WIN32)
    FIND_LIBRARY(QUASAR_LIB NAMES SpinQInterface_win_x86_64 HINTS ${CMAKE_CURRENT_LIST_DIR}/lib REQUIRED)
elseif (CMAKE_HOST_APPLE AND (CMAKE_HOST_SYSTEM_PROCESSOR STREQUAL "x86_64"))
    FIND_LIBRARY(QUASAR_LIB NAMES SpinQInterface_darwin_x86_64 HINTS ${CMAKE_CURRENT_LIST_DIR}/lib REQUIRED)
elseif (CMAKE_HOST_APPLE AND (CMAKE_HOST_SYSTEM_PROCESSOR STREQUAL "arm64"))
    FIND_LIBRARY(QUASAR_LIB NAMES SpinQInterface_darwin_arm_64 HINTS ${CMAKE_CURRENT_LIST_DIR}/lib REQUIRED)
elseif (CMAKE_HOST_UNIX)
    FIND_LIBRARY(QUASAR_LIB NAMES SpinQInterface_linux_x86_64 HINTS ${CMAKE_CURRENT_LIST_DIR}/lib REQUIRED)
endif ()
message("SpinQInterface found at ${QUASAR_LIB}")

set(THREADS_PREFER_PTHREAD_FLAG ON)
find_package(Threads REQUIRED)

if (CMAKE_HOST_UNIX)
    add_compile_options(-fPIC)
endif()

add_library(spinq-simulator STATIC ${SOURCE_FILES})

# Include directories
target_include_directories(spinq-simulator PUBLIC ${CMAKE_CURRENT_LIST_DIR}/basic_simulator/include
                                                  ${CMAKE_CURRENT_LIST_DIR}/nmr/include
                                                  ${CMAKE_CURRENT_LIST_DIR}/include
                                                  ${Python_INCLUDE_DIRS})

set_target_properties(spinq-simulator PROPERTIES 
                     BUILD_WITH_INSTALL_RPATH TRUE 
                     INSTALL_RPATH "\$ORIGIN"
                     BUILD_RPATH "\$ORIGIN"
                     )
                                              
target_link_libraries(spinq-simulator PUBLIC
                        ${CORE_LIB} 
                        ${IGRAPH_LIB}                      
                        ${QUASAR_LIB}
                        pybind11::headers
                        Threads::Threads
                        )
