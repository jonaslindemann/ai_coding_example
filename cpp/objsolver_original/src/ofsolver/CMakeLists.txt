file(GLOB SOURCE_FILES *.cpp)
# Exclude legacy/old implementations kept for reference
file(GLOB_RECURSE OLD_FILES old/*.cpp)
list(REMOVE_ITEM SOURCE_FILES ${OLD_FILES})

add_executable(objsolver ${SOURCE_FILES})

target_link_libraries(objsolver PRIVATE ofsolve fem logger)

set_target_properties(objsolver PROPERTIES DEBUG_POSTFIX d)
