##
##

import logging
import jinja2
from jinja2.meta import find_undeclared_variables
from lib.exceptions import TemplateError


class template(object):

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.raw_input = None
        self.requested_vars = set()
        self.formatted_template = None
        self.parameters = {}
        self.cloud = None

    def read_file(self, file: str) -> bool:
        try:
            with open(file, 'r') as inputFile:
                self.raw_input = inputFile.read()
            inputFile.close()
        except OSError as err:
            raise TemplateError(f"can not read template file: {err}")

        return True

    def write_file(self, file: str) -> bool:
        try:
            with open(file, 'w') as write_file:
                write_file.write(self.formatted_template)
                write_file.write("\n")
                write_file.close()
        except OSError as err:
            raise TemplateError(f"can not write template file: {err}")

        return True

    def get_file_parameters(self) -> set[str]:
        env = jinja2.Environment(undefined=jinja2.DebugUndefined)
        template = env.from_string(self.raw_input)
        rendered = template.render()
        ast = env.parse(rendered)
        self.requested_vars = find_undeclared_variables(ast)

        return self.requested_vars

    def process_template(self, cloud_vars: list[tuple]) -> str:
        parameters = dict((a, d) for a, b, c, d in cloud_vars)
        raw_template = jinja2.Template(self.raw_input)
        self.formatted_template = raw_template.render(parameters)

        return self.formatted_template

    def process_vars(self, driver_class, variables: set[str], cloud_vars: list[tuple]) -> list[tuple]:
        processed_set = []
        for variable in variables:
            param, tfv, func, value = next(((a, b, c, d) for (a, b, c, d) in cloud_vars if a == variable), (None, None, None, None))
            if not func:
                continue
            print(f"Processing template parameter {variable}")
            value = getattr(driver_class, func)()
            processed_set.append((param, tfv, func, value))

        return processed_set
