"""Long-lived offline transport. Own it with a context manager or explicit close."""
from __future__ import annotations
import json
from queue import Empty, Queue
import subprocess
from threading import Event, Lock, Thread
from advisor.showdown_bridge import BRIDGE_SCRIPT, ShowdownBridge, ShowdownBridgeError, silent_process_options


class ShowdownWorker(ShowdownBridge):
    """Load the verified immutable external build once; serialize bounded requests.

    A timeout or malformed response destroys the worker. The next request starts
    a fresh verified process; no partial result or old session is reused.
    """
    def __init__(self, checkout, *, timeout_s=10.0):
        super().__init__(checkout, timeout_s=timeout_s)
        self._lock = Lock()
        self._process = None
        self._reader = None
        self._responses = Queue()
        self._request_id = 0
        self._generation = 0
        self._interrupted = Event()

    def __enter__(self): return self
    def __exit__(self, *_): self.close()

    def _start(self):
        if self._interrupted.is_set(): raise ShowdownBridgeError("showdown_cancelled")
        self._verify_checkout()
        if self._interrupted.is_set(): raise ShowdownBridgeError("showdown_cancelled")
        self._responses = Queue()
        self._process = subprocess.Popen(
            ["node", str(BRIDGE_SCRIPT.with_name("worker.cjs")), str(self.checkout)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", bufsize=1,
            **silent_process_options(),
        )
        self._generation += 1
        stream, responses = self._process.stdout, self._responses
        def read():
            try:
                while line := stream.readline(32 * 1024 * 1024 + 1):
                    if len(line) > 32 * 1024 * 1024 or not line.endswith("\n"):
                        responses.put(None)
                        break
                    responses.put(line)
            except (OSError, ValueError): pass
            finally: responses.put(None)
        self._reader = Thread(target=read, daemon=True, name="showdown-response")
        self._reader.start()

    def run(self, request):
        with self._lock:
            try:
                if self._interrupted.is_set(): raise ShowdownBridgeError("showdown_cancelled")
                if self._process is None or self._process.poll() is not None:
                    self._stop()
                    self._start()
                self._request_id += 1
                payload = json.dumps({"request_id": self._request_id, "request": request}, ensure_ascii=True, allow_nan=False)
                if len(payload.encode("utf-8")) > 8 * 1024 * 1024:
                    raise ShowdownBridgeError("showdown_request_too_large")
                self._process.stdin.write(payload + "\n")
                self._process.stdin.flush()
                line = self._responses.get(timeout=self.timeout_s)
                if line is None: raise ShowdownBridgeError("showdown_worker_exited")
                envelope = json.loads(line)
                if envelope.get("request_id") != self._request_id:
                    raise ShowdownBridgeError("showdown_worker_request_mismatch")
                response = envelope.get("response")
                if not isinstance(response, dict): raise ShowdownBridgeError("showdown_invalid_response")
                return self._validate_response(request, response)
            except Empty as exc:
                self._stop()
                raise ShowdownBridgeError("showdown_timeout") from exc
            except (OSError, ValueError, TypeError, ShowdownBridgeError) as exc:
                self._stop()
                if isinstance(exc, ShowdownBridgeError): raise
                raise ShowdownBridgeError("showdown_unavailable_or_invalid_response") from exc

    def _stop(self):
        process, self._process = self._process, None
        if process is None: return
        if process.poll() is None:
            process.terminate()
            try: process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        if process.stdin: process.stdin.close()
        if self._reader: self._reader.join(timeout=2)
        if process.stdout: process.stdout.close()
        self._reader = None

    def close(self):
        with self._lock: self._stop()

    @property
    def generation(self):
        """Coordinator identity; no native handles survive a process restart."""
        return self._generation

    @property
    def is_alive(self):
        process = self._process
        return not self._interrupted.is_set() and process is not None and process.poll() is None

    def interrupt(self):
        """Cancel local execution from the UI without waiting for the request lock.

        The reader wakes the running request; normal run/close owns cleanup.
        No partial result is reusable; construct a new worker after cancellation.
        """
        self._interrupted.set()
        process = self._process
        if process is not None:
            try:
                if process.poll() is None: process.terminate()
            except OSError: pass
