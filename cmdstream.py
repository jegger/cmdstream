# Wrapped arround answer of
#  http://stackoverflow.com/questions/6809590/merging-a-python-scripts-subprocess-stdout-and-stderr-while-keeping-them-disti
# (T.Rojan)

# Only supposed to work on Linux / Mac
# Wrapper to check the output of a command (as stream) by line
# and be able to set a timeout

import subprocess
import select
import psutil
import time


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
        tsk = subprocess.Popen(command,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

        poll = select.poll()
        poll.register(tsk.stdout, select.POLLIN | select.POLLHUP)
        poll.register(tsk.stderr, select.POLLIN | select.POLLHUP)
        pollc = 2
        events = poll.poll()
        while pollc > 0 and len(events) > 0:
            # Check for timeout
            if timeout:
                if start_time+timeout < time.time():
                    self.kill(tsk.pid)
                    break
            # Check stdout / stderr
            for event in events:
                (rfd, event) = event
                if event & select.POLLIN:
                    if rfd == tsk.stdout.fileno():
                        line = tsk.stdout.readline()
                        if len(line) > 0:
                            if self.on_stdout(line[:-1]):
                                self.kill(tsk.pid)
                                break
                    if rfd == tsk.stderr.fileno():
                        line = tsk.stderr.readline()
                        if len(line) > 0:
                            if self.on_stderr(line[:-1]):
                                self.kill(tsk.pid)
                                break
                if event & select.POLLHUP:
                    poll.unregister(rfd)
                    pollc -= 1
                if pollc > 0:
                    events = poll.poll()
        tsk.wait()

    def kill(self, proc_pid):
        # Kills a process and its subs
        process = psutil.Process(proc_pid)
        for proc in process.children(recursive=True):
            proc.kill()
        process.kill()

    def on_stdout(self, stdout):
        print("Stdout: %s" % stdout)
        return False

    def on_stderr(self, stderr):
        print("Stderr:" % stderr)
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