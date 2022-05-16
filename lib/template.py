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

    def get_file_parameters(self) -> set[str]:
        env = jinja2.Environment(undefined=jinja2.DebugUndefined)
        template = env.from_string(self.raw_input)
        rendered = template.render()
        ast = env.parse(rendered)
        self.requested_vars = find_undeclared_variables(ast)

        return self.requested_vars

    def process_template(self, parameters: dict) -> str:
        raw_template = jinja2.Template(self.raw_input)
        self.formatted_template = raw_template.render(parameters)

        return self.formatted_template

    def process_vars(self, driver_class, variables: set[str], cloud_vars: list[tuple]):
        for variable in variables:
            func = next((t[2] for f in variables for t in cloud_vars if t[0] == f), None)
            value = getattr(driver_class, func)()
            print(f"value = {value}")
