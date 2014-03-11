set(PY_INC_PATH ${CMAKE_SOURCE_DIR}/include)
set(PY_LIB_PATH ${CMAKE_SOURCE_DIR}/lib/analysis)
set(LARIAT_PATH ${lariat_path})

configure_file(analysis_conf.py.in ${PY_LIB_PATH}/analysis_conf.py @ONLY)

file(COPY __init__.py exam gen plot DESTINATION ${PY_LIB_PATH})
file(COPY nightly.py nightly.sh DESTINATION ${CMAKE_SOURCE_DIR}/bin
  FILE_PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ
  GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)

add_subdirectory(tests)
