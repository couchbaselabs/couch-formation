##
##

import distutils.spawn
import subprocess
import time
import re
import json
from datetime import datetime
from typing import Union
from lib.exceptions import *
from lib.output import spinner
from lib.logfile import log_file


class packer_run(object):

    def __init__(self, working_dir=None):
        _logger = log_file(self.__class__.__name__, path=working_dir, filename='build.log')
        self.logger = _logger.logger
        self.working_dir = working_dir
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

    def log_output(self, line: Union[str, bytes]):
        if type(line) == bytes:
            line_string = line.decode("utf-8")
            line_string = line_string.rstrip()
        else:
            line_string = line
        self.logger.info(line_string)

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
        self.log_output(line_string)
        line_contents: list = line_string.split(",")

        message['timestamp'] = line_contents[0]
        message['target'] = line_contents[1] if len(line_contents) > 1 else None
        message['type'] = line_contents[2] if len(line_contents) > 2 else None
        message['content'] = self.fix_text(line_contents[3]) if len(line_contents) > 3 else None
        message['message'] = self.fix_text(line_contents[4]) if len(line_contents) > 4 else None

        return message

    def _packer(self, *args: str, no_output=False):
        error_string: str = ''
        if no_output:
            packer_cmd = [
                'packer',
                *args
            ]
        else:
            packer_cmd = [
                'packer',
                '-machine-readable',
                *args
            ]

        p = subprocess.Popen(packer_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self.working_dir, bufsize=1)

        sp = spinner()
        sp.start()
        while True:
            line = p.stdout.readline()
            if not line:
                break
            if no_output:
                self.log_output(line)
            else:
                message = self.parse_output(line)
                if message['type'] == 'error':
                    error_string += message['content']

        sp.stop()
        p.communicate()
        if p.returncode != 0:
            raise PackerRunError(f"error: {error_string}")

    def init(self):
        cmd = []

        cmd.append('init')
        cmd.append('.')

        print("Beginning packer init")
        start_time = time.perf_counter()
        self._packer(*cmd, no_output=True)
        end_time = time.perf_counter()
        run_time = time.strftime("%H hours %M minutes %S seconds.", time.gmtime(end_time - start_time))
        print(f"Init complete in {run_time}.")

    def build(self, var_file: str, packer_file: str):
        cmd = []

        cmd.append('build')
        cmd.append('-var-file')
        cmd.append(var_file)
        cmd.append(packer_file)

        print("Beginning packer build (this can take several minutes)")
        start_time = time.perf_counter()
        self._packer(*cmd)
        end_time = time.perf_counter()
        run_time = time.strftime("%H hours %M minutes %S seconds.", time.gmtime(end_time - start_time))
        print(f"Image creation complete in {run_time}.")


class tf_run(object):

    def __init__(self, working_dir=None):
        _logger = log_file(self.__class__.__name__, path=working_dir)
        self.logger = _logger.logger
        self.working_dir = working_dir
        self.deployment_data = None
        self.check_binary()

    def check_binary(self) -> bool:
        if not distutils.spawn.find_executable("terraform"):
            raise PackerRunError("can not find terraform executable")

        return True

    def _terraform(self, *args: str, json_output=False, ignore_error=False):
        command_output = ''
        tf_cmd = [
            'terraform',
            *args
        ]

        p = subprocess.Popen(tf_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=self.working_dir, bufsize=1)

        sp = spinner()
        sp.start()
        while True:
            line = p.stdout.readline()
            if not line:
                break
            line_string = line.decode("utf-8")
            escape_char = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            line_string = escape_char.sub('', line_string)
            if json_output:
                command_output += line_string
            else:
                line_string = line_string.rstrip()
                self.logger.info(line_string)

        sp.stop()
        p.communicate()
        if p.returncode != 0:
            if ignore_error:
                return False
            else:
                raise TerraformRunError(f"environment deployment error (see log file for details)")

        if len(command_output) > 0:
            try:
                self.deployment_data = json.loads(command_output)
            except json.decoder.JSONDecodeError as err:
                raise TerraformRunError(f"can not capture deployment output: {err}")

        return True

    def _command(self, cmd: list, json_output=False, quiet=False, ignore_error=False):
        now = datetime.now()
        time_string = now.strftime("%D %I:%M:%S %p")
        self.logger.info(f" --- start {cmd[0]} at {time_string}")

        start_time = time.perf_counter()
        result = self._terraform(*cmd, json_output=json_output, ignore_error=ignore_error)
        end_time = time.perf_counter()
        run_time = time.strftime("%H hours %M minutes %S seconds.", time.gmtime(end_time - start_time))

        now = datetime.now()
        time_string = now.strftime("%D %I:%M:%S %p")
        self.logger.info(f" --- end {cmd[0]} at {time_string}")

        if not quiet:
            print(f"Step complete in {run_time}.")

        return result

    def init(self):
        cmd = []

        cmd.append('init')
        cmd.append('-input=false')

        print("Initializing environment")
        self._command(cmd)

    def apply(self):
        cmd = []

        cmd.append('apply')
        cmd.append('-input=false')
        cmd.append('-auto-approve')

        print("Deploying environment")
        self._command(cmd)

    def destroy(self, refresh=True, ignore_error=False):
        cmd = []

        cmd.append('destroy')
        cmd.append('-input=false')
        cmd.append('-auto-approve')
        if not refresh:
            cmd.append('-refresh=false')
        else:
            ignore_error = True

        print("Removing environment")
        if not self._command(cmd, ignore_error=ignore_error):
            print("First destroy attempt failed, retrying without refresh ...")
            self.destroy(refresh=False, ignore_error=False)

    def validate(self):
        cmd = []

        cmd.append('validate')

        return self._command(cmd, ignore_error=True, quiet=True)

    def output(self, quiet=False):
        cmd = []

        cmd.append('output')
        cmd.append('-json')

        if not quiet:
            print("Getting environment information")
        self._command(cmd, json_output=True, quiet=quiet)

        return self.deployment_data
