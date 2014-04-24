set(CMAKE_C_FLAGS  "-g -Wall -Werror -O3 -DDEBUG")
set(TACC_STATS_OBJS main stats dict collect schema stats_file lustre_obd_to_mnt)

separate_arguments(TYPES)
list(SORT TYPES)

file(WRITE "stats.x")
foreach(T ${TYPES})
	  set(TYPE_OBJS ${TYPE_OBJS} ${T})
	  file(APPEND "stats.x" "X(${T}) ")
endforeach(T)
file(APPEND "stats.x" "\n")

add_definitions(-D_GNU_SOURCE)
add_definitions(-DSTATS_PROGRAM=\"${CMAKE_PROJECT_NAME}\")
add_definitions(-DSTATS_VERSION=\"${PROJECT_VERSION}\")
add_definitions(-DSTATS_DIR_PATH=\"${stats_dir}\")
add_definitions(-DSTATS_LOCK_PATH=\"${stats_lock}\")
add_definitions(-DJOBID_FILE_PATH=\"${jobid_file}\")


include_directories(/opt/ofed/include)
link_directories(/opt/ofed/lib64)
add_executable(tacc_stats ${TACC_STATS_OBJS} ${TYPE_OBJS})
if( "${TYPE_OBJS}" MATCHES "ib" )
    target_link_libraries(tacc_stats ibmad)
endif( "${TYPE_OBJS}" MATCHES "ib" )

set(PRINT_OBJS print-schema stats dict schema ${TYPE_OBJS})
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wl,--unresolved-symbols=ignore-all")

add_executable(print-schema ${PRINT_OBJS})

# Install executable files to bin directory
install(PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/tacc_stats 
  ${CMAKE_CURRENT_BINARY_DIR}/print-schema DESTINATION ${CMAKE_SOURCE_DIR}/bin)

