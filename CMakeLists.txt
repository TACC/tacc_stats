cmake_minimum_required(VERSION 2.6)
set(CMAKE_PROJECT_NAME "tacc_stats")
set(PROJECT_VERSION "1.0.6")

include(CTest)

# Write runtime configuration file for all modules
set(PY_LIB_PATH ${CMAKE_SOURCE_DIR}/lib)
file(WRITE "${PY_LIB_PATH}/sys_conf.py")
file(APPEND "${PY_LIB_PATH}/sys_conf.py" 
  tacc_stats_home=\"${tacc_stats_home}\"\n
  acct_path=\"${acct_path}\"\n
  host_list_dir=\"${host_list_dir}\"\n
  host_name_ext=\"${host_name_ext}\"\n
  batch_system=\"${batch_system}\"\n
  lariat_path=\"${lariat_path}\"\n
  pickles_dir=\"${pickles_dir}\"\n
  tacc_stats_lib="${PY_LIB_PATH}"\n
  seek=0\n)

add_subdirectory(monitor)
add_subdirectory(pickler)
add_subdirectory(analysis)
add_subdirectory(site)

# add a target to generate API documentation with Doxygen
find_package(Doxygen)
if(DOXYGEN_FOUND)
configure_file(${CMAKE_CURRENT_SOURCE_DIR}/autodoc/Doxyfile.in ${CMAKE_CURRENT_BINARY_DIR}/Doxyfile @ONLY)
add_custom_target(doc
${DOXYGEN_EXECUTABLE} ${CMAKE_CURRENT_BINARY_DIR}/Doxyfile
WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
COMMENT "Generating API documentation with Doxygen" VERBATIM
)
endif(DOXYGEN_FOUND)

# archive repository in tarball
set(ARCHIVE_NAME ${CMAKE_PROJECT_NAME}-${PROJECT_VERSION})
add_custom_target(dist
    COMMAND git archive --prefix=${ARCHIVE_NAME}/ HEAD
        | gzip > ${CMAKE_BINARY_DIR}/${ARCHIVE_NAME}.tar.gz
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR})
