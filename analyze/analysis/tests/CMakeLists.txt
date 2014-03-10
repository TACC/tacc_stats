set(TEST_DATA ${CMAKE_SOURCE_DIR}/pickler/tests/python/1835740_ref)

configure_file(${CMAKE_CURRENT_SOURCE_DIR}/python/test_plots.py.in ${CMAKE_CURRENT_BINARY_DIR}/python/test_plots.py)

add_test(analysis_plot_tests python ${CMAKE_CURRENT_BINARY_DIR}/python/test_plots.py)
set_tests_properties(analysis_plot_tests PROPERTIES PASS_REGULAR_EXPRESSION "True")