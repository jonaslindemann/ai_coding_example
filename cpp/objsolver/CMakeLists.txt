cmake_minimum_required(VERSION 3.20)

project(objsolver VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Optimised compiler flags
if(MSVC)
    add_compile_options(
        /O2          # Maximise speed
        /Oi          # Enable intrinsic functions
        /GL          # Whole-program optimisation
        /Gy          # Enable function-level linking
        /arch:AVX2   # Enable AVX2 SIMD (requires AVX2-capable CPU)
        /W4          # Warning level 4
    )
    add_link_options(/LTCG)  # Link-time code generation (pairs with /GL)
elseif(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    add_compile_options(
        -O3              # Maximise optimisation
        -march=native    # Tune for the build machine's CPU
        -funroll-loops   # Unroll loops for throughput
        -fomit-frame-pointer  # Free up a register
        -Wall            # Enable common warnings
        -Wextra          # Enable extra warnings
    )
endif()

# Dependencies provided via vcpkg
find_package(Eigen3 CONFIG REQUIRED)
find_package(nlohmann_json CONFIG REQUIRED)
find_package(fmt CONFIG REQUIRED)

# Minimal logger library shared by fem and ofsolve.
# The full src/util library depends on OpenGL (glad/stb) which is not
# part of the compute kernel build, so we compile only the logger here.
add_library(logger STATIC src/util/logger.cpp)
target_include_directories(logger PUBLIC src/util)

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/bin)

add_subdirectory(src/fem)
add_subdirectory(src/ofsolve)
add_subdirectory(src/ofsolver)
