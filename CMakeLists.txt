cmake_minimum_required(VERSION 2.6)
set(CMAKE_PROJECT_NAME "tacc_stats")
set(PROJECT_VERSION "1.0.5")

include(CTest)

if (ENABLE)
  if (${ENABLE} MATCHES "all")
    message("Build all")
    set(packages monitor pickler analyze)
  else()
    foreach(ARG ${ENABLE})
      message("Build " ${ARG})
      set(packages ${packages} ${ARG})
    endforeach()
  endif()
else()
  message("Build all by default")
  set(packages monitor pickler analyze)
endif()

foreach(package ${packages})
  add_subdirectory(${package})
endforeach()

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
