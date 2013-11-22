set(PICKLES_DIR ${pickles_dir})
set(LARIAT_PATH ${lariat_path})
set(PY_PROCESS_PICKLES_PATH ${CMAKE_SOURCE_DIR}/bin)
set(PY_INC_PATH ${CMAKE_SOURCE_DIR}/include)

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/stampede/sys_path_append.py.in 
  ${CMAKE_CURRENT_SOURCE_DIR}/stampede/sys_path_append.py @ONLY)
