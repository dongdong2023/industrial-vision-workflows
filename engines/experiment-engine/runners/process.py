"""Bound elapsed time and keep process output on disk."""
import os
import signal
import subprocess
import time


def execute(argv, cwd, env, timeout):
    start = time.perf_counter()
    with (cwd / "stdout.log").open("wb") as out, (cwd / "stderr.log").open("wb") as err:
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=out, stderr=err,
                                   start_new_session=os.name != "nt",
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
        timed_out = False
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
            else:
                os.killpg(process.pid, signal.SIGKILL)
            if process.poll() is None:
                process.kill()
            code = process.wait()
    return {"returncode": code, "timed_out": timed_out, "wall_seconds": time.perf_counter() - start}
