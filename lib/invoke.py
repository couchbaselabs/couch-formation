##
##

import distutils.spawn
import subprocess
import time
from lib.exceptions import *
from lib.output import spinner


class packer_run(object):

    def __init__(self):
        self.check_binary()

    def check_binary(self) -> bool:
        if not distutils.spawn.find_executable("packer"):
            raise PackerRunError("can not find packer executable")

        return True

    def fix_text(self, data: str) -> str:
        data = data.replace('%!(PACKER_COMMA)', ',')
        data = data.replace('\t', ' ')
        data = data.replace('\\n', '')
        data = data.replace('\n', '')
        return data

    def parse_output(self, line: bytes) -> dict:
        message: dict = {
            'timestamp': None,
            'target': None,
            'type': None,
            'content': None,
            'message': None
        }
        line_string = line.decode("utf-8")
        line_string = line_string.rstrip()
        line_contents: list = line_string.split(",")

        message['timestamp'] = line_contents[0]
        message['target'] = line_contents[1] if len(line_contents) > 1 else None
        message['type'] = line_contents[2] if len(line_contents) > 2 else None
        message['content'] = self.fix_text(line_contents[3]) if len(line_contents) > 3 else None
        message['message'] = self.fix_text(line_contents[4]) if len(line_contents) > 4 else None

        return message

    def _packer(self, *args: str, working_dir=None):
        error_string: str = ''
        packer_cmd = [
            'packer',
            '-machine-readable',
            *args
        ]

        p = subprocess.Popen(packer_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=working_dir, bufsize=1)

        sp = spinner()
        sp.start()
        while True:
            line = p.stdout.readline()
            if not line:
                break
            message = self.parse_output(line)
            if message['type'] == 'error':
                error_string += message['content']

        sp.stop()
        p.communicate()
        if p.returncode != 0:
            raise PackerRunError(f"error: {error_string}")

    def build(self, working_dir: str, var_file: str, packer_file: str):
        cmd = []

        cmd.append('build')
        cmd.append('-var-file')
        cmd.append(var_file)
        cmd.append(packer_file)

        print("Beginning packer build (this can take several minutes)")
        start_time = time.perf_counter()
        self._packer(*cmd, working_dir=working_dir)
        end_time = time.perf_counter()
        run_time = time.strftime("%H hours %M minutes %S seconds.", time.gmtime(end_time - start_time))
        print(f"Image creation complete in {run_time}.")
