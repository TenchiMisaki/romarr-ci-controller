"""Owned Windows process trees for dormant platform probes.

Independent Win32 adapter: create suspended, assign a kill-on-close job, then
resume. Only explicitly listed standard handles are inherited. No breakaway,
shell, process-name killing, credentials or candidate execution at import time.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes as w
import os
from pathlib import Path
import shutil
import subprocess
import time


class OwnedWindowsProcess:
    """Minimal process interface with unconditional job-wide cleanup."""

    def __init__(self, args, *, env, cwd=None):
        if os.name != 'nt':
            raise OSError('Windows required')
        import msvcrt
        self.stdout = self.stderr = None
        self._job = self._process = None
        self.returncode = None
        self._api = ctypes.WinDLL('kernel32', use_last_error=True)
        self._bind()
        handles = []
        fds = []
        attribute_buffer = None
        attributes_ready = False
        thread = None
        try:
            self._job = self._api.CreateJobObjectW(None, None)
            self._check(self._job)
            limits = ExtendedLimits()
            limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
            self._check(self._api.SetInformationJobObject(
                self._job, 9, ctypes.byref(limits), ctypes.sizeof(limits)))
            stdin_fd = os.open(os.devnull, os.O_RDONLY)
            fds.append(stdin_fd)
            for label in ('stdout', 'stderr'):
                read_fd, write_fd = os.pipe()
                fds.extend((read_fd, write_fd))
                setattr(self, label, os.fdopen(read_fd, 'rb', buffering=0))
                fds.remove(read_fd)
            # fds: stdin, stdout writer, stderr writer; readers never inherit.
            handles = [msvcrt.get_osfhandle(fd) for fd in fds]
            for handle in handles:
                os.set_handle_inheritable(handle, True)
            size = ctypes.c_size_t()
            self._api.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
            attribute_buffer = ctypes.create_string_buffer(size.value)
            self._check(self._api.InitializeProcThreadAttributeList(
                attribute_buffer, 1, 0, ctypes.byref(size)))
            attributes_ready = True
            inherited = (w.HANDLE * len(handles))(*handles)
            self._check(self._api.UpdateProcThreadAttribute(
                attribute_buffer, 0, 0x20002, inherited,
                ctypes.sizeof(inherited), None, None))  # HANDLE_LIST
            startup = StartupInfoEx()
            startup.StartupInfo.cb = ctypes.sizeof(startup)
            startup.StartupInfo.dwFlags = 0x100  # USESTDHANDLES
            startup.StartupInfo.hStdInput, startup.StartupInfo.hStdOutput, startup.StartupInfo.hStdError = handles
            startup.lpAttributeList = ctypes.cast(attribute_buffer, ctypes.c_void_p)
            executable = shutil.which(str(args[0]), path=env.get('PATH', ''))
            if not executable or Path(executable).suffix.lower() not in {'.exe', '.com'}:
                raise OSError('Executable unavailable or unsupported')
            command_line = ctypes.create_unicode_buffer(subprocess.list2cmdline([str(x) for x in args]))
            environment = ctypes.create_unicode_buffer(
                '\0'.join(k+'='+v for k, v in sorted(env.items(), key=lambda x:x[0].upper()))+'\0\0')
            info = ProcessInfo()
            self._check(self._api.CreateProcessW(executable, command_line, None, None, True,
                0x4 | 0x80000 | 0x8000000 | 0x400, environment, cwd,
                ctypes.byref(startup), ctypes.byref(info)))
            self._process, thread, self.pid = info.hProcess, info.hThread, info.dwProcessId
            # No application instruction or descendant can run before ownership.
            self._check(self._api.AssignProcessToJobObject(self._job, self._process))
            if self._api.ResumeThread(thread) == 0xffffffff:
                raise ctypes.WinError(ctypes.get_last_error())
        except BaseException:
            if self._process:
                # Assignment may have failed: terminate this exact suspended process.
                self._api.TerminateProcess(self._process, 1)
                self._api.WaitForSingleObject(self._process, 5000)
            self.close()
            for stream in (self.stdout, self.stderr):
                if stream is not None:
                    stream.close()
            raise
        finally:
            if thread:
                self._api.CloseHandle(thread)
            if attributes_ready:
                self._api.DeleteProcThreadAttributeList(attribute_buffer)
            for fd in fds:
                os.close(fd)

    def _bind(self):
        """Declare pointer-sized API signatures; never truncate native handles."""
        specs = {
            'CreateJobObjectW': ([ctypes.c_void_p, w.LPCWSTR], w.HANDLE),
            'SetInformationJobObject': ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD], w.BOOL),
            'QueryInformationJobObject': ([w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD, ctypes.c_void_p], w.BOOL),
            'AssignProcessToJobObject': ([w.HANDLE, w.HANDLE], w.BOOL),
            'TerminateJobObject': ([w.HANDLE, w.UINT], w.BOOL),
            'TerminateProcess': ([w.HANDLE, w.UINT], w.BOOL),
            'InitializeProcThreadAttributeList': ([ctypes.c_void_p, w.DWORD, w.DWORD, ctypes.POINTER(ctypes.c_size_t)], w.BOOL),
            'UpdateProcThreadAttribute': ([ctypes.c_void_p, w.DWORD, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p], w.BOOL),
            'DeleteProcThreadAttributeList': ([ctypes.c_void_p], None),
            'CreateProcessW': ([w.LPCWSTR, w.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, w.BOOL,
                               w.DWORD, ctypes.c_void_p, w.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p], w.BOOL),
            'ResumeThread': ([w.HANDLE], w.DWORD),
            'WaitForSingleObject': ([w.HANDLE, w.DWORD], w.DWORD),
            'GetExitCodeProcess': ([w.HANDLE, ctypes.POINTER(w.DWORD)], w.BOOL),
            'CloseHandle': ([w.HANDLE], w.BOOL),
        }
        for name, (args, result) in specs.items():
            function = getattr(self._api, name)
            function.argtypes, function.restype = args, result

    @staticmethod
    def _check(result):
        """Surface native failures without proceeding with unowned execution."""
        if not result:
            raise ctypes.WinError(ctypes.get_last_error())

    def poll(self):
        """Distinguish a running process from a legitimate exit code of 259."""
        if self.returncode is None:
            status = self._api.WaitForSingleObject(self._process, 0)
            if status == 0:
                code = w.DWORD()
                self._check(self._api.GetExitCodeProcess(self._process, ctypes.byref(code)))
                self.returncode = code.value
            elif status != 258:
                raise ctypes.WinError(ctypes.get_last_error())
        return self.returncode

    def kill(self):
        """Terminate only the owned job, including surviving descendants."""
        if self._job:
            self._check(self._api.TerminateJobObject(self._job, 1))

    def close(self):
        """Kill and verify zero active members even after successful parent exit."""
        try:
            if self._job:
                self.kill()
                deadline = time.monotonic()+5
                while True:
                    counts = BasicAccounting()
                    self._check(self._api.QueryInformationJobObject(
                        self._job, 1, ctypes.byref(counts), ctypes.sizeof(counts), None))
                    if not counts.ActiveProcesses:
                        break
                    if time.monotonic() >= deadline:
                        raise OSError('Owned job cleanup not confirmed')
                    time.sleep(.01)
        finally:
            if self._job:
                self._api.CloseHandle(self._job)
                self._job = None
            if self._process:
                self._api.CloseHandle(self._process)
                self._process = None


class BasicLimits(ctypes.Structure):
    """JOBOBJECT_BASIC_LIMIT_INFORMATION layout."""
    _fields_ = [('PerProcessUserTimeLimit', ctypes.c_longlong), ('PerJobUserTimeLimit', ctypes.c_longlong),
        ('LimitFlags', w.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
        ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', w.DWORD),
        ('Affinity', ctypes.c_size_t), ('PriorityClass', w.DWORD), ('SchedulingClass', w.DWORD)]


class IoCounters(ctypes.Structure):
    """IO_COUNTERS uses six unsigned 64-bit counters."""
    _fields_ = [(name, ctypes.c_ulonglong) for name in ('ReadOperationCount', 'WriteOperationCount',
        'OtherOperationCount', 'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]


class ExtendedLimits(ctypes.Structure):
    """JOBOBJECT_EXTENDED_LIMIT_INFORMATION layout."""
    _fields_ = [('BasicLimitInformation', BasicLimits), ('IoInfo', IoCounters),
        ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t),
        ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]


class BasicAccounting(ctypes.Structure):
    """JOBOBJECT_BASIC_ACCOUNTING_INFORMATION for cleanup verification."""
    _fields_ = [(name, ctypes.c_longlong) for name in ('TotalUserTime', 'TotalKernelTime',
        'ThisPeriodTotalUserTime', 'ThisPeriodTotalKernelTime')] + [(name, w.DWORD) for name in
        ('TotalPageFaultCount', 'TotalProcesses', 'ActiveProcesses', 'TotalTerminatedProcesses')]


class StartupInfo(ctypes.Structure):
    """STARTUPINFOW layout, including explicit standard handles."""
    _fields_ = [('cb', w.DWORD), ('lpReserved', w.LPWSTR), ('lpDesktop', w.LPWSTR), ('lpTitle', w.LPWSTR)] + [
        (name, w.DWORD) for name in ('dwX', 'dwY', 'dwXSize', 'dwYSize', 'dwXCountChars',
        'dwYCountChars', 'dwFillAttribute', 'dwFlags')] + [('wShowWindow', w.WORD),
        ('cbReserved2', w.WORD), ('lpReserved2', ctypes.c_void_p), ('hStdInput', w.HANDLE),
        ('hStdOutput', w.HANDLE), ('hStdError', w.HANDLE)]


class StartupInfoEx(ctypes.Structure):
    """STARTUPINFOEXW with an explicit inherited-handle attribute list."""
    _fields_ = [('StartupInfo', StartupInfo), ('lpAttributeList', ctypes.c_void_p)]


class ProcessInfo(ctypes.Structure):
    """PROCESS_INFORMATION handles belong to this adapter only."""
    _fields_ = [('hProcess', w.HANDLE), ('hThread', w.HANDLE), ('dwProcessId', w.DWORD), ('dwThreadId', w.DWORD)]
