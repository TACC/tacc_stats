
set(CMAKE_C_FLAGS  "-g -Wall -Werror -O3 -DDEBUG")
set(TACC_STATS_OBJS main stats dict collect schema stats_file lustre_obd_to_mnt)

separate_arguments(TYPES)
list(SORT TYPES)

file(WRITE "stats.x")
foreach(T ${TYPES})
	  set(TYPE_OBJS ${TYPE_OBJS} ${T})
	  file(APPEND "stats.x" "X(${T}) ")
endforeach(T)

add_definitions(-D_GNU_SOURCE)
add_definitions(-DSTATS_PROGRAM=\"${name}\")
add_definitions(-DSTATS_VERSION=\"${version}\")
add_definitions(-DSTATS_DIR_PATH=\"${stats_dir}\")
add_definitions(-DSTATS_LOCK_PATH=\"${stats_lock}\")
add_definitions(-DJOBID_FILE_PATH=\"${jobid_file}\")


include_directories(/opt/ofed/include)
link_directories(/opt/ofed/lib64)
add_executable(tacc_stats ${TACC_STATS_OBJS} ${TYPE_OBJS})
target_link_libraries(tacc_stats ibmad)

set(PRINT_OBJS print-schema stats dict schema ${TYPE_OBJS})
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wl,--unresolved-symbols=ignore-all")

add_executable(print-schema ${PRINT_OBJS})

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
install(PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/tacc_stats 
  ${CMAKE_CURRENT_BINARY_DIR}/print-schema DESTINATION ${CMAKE_SOURCE_DIR}/bin)

install(PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/pickles.conf 
  DESTINATION ${CMAKE_SOURCE_DIR}/bin)

# Setup python scripts and module locations
# place support modules in include dir
set(CONFIG_PY_DIR ${CMAKE_SOURCE_DIR}/include)
configure_file(find_jobs_between.py.in ${CMAKE_CURRENT_BINARY_DIR}/find_jobs_between.py @ONLY)
configure_file(job_pickles.py.in ${CMAKE_CURRENT_BINARY_DIR}/job_pickles.py @ONLY)
configure_file(job_report.py.in ${CMAKE_CURRENT_BINARY_DIR}/job_report.py @ONLY)

# Setup cron script for pickler
set (PICKLES_DIR ${pickles_dir})
set (PYTHON_PATH ${python_path})
configure_file(do_job_pickles_cron.sh.in ${CMAKE_CURRENT_BINARY_DIR}/do_job_pickles_cron.sh @ONLY)

file(GLOB PY_INC_FILES ${CMAKE_CURRENT_SOURCE_DIR}/*.py) 
install(PROGRAMS ${PY_INC_FILES}  DESTINATION 
  ${CMAKE_SOURCE_DIR}/include)

install(PROGRAMS 
  ${CMAKE_CURRENT_BINARY_DIR}/find_jobs_between.py 
  ${CMAKE_CURRENT_BINARY_DIR}/job_pickles.py
  ${CMAKE_CURRENT_BINARY_DIR}/job_report.py  
  ${CMAKE_CURRENT_BINARY_DIR}/do_job_pickles_cron.sh  
  DESTINATION ${CMAKE_SOURCE_DIR}/bin)

file(GLOB BASH_FILES ${CMAKE_CURRENT_SOURCE_DIR}/*.sh) 
install(PROGRAMS ${BASH_FILES} DESTINATION ${CMAKE_SOURCE_DIR}/bin)
