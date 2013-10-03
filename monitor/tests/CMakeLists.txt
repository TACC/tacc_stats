set(TEST_DATA ${CMAKE_CURRENT_SOURCE_DIR}/data)
# Write pickler runtime configuration file                                      
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/pickles.conf")
file(APPEND "${CMAKE_CURRENT_BINARY_DIR}/pickles.conf"
  tacc_stats_home=\"${TEST_DATA}\"\n
  acct_path=\"${TEST_DATA}/tacc_jobs_completed\"\n
  host_list_dir=\"${TEST_DATA}\"\n
  host_name_ext=\"platform.extension\"\n
  batch_system=\"SLURM\"\n
  seek=0\n)

configure_file(${CMAKE_BINARY_DIR}/monitor/job_pickles.py 
  ${CMAKE_CURRENT_BINARY_DIR}/python/job_pickles.py COPY_ONLY)

add_test(pickler python ${CMAKE_CURRENT_BINARY_DIR}/python/job_pickles.py ${CMAKE_CURRENT_BINARY_DIR}/python/ 2013-10-01 2013-10-02)
