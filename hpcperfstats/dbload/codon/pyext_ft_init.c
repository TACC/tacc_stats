/*
 * Multi-phase Python module for Codon feed_collapse under free-threaded 3.14t.
 *
 * Codon 0.20.4 --pyext PyInit/Create2 and from_python converters are GIL-ABI
 * and SIGSEGV / fail under /opt/python3.14t. We build the Codon unit with
 * --lib (@export C entry), marshal List[str] -> char** here, and expose
 * METH_VARARGS methods that call Codon C ABI.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>

extern void feed_and_collapse_fingerprint_c(
  long n,
  char **ptr,
  long *out_raw,
  long *out_collapsed,
  double *out_value_sum,
  double *out_proc_rows
);

extern void parse_stats_lines_codon_run_c(
  long n,
  char **ptr,
  long *out_ns,
  long *out_np
);

extern double pss_time_c(long i);
extern double pss_value_c(long i);
extern long pss_wid_c(long i);
extern double pss_mult_c(long i);
extern char *pss_host_c(long i);
extern char *pss_jid_c(long i);
extern char *pss_type_c(long i);
extern char *pss_dev_c(long i);
extern char *pss_event_c(long i);
extern char *pss_unit_c(long i);
extern char *psp_jid_c(long i);
extern char *psp_host_c(long i);
extern char *psp_proc_c(long i);
extern long psp_field_c(long i, long key_idx);

/* Must match feed_collapse.HOST_PROC_KEYS order. */
static const char *const HOST_PROC_KEYS[] = {
  "uid", "vm_peak", "vm_size", "vm_lck", "vm_hwm", "vm_rss", "vm_data",
  "vm_stk", "vm_exe", "vm_lib", "vm_pte", "vm_swap", "threads",
};
static const Py_ssize_t HOST_PROC_N =
  (Py_ssize_t)(sizeof(HOST_PROC_KEYS) / sizeof(HOST_PROC_KEYS[0]));

static int
fill_char_ptrs(PyObject *list_obj, char ***out_ptrs, Py_ssize_t *out_n)
{
  const Py_ssize_t n = PyList_GET_SIZE(list_obj);
  char **ptrs = NULL;
  *out_ptrs = NULL;
  *out_n = n;
  if (n > 0) {
    ptrs = (char **)PyMem_Calloc((size_t)n, sizeof(char *));
    if (ptrs == NULL) {
      PyErr_NoMemory();
      return -1;
    }
  }
  for (Py_ssize_t i = 0; i < n; i++) {
    PyObject *item = PyList_GET_ITEM(list_obj, i);
    if (!PyUnicode_Check(item)) {
      PyMem_Free(ptrs);
      PyErr_SetString(PyExc_TypeError, "lines must be str");
      return -1;
    }
    ptrs[i] = (char *)PyUnicode_AsUTF8(item);
    if (ptrs[i] == NULL) {
      PyMem_Free(ptrs);
      return -1;
    }
  }
  *out_ptrs = ptrs;
  return 0;
}

static PyObject *
feed_and_collapse_fingerprint_py(PyObject *self, PyObject *args)
{
  PyObject *list_obj = NULL;
  if (!PyArg_ParseTuple(args, "O!", &PyList_Type, &list_obj)) {
    return NULL;
  }
  char **ptrs = NULL;
  Py_ssize_t n = 0;
  if (fill_char_ptrs(list_obj, &ptrs, &n) < 0) {
    return NULL;
  }
  long raw_stats = 0;
  long collapsed_rows = 0;
  double value_sum = 0.0;
  double proc_rows = 0.0;
  feed_and_collapse_fingerprint_c(
    (long)n,
    ptrs,
    &raw_stats,
    &collapsed_rows,
    &value_sum,
    &proc_rows
  );
  PyMem_Free(ptrs);
  return Py_BuildValue("(lldd)", raw_stats, collapsed_rows, value_sum, proc_rows);
}

static PyObject *
py_str_from_codon(char *s)
{
  if (s == NULL) {
    return PyUnicode_FromString("");
  }
  return PyUnicode_FromString(s);
}

static PyObject *
parse_stats_lines_codon_py(PyObject *self, PyObject *args)
{
  PyObject *list_obj = NULL;
  if (!PyArg_ParseTuple(args, "O!", &PyList_Type, &list_obj)) {
    return NULL;
  }
  char **ptrs = NULL;
  Py_ssize_t n = 0;
  if (fill_char_ptrs(list_obj, &ptrs, &n) < 0) {
    return NULL;
  }
  long n_stats = 0;
  long n_procs = 0;
  parse_stats_lines_codon_run_c((long)n, ptrs, &n_stats, &n_procs);
  PyMem_Free(ptrs);

  PyObject *stats = PyList_New((Py_ssize_t)n_stats);
  if (stats == NULL) {
    return NULL;
  }
  for (long i = 0; i < n_stats; i++) {
    PyObject *row = PyDict_New();
    if (row == NULL) {
      Py_DECREF(stats);
      return NULL;
    }
    PyObject *v;
    int rc = 0;
    v = PyFloat_FromDouble(pss_time_c(i));
    rc |= v == NULL || PyDict_SetItemString(row, "time", v) < 0;
    Py_XDECREF(v);
    v = py_str_from_codon(pss_host_c(i));
    rc |= v == NULL || PyDict_SetItemString(row, "host", v) < 0;
    Py_XDECREF(v);
    v = py_str_from_codon(pss_jid_c(i));
    rc |= v == NULL || PyDict_SetItemString(row, "jid", v) < 0;
    Py_XDECREF(v);
    v = py_str_from_codon(pss_type_c(i));
    rc |= v == NULL || PyDict_SetItemString(row, "type", v) < 0;
    Py_XDECREF(v);
    v = py_str_from_codon(pss_dev_c(i));
    rc |= v == NULL || PyDict_SetItemString(row, "dev", v) < 0;
    Py_XDECREF(v);
    v = py_str_from_codon(pss_event_c(i));
    rc |= v == NULL || PyDict_SetItemString(row, "event", v) < 0;
    Py_XDECREF(v);
    v = PyFloat_FromDouble(pss_value_c(i));
    rc |= v == NULL || PyDict_SetItemString(row, "value", v) < 0;
    Py_XDECREF(v);
    v = PyLong_FromLong(pss_wid_c(i));
    rc |= v == NULL || PyDict_SetItemString(row, "wid", v) < 0;
    Py_XDECREF(v);
    v = PyFloat_FromDouble(pss_mult_c(i));
    rc |= v == NULL || PyDict_SetItemString(row, "mult", v) < 0;
    Py_XDECREF(v);
    v = py_str_from_codon(pss_unit_c(i));
    rc |= v == NULL || PyDict_SetItemString(row, "unit", v) < 0;
    Py_XDECREF(v);
    if (rc) {
      Py_DECREF(row);
      Py_DECREF(stats);
      return NULL;
    }
    PyList_SET_ITEM(stats, (Py_ssize_t)i, row);
  }

  PyObject *procs = PyList_New((Py_ssize_t)n_procs);
  if (procs == NULL) {
    Py_DECREF(stats);
    return NULL;
  }
  for (long i = 0; i < n_procs; i++) {
    PyObject *row = PyDict_New();
    if (row == NULL) {
      Py_DECREF(stats);
      Py_DECREF(procs);
      return NULL;
    }
    PyObject *v;
    int rc = 0;
    v = py_str_from_codon(psp_jid_c(i));
    rc |= v == NULL || PyDict_SetItemString(row, "jid", v) < 0;
    Py_XDECREF(v);
    v = py_str_from_codon(psp_host_c(i));
    rc |= v == NULL || PyDict_SetItemString(row, "host", v) < 0;
    Py_XDECREF(v);
    v = py_str_from_codon(psp_proc_c(i));
    rc |= v == NULL || PyDict_SetItemString(row, "proc", v) < 0;
    Py_XDECREF(v);
    for (Py_ssize_t k = 0; k < HOST_PROC_N; k++) {
      long fv = psp_field_c(i, (long)k);
      if (fv < 0) {
        continue;
      }
      v = PyLong_FromLong(fv);
      rc |= v == NULL || PyDict_SetItemString(row, HOST_PROC_KEYS[k], v) < 0;
      Py_XDECREF(v);
    }
    if (rc) {
      Py_DECREF(row);
      Py_DECREF(stats);
      Py_DECREF(procs);
      return NULL;
    }
    PyList_SET_ITEM(procs, (Py_ssize_t)i, row);
  }
  return Py_BuildValue("(NN)", stats, procs);
}

static PyMethodDef codon_methods[] = {
  {
    "feed_and_collapse_fingerprint",
    feed_and_collapse_fingerprint_py,
    METH_VARARGS,
    "Fingerprint: (raw_stats, collapsed_rows, value_sum, proc_rows)",
  },
  {
    "parse_stats_lines_codon",
    parse_stats_lines_codon_py,
    METH_VARARGS,
    "Finish()-shaped parse: (stats_records, proc_rows)",
  },
  {NULL, NULL, 0, NULL},
};

static int
hpcperfstats_codon_parse_exec(PyObject *module)
{
  if (PyModule_AddFunctions(module, codon_methods) < 0) {
    return -1;
  }
  return 0;
}

static PyModuleDef_Slot codon_slots[] = {
  {Py_mod_exec, (void *)hpcperfstats_codon_parse_exec},
  {Py_mod_gil, Py_MOD_GIL_USED},
  {0, NULL},
};

static struct PyModuleDef codon_module = {
  PyModuleDef_HEAD_INIT,
  .m_name = "hpcperfstats_codon_parse",
  .m_doc = "Codon feed+collapse (C-ABI + multi-phase FT init)",
  .m_size = 0,
  .m_slots = codon_slots,
};

PyMODINIT_FUNC
PyInit_hpcperfstats_codon_parse(void)
{
  return PyModuleDef_Init(&codon_module);
}
