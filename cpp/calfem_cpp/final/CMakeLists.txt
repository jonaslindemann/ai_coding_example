cmake_minimum_required(VERSION 3.12)
project(BeamAnalysis)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Eigen3
find_package(Eigen3 3.3 REQUIRED NO_MODULE)

# Add executable
add_executable(beam_example example_usage.cpp)

# Link Eigen3
target_link_libraries(beam_example Eigen3::Eigen)

# Include current directory for header files
target_include_directories(beam_example PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})