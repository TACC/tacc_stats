set(TEST_DATA ${CMAKE_CURRENT_SOURCE_DIR}/data)
# Write pickler runtime configuration file for testing           
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/sys_conf.py")
set(PY_LIB_PATH ${CMAKE_SOURCE_DIR}/lib)
file(APPEND "${CMAKE_CURRENT_BINARY_DIR}/sys_conf.py"
  tacc_stats_home=\"${TEST_DATA}\"\n
  acct_path=\"${TEST_DATA}/tacc_jobs_completed\"\n
  host_list_dir=\"${TEST_DATA}\"\n
  host_name_ext=\"platform.extension\"\n
  batch_system=\"SLURM\"\n
  lariat_path=\"${lariat_path}\"\n	
   pickles_dir=\"${pickles_dir}\"\n
  tacc_stats_lib="${PY_LIB_PATH}"\n
  seek=0\n)

file(COPY ${CMAKE_SOURCE_DIR}/bin/job_pickles.py 
	  DESTINATION ${CMAKE_CURRENT_BINARY_DIR})

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/python/np2text.py 
  ${CMAKE_CURRENT_BINARY_DIR}/python/np2text.py @ONLY)

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/python/1835740_ref
  ${CMAKE_CURRENT_BINARY_DIR}/python/1835740_ref COPYONLY)

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/python/read.py
  ${CMAKE_CURRENT_BINARY_DIR}/python/read.py @ONLY)


add_test(pickler_runs ${CMAKE_CURRENT_BINARY_DIR}/job_pickles.py 
  ${CMAKE_CURRENT_BINARY_DIR}/python/ 2013-10-01 2013-10-02)

add_test(pickler_compare ${CMAKE_CURRENT_BINARY_DIR}/python/np2text.py 
  ${CMAKE_CURRENT_BINARY_DIR}/python/1835740 ${CMAKE_CURRENT_BINARY_DIR}/python/1835740_ref)

set_tests_properties(pickler_compare PROPERTIES 
				     DEPENDS pickler_runs PASS_REGULAR_EXPRESSION "True")
