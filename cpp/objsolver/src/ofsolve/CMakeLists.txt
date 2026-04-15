file(GLOB SOURCE_FILES *.cpp)
file(GLOB INCLUDE_FILES ${PROJECT_SOURCE_DIR}/include/ofsolve/*.h)

# tetgen_beam_mesher.cpp depends on glad/ofutil (graphics utilities) which
# are not part of the compute kernel build.
list(REMOVE_ITEM SOURCE_FILES "${CMAKE_CURRENT_SOURCE_DIR}/tetgen_beam_mesher.cpp")

add_library(ofsolve ${INCLUDE_FILES} ${SOURCE_FILES})

target_include_directories(ofsolve
    PUBLIC ${PROJECT_SOURCE_DIR}/include
)

target_link_libraries(ofsolve
    PUBLIC  Eigen3::Eigen fem
    PRIVATE logger
)

 set_target_properties(ofsolve PROPERTIES DEBUG_POSTFIX d)
