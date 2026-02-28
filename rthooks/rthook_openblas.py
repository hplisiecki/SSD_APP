import os

# Limit OpenBLAS to a single thread to prevent stack overflows in worker
# threads on macOS (SIGBUS / KERN_PROTECTION_FAILURE in blas_thread_server).
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
