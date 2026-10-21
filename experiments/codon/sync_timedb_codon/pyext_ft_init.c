/*
 * Multi-phase Python module for Codon feed_collapse under free-threaded 3.14t.
 *
 * Codon 0.20.4 --pyext PyInit/Create2 and from_python converters are GIL-ABI
 * and SIGSEGV / fail under /opt/python3.14t. We build the Codon unit with
 * --lib (@export C entry), marshal List[str] -> char** here, and expose a
 * normal METH_VARARGS method that calls feed_and_collapse_fingerprint_c.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>

/* Codon --lib @export (name verified by nm in build script). */
extern void feed_and_collapse_fingerprint_c(
  long n,
  char **ptr,
  long *out_raw,
  long *out_collapsed,
  double *out_value_sum,
  double *out_proc_rows
);

static PyObject *
feed_and_collapse_fingerprint_py(PyObject *self, PyObject *args)
{
  PyObject *list_obj = NULL;
  if (!PyArg_ParseTuple(args, "O!", &PyList_Type, &list_obj)) {
    return NULL;
  }
  const Py_ssize_t n = PyList_GET_SIZE(list_obj);
  char **ptrs = NULL;
  if (n > 0) {
    ptrs = (char **)PyMem_Calloc((size_t)n, sizeof(char *));
    if (ptrs == NULL) {
      return PyErr_NoMemory();
    }
  }
  for (Py_ssize_t i = 0; i < n; i++) {
    PyObject *item = PyList_GET_ITEM(list_obj, i);
    if (!PyUnicode_Check(item)) {
      PyMem_Free(ptrs);
      PyErr_SetString(PyExc_TypeError, "lines must be str");
      return NULL;
    }
    ptrs[i] = (char *)PyUnicode_AsUTF8(item);
    if (ptrs[i] == NULL) {
      PyMem_Free(ptrs);
      return NULL;
    }
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

static PyMethodDef codon_methods[] = {
  {
    "feed_and_collapse_fingerprint",
    feed_and_collapse_fingerprint_py,
    METH_VARARGS,
    "Fingerprint: (raw_stats, collapsed_rows, value_sum, proc_rows)",
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
