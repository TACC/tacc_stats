/*
 * Multi-phase Python module for Codon feed_collapse under free-threaded 3.14t.
 *
 * Codon 0.20.4 --pyext PyInit/Create2 and from_python converters are GIL-ABI
 * and SIGSEGV / fail under /opt/python3.14t. We build the Codon unit with
 * --lib (@export C entry), marshal List[str] -> owned char** here, and expose
 * METH_VARARGS methods that call Codon C ABI.
 *
 * Declares Py_MOD_GIL_NOT_USED. Concurrent callers must use distinct slot
 * banks (optional slot arg; default 0) under bridge per-slot locks.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <string.h>

#define MAX_CODON_SLOTS 32

extern void feed_and_collapse_fingerprint_c(
  long slot,
  long n,
  char **ptr,
  long *out_raw,
  long *out_collapsed,
  double *out_value_sum,
  double *out_proc_rows
);

extern void parse_stats_lines_codon_run_c(
  long slot,
  long n,
  char **ptr,
  long *out_ns,
  long *out_np
);

extern double pss_time_c(long slot, long i);
extern double pss_value_c(long slot, long i);
extern long pss_wid_c(long slot, long i);
extern double pss_mult_c(long slot, long i);
extern char *pss_host_c(long slot, long i);
extern char *pss_jid_c(long slot, long i);
extern char *pss_type_c(long slot, long i);
extern char *pss_dev_c(long slot, long i);
extern char *pss_event_c(long slot, long i);
extern char *pss_unit_c(long slot, long i);
extern char *psp_jid_c(long slot, long i);
extern char *psp_host_c(long slot, long i);
extern char *psp_proc_c(long slot, long i);
extern long psp_field_c(long slot, long i, long key_idx);

/* Must match feed_collapse.HOST_PROC_KEYS order. */
static const char *const HOST_PROC_KEYS[] = {
  "uid", "vm_peak", "vm_size", "vm_lck", "vm_hwm", "vm_rss", "vm_data",
  "vm_stk", "vm_exe", "vm_lib", "vm_pte", "vm_swap", "threads",
};
static const Py_ssize_t HOST_PROC_N =
  (Py_ssize_t)(sizeof(HOST_PROC_KEYS) / sizeof(HOST_PROC_KEYS[0]));

static void
free_char_ptrs(char **ptrs, Py_ssize_t n)
{
  if (ptrs == NULL) {
    return;
  }
  for (Py_ssize_t i = 0; i < n; i++) {
    PyMem_Free(ptrs[i]);
  }
  PyMem_Free(ptrs);
}

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
      free_char_ptrs(ptrs, i);
      PyErr_SetString(PyExc_TypeError, "lines must be str");
      return -1;
    }
    const char *utf8 = PyUnicode_AsUTF8(item);
    if (utf8 == NULL) {
      free_char_ptrs(ptrs, i);
      return -1;
    }
    const size_t len = strlen(utf8);
    char *owned = (char *)PyMem_Malloc(len + 1);
    if (owned == NULL) {
      free_char_ptrs(ptrs, i);
      PyErr_NoMemory();
      return -1;
    }
    memcpy(owned, utf8, len + 1);
    ptrs[i] = owned;
  }
  *out_ptrs = ptrs;
  return 0;
}

static int
parse_lines_and_slot(PyObject *args, PyObject **list_obj, long *slot)
{
  *slot = 0;
  if (!PyArg_ParseTuple(args, "O!|l", &PyList_Type, list_obj, slot)) {
    return -1;
  }
  if (*slot < 0 || *slot >= MAX_CODON_SLOTS) {
    PyErr_SetString(PyExc_ValueError, "codon slot out of range");
    return -1;
  }
  return 0;
}

static PyObject *
feed_and_collapse_fingerprint_py(PyObject *self, PyObject *args)
{
  PyObject *list_obj = NULL;
  long slot = 0;
  if (parse_lines_and_slot(args, &list_obj, &slot) < 0) {
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
    slot,
    (long)n,
    ptrs,
    &raw_stats,
    &collapsed_rows,
    &value_sum,
    &proc_rows
  );
  free_char_ptrs(ptrs, n);
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
  long slot = 0;
  if (parse_lines_and_slot(args, &list_obj, &slot) < 0) {
    return NULL;
  }
  char **ptrs = NULL;
  Py_ssize_t n = 0;
  if (fill_char_ptrs(list_obj, &ptrs, &n) < 0) {
    return NULL;
  }
  long n_stats = 0;
  long n_procs = 0;
  parse_stats_lines_codon_run_c(slot, (long)n, ptrs, &n_stats, &n_procs);
  free_char_ptrs(ptrs, n);

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
    v = PyFloat_FromDouble(pss_time_c(slot, i));
    rc |= v == NULL || PyDict_SetItemString(row, "time", v) < 0;
    Py_XDECREF(v);
    v = py_str_from_codon(pss_host_c(slot, i));
    rc |= v == NULL || PyDict_SetItemString(row, "host", v) < 0;
    Py_XDECREF(v);
    v = py_str_from_codon(pss_jid_c(slot, i));
    rc |= v == NULL || PyDict_SetItemString(row, "jid", v) < 0;
    Py_XDECREF(v);
    v = py_str_from_codon(pss_type_c(slot, i));
    rc |= v == NULL || PyDict_SetItemString(row, "type", v) < 0;
    Py_XDECREF(v);
    v = py_str_from_codon(pss_dev_c(slot, i));
    rc |= v == NULL || PyDict_SetItemString(row, "dev", v) < 0;
    Py_XDECREF(v);
    v = py_str_from_codon(pss_event_c(slot, i));
    rc |= v == NULL || PyDict_SetItemString(row, "event", v) < 0;
    Py_XDECREF(v);
    v = PyFloat_FromDouble(pss_value_c(slot, i));
    rc |= v == NULL || PyDict_SetItemString(row, "value", v) < 0;
    Py_XDECREF(v);
    v = PyLong_FromLong(pss_wid_c(slot, i));
    rc |= v == NULL || PyDict_SetItemString(row, "wid", v) < 0;
    Py_XDECREF(v);
    v = PyFloat_FromDouble(pss_mult_c(slot, i));
    rc |= v == NULL || PyDict_SetItemString(row, "mult", v) < 0;
    Py_XDECREF(v);
    v = py_str_from_codon(pss_unit_c(slot, i));
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
    v = py_str_from_codon(psp_jid_c(slot, i));
    rc |= v == NULL || PyDict_SetItemString(row, "jid", v) < 0;
    Py_XDECREF(v);
    v = py_str_from_codon(psp_host_c(slot, i));
    rc |= v == NULL || PyDict_SetItemString(row, "host", v) < 0;
    Py_XDECREF(v);
    v = py_str_from_codon(psp_proc_c(slot, i));
    rc |= v == NULL || PyDict_SetItemString(row, "proc", v) < 0;
    Py_XDECREF(v);
    for (Py_ssize_t k = 0; k < HOST_PROC_N; k++) {
      long fv = psp_field_c(slot, i, (long)k);
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
    "Fingerprint: (raw_stats, collapsed_rows, value_sum, proc_rows) [slot optional]",
  },
  {
    "parse_stats_lines_codon",
    parse_stats_lines_codon_py,
    METH_VARARGS,
    "Finish()-shaped parse: (stats_records, proc_rows) [slot optional]",
  },
  {NULL, NULL, 0, NULL},
};

static int
hpcperfstats_codon_parse_exec(PyObject *module)
{
  if (PyModule_AddFunctions(module, codon_methods) < 0) {
    return -1;
  }
  if (PyModule_AddIntConstant(module, "MAX_CODON_SLOTS", MAX_CODON_SLOTS) < 0) {
    return -1;
  }
  return 0;
}

static PyModuleDef_Slot codon_slots[] = {
  {Py_mod_exec, (void *)hpcperfstats_codon_parse_exec},
  {Py_mod_gil, Py_MOD_GIL_NOT_USED},
  {0, NULL},
};

static struct PyModuleDef codon_module = {
  PyModuleDef_HEAD_INIT,
  .m_name = "hpcperfstats_codon_parse",
  .m_doc = "Codon feed+collapse (C-ABI + multi-phase FT init, GIL_NOT_USED)",
  .m_size = 0,
  .m_slots = codon_slots,
};

PyMODINIT_FUNC
PyInit_hpcperfstats_codon_parse(void)
{
  return PyModuleDef_Init(&codon_module);
}
