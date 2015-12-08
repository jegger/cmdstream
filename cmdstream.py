# Wrapped arround answer of
#  http://stackoverflow.com/questions/6809590/merging-a-python-scripts-subprocess-stdout-and-stderr-while-keeping-them-disti
# (T.Rojan & J.F.Sebastian)

# Only supposed to work on Linux / Mac
# Wrapper to check the output of a command (as stream) by line
# and be able to set a timeout

import subprocess
import select
import psutil
import time
import pty
import os


class CMDStream(object):
    """
    Call run() with your command. Overwrite on_stdout, on_stderr and on_timeout
    to get notified whenever such an event happens.

    on_stdout and on_stderr: Return True to kill the command.
    """

    def run(self, command, timeout=False):
        """
        :param command: cmd list for Popen()
        :param timeout: optional in seconds
        """
        start_time = time.time()
        master_fd, slave_fd = pty.openpty()
        p = subprocess.Popen(command,
                             stdout=slave_fd,
                             stderr=subprocess.PIPE)

        with os.fdopen(master_fd) as stdout:
            poll = select.poll()
            poll.register(stdout, select.POLLIN)
            poll.register(p.stderr, select.POLLIN | select.POLLHUP)

            def cleanup(_done=[]):
                if _done:
                    return
                _done.append(1)
                poll.unregister(p.stderr)
                p.stderr.close()
                poll.unregister(stdout)
                assert p.poll() is not None

            while True:
                events = poll.poll(40)
                if not events and p.poll() is not None:
                    # no IO events and the subprocess exited
                    cleanup()
                    break

                # Check for timeout
                if timeout:
                    if start_time+timeout < time.time():
                        self.on_timeout()
                        self.kill(p.pid)
                        break

                for fd, event in events:
                    if event & select.POLLIN:
                        # there is something to read
                        if fd == stdout.fileno():
                            out = stdout.readline().rstrip()
                            if self.on_stderr(out):
                                self.kill(p.pid)
                                break
                        if fd == p.stderr.fileno():
                            err = p.stderr.readline().rstrip()
                            if self.on_stderr(err):
                                self.kill(p.pid)
                                break
                    elif event & select.POLLHUP:
                        # free resources if stderr hung up
                        cleanup()
                    else:
                        # something unexpected happened
                        assert 0
        p.wait()

    def kill(self, proc_pid):
        # Kills a process and its subs
        process = psutil.Process(proc_pid)
        for proc in process.children(recursive=True):
            proc.kill()
        process.kill()

    def on_stdout(self, stdout):
        print(stdout)
        return False

    def on_stderr(self, stderr):
        print(stderr)
        return False

    def on_timeout(self):
        print("Timeout")


if __name__ == '__main__':
    # Example usage
    def stderr(stderr):
        print("own-handled: %s" % stderr)
        if stderr == "Timeout":
            return True  # This should exit

    def stdout(stdout):
        print("own-handled: %s" % stdout)

    stream = CMDStream()
    stream.on_stderr = stderr
    stream.on_stdout = stdout
    stream.run(("ping", "google.com"))