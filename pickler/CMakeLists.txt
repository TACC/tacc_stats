# Write pickler runtime configuration file
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/pickles.conf")
file(APPEND "${CMAKE_CURRENT_BINARY_DIR}/pickles.conf" 
  tacc_stats_home=\"${tacc_stats_home}\"\n
  acct_path=\"${acct_path}\"\n
  host_list_dir=\"${host_list_dir}\"\n
  host_name_ext=\"${host_name_ext}\"\n
  batch_system=\"${batch_system}\"\n
  seek=0\n)

# Install executable files to bin directory
install(PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/pickles.conf 
  DESTINATION ${CMAKE_SOURCE_DIR}/bin)

# Setup python scripts and module locations
# place support modules in include dir
set(CONFIG_PY_DIR ${CMAKE_SOURCE_DIR}/include)
configure_file(find_jobs_between.py.in ${CMAKE_CURRENT_BINARY_DIR}/find_jobs_between.py @ONLY)
configure_file(job_pickles.py.in ${CMAKE_CURRENT_BINARY_DIR}/job_pickles.py @ONLY)
configure_file(job_report.py.in ${CMAKE_CURRENT_BINARY_DIR}/job_report.py @ONLY)

# Setup cron script for pickler
set(PICKLES_DIR ${pickles_dir})
set(PYTHON_PATH ${python_path})
configure_file(do_job_pickles_cron.sh.in ${CMAKE_CURRENT_BINARY_DIR}/do_job_pickles_cron.sh @ONLY)
file(GLOB PY_INC_FILES ${CMAKE_CURRENT_SOURCE_DIR}/*.py) 

# Install support modules for pickler
install(PROGRAMS ${PY_INC_FILES}  DESTINATION 
  ${CMAKE_SOURCE_DIR}/include)

# Install pickler scripts
install(PROGRAMS 
  ${CMAKE_CURRENT_BINARY_DIR}/find_jobs_between.py 
  ${CMAKE_CURRENT_BINARY_DIR}/job_pickles.py
  ${CMAKE_CURRENT_BINARY_DIR}/job_report.py  
  ${CMAKE_CURRENT_BINARY_DIR}/do_job_pickles_cron.sh  
  DESTINATION ${CMAKE_SOURCE_DIR}/bin)

# Install Bash scripts
file(GLOB BASH_FILES ${CMAKE_CURRENT_SOURCE_DIR}/*.sh) 
install(PROGRAMS ${BASH_FILES} DESTINATION ${CMAKE_SOURCE_DIR}/bin)

# Add testing directory
add_subdirectory(tests)