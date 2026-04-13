file(GLOB SOURCE_FILES *.cpp)
file(GLOB INCLUDE_FILES ${PROJECT_SOURCE_DIR}/include/ofem/*.h)

# cpp-base64 installs base64.h into include/cpp-base64/ — expose that
# directory so the relative #include "base64.h" in calfem_reader/writer
# and the bundled base64.cpp resolve correctly.
find_path(CPP_BASE64_INCLUDE_DIR base64.h PATH_SUFFIXES cpp-base64 REQUIRED)

add_library(fem ${INCLUDE_FILES} ${SOURCE_FILES})

target_include_directories(fem
    PUBLIC  ${PROJECT_SOURCE_DIR}/include
    PRIVATE ${CPP_BASE64_INCLUDE_DIR}
)

target_link_libraries(fem
    PUBLIC  nlohmann_json::nlohmann_json
    PRIVATE logger fmt::fmt
)

set_target_properties(fem PROPERTIES DEBUG_POSTFIX d)
