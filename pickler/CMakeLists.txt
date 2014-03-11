set(PY_INC_PATH ${CMAKE_SOURCE_DIR}/include)
set(PY_LIB_PATH ${CMAKE_SOURCE_DIR}/lib/pickler)
set(LARIAT_PATH ${lariat_path})

# Write pickler runtime configuration file
file(WRITE "${PY_LIB_PATH}/pickler_conf.py")
file(APPEND "${PY_LIB_PATH}/pickler_conf.py" 
  tacc_stats_home=\"${tacc_stats_home}\"\n
  acct_path=\"${acct_path}\"\n
  host_list_dir=\"${host_list_dir}\"\n
  host_name_ext=\"${host_name_ext}\"\n
  batch_system=\"${batch_system}\"\n
  seek=0\n)

# Setup python scripts and module locations
# place support modules in PY_LIB_PATH dir

# Setup cron script for pickler
set(PICKLES_DIR ${pickles_dir})
set(PYTHON_PATH ${python_path})
configure_file(do_job_pickles_cron.sh.in 
  ${CMAKE_CURRENT_BINARY_DIR}/do_job_pickles_cron.sh @ONLY)

# Install support modules for pickler
file(GLOB PY_INC_FILES ${CMAKE_CURRENT_SOURCE_DIR}/*.py) 
file(COPY ${PY_INC_FILES} DESTINATION ${PY_LIB_PATH}
  FILE_PERMISSIONS OWNER_READ OWNER_WRITE GROUP_READ WORLD_READ) 

# Install pickler scripts
file(COPY   
  find_jobs_between.py 
  job_pickles.py
  job_report.py  
  DESTINATION ${CMAKE_SOURCE_DIR}/bin 
  FILE_PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ
  GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)

# Install Bash scripts
file(GLOB BASH_FILES ${CMAKE_CURRENT_SOURCE_DIR}/*.sh) 
file(COPY ${BASH_FILES} DESTINATION ${CMAKE_SOURCE_DIR}/bin)

# Add testing directory
add_subdirectory(tests)