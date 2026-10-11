"""Bounded local process lifetime and resource containment (no learning code)."""

import ctypes
from ctypes import wintypes as wt
import json
import os
from pathlib import Path
import threading
import time


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".writing")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def process_alive(pid):
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    kernel.OpenProcess.restype = wt.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
    kernel.CloseHandle.argtypes = [wt.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        code = wt.DWORD()
        return (
            bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code)))
            and code.value == 259
        )
    finally:
        kernel.CloseHandle(handle)


class WindowsJob:
    """Kill the complete trainer/native-worker tree when its owner exits."""

    def __init__(self, *, memory_mib=3072, cpu_percent=12.5):
        if os.name != "nt":
            raise RuntimeError("hard_resource_launcher_currently_requires_windows")
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel = k
        k.GetCurrentProcess.restype = wt.HANDLE
        k.CreateJobObjectW.argtypes = [ctypes.c_void_p, wt.LPCWSTR]
        k.CreateJobObjectW.restype = wt.HANDLE
        k.SetInformationJobObject.argtypes = [
            wt.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wt.DWORD,
        ]
        k.AssignProcessToJobObject.argtypes = [wt.HANDLE, wt.HANDLE]
        k.IsProcessInJob.argtypes = [wt.HANDLE, wt.HANDLE, ctypes.POINTER(wt.BOOL)]
        k.CloseHandle.argtypes = [wt.HANDLE]
        k.QueryInformationJobObject.argtypes = [
            wt.HANDLE,
            ctypes.c_int,
            ctypes.c_void_p,
            wt.DWORD,
            ctypes.c_void_p,
        ]
        member = wt.BOOL()
        self._check(k.IsProcessInJob(k.GetCurrentProcess(), None, ctypes.byref(member)))
        self.inherited_job = bool(member.value)

        class Basic(ctypes.Structure):
            _fields_ = [
                ("per_process", ctypes.c_int64),
                ("per_job", ctypes.c_int64),
                ("flags", wt.DWORD),
                ("min_ws", ctypes.c_size_t),
                ("max_ws", ctypes.c_size_t),
                ("active_limit", wt.DWORD),
                ("affinity", ctypes.c_size_t),
                ("priority", wt.DWORD),
                ("scheduling", wt.DWORD),
            ]

        class IO(ctypes.Structure):
            _fields_ = [
                (name, ctypes.c_uint64)
                for name in (
                    "read_ops",
                    "write_ops",
                    "other_ops",
                    "read_bytes",
                    "write_bytes",
                    "other_bytes",
                )
            ]

        class Extended(ctypes.Structure):
            _fields_ = [
                ("basic", Basic),
                ("io", IO),
                ("process_memory", ctypes.c_size_t),
                ("job_memory", ctypes.c_size_t),
                ("peak_process", ctypes.c_size_t),
                ("peak_job", ctypes.c_size_t),
            ]

        class CPU(ctypes.Structure):
            _fields_ = [("flags", wt.DWORD), ("rate", wt.DWORD)]

        self.extended_type = Extended
        self.handle = k.CreateJobObjectW(None, None)
        self._check(self.handle)
        try:
            limits = Extended()
            limits.basic.flags = (
                0x2000 | 0x200 | 0x8
            )  # kill-on-close, aggregate memory, active processes
            limits.basic.active_limit = 12
            limits.job_memory = memory_mib * 1024 * 1024
            self._check(
                k.SetInformationJobObject(
                    self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)
                )
            )
            cpu = CPU(0x1 | 0x4, int(cpu_percent * 100))  # enabled hard cap
            self._check(
                k.SetInformationJobObject(
                    self.handle, 15, ctypes.byref(cpu), ctypes.sizeof(cpu)
                )
            )
            self._check(k.AssignProcessToJobObject(self.handle, k.GetCurrentProcess()))
        except BaseException:
            k.CloseHandle(self.handle)
            raise
        # Retain the handle until process exit. Closing it deliberately kills this process too.

    def usage(self):
        class Accounting(ctypes.Structure):
            _fields_ = [
                ("user", ctypes.c_int64),
                ("kernel", ctypes.c_int64),
                ("period_user", ctypes.c_int64),
                ("period_kernel", ctypes.c_int64),
                ("faults", wt.DWORD),
                ("processes", wt.DWORD),
                ("active", wt.DWORD),
                ("terminated", wt.DWORD),
            ]

        accounting, limits = Accounting(), self.extended_type()
        self._check(
            self.kernel.QueryInformationJobObject(
                self.handle,
                1,
                ctypes.byref(accounting),
                ctypes.sizeof(accounting),
                None,
            )
        )
        self._check(
            self.kernel.QueryInformationJobObject(
                self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits), None
            )
        )
        return {
            "tree_cpu_seconds": (accounting.user + accounting.kernel) / 1e7,
            "peak_job_memory_bytes": limits.peak_job,
            "active_processes": accounting.active,
        }

    @staticmethod
    def _check(result):
        if not result:
            raise ctypes.WinError(ctypes.get_last_error())


class RuntimeLimit:
    def __init__(self, output, seconds):
        self.output = Path(output)
        self.deadline = time.monotonic() + seconds
        self.finished = threading.Event()
        threading.Thread(target=self._watch, daemon=True).start()

    def stopping(self):
        return time.monotonic() >= self.deadline or (self.output / "STOP").exists()

    def _watch(self):
        # If native I/O or an evaluation blocks, the job still has a bounded lifetime.
        while not self.finished.wait(1):
            if self.stopping():
                if not self.finished.wait(30):
                    atomic_json(
                        self.output / "watchdog.json",
                        {
                            "reason": "deadline_or_stop_grace_exceeded",
                            "recover_from": "last_complete_checkpoint",
                        },
                    )
                    os._exit(124)
                return
