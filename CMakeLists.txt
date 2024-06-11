cmake_minimum_required(VERSION 3.20)
project(raylib_project)

# Set the C++ standard to C++11
set(CMAKE_CXX_STANDARD 20)

# Find the required packages

find_package(raylib CONFIG REQUIRED)

# Set the include directories
include_directories(include)

# Set the output directory for binaries
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

# Include the subdirectory for further configuration
add_subdirectory(src)

