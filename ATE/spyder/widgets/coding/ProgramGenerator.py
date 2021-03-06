import os
from jinja2 import Environment
from jinja2 import FileSystemLoader
from ATE.spyder.widgets.coding.generators import BaseGenerator


class test_program_generator(BaseGenerator):
    def indexgen(self):
        self.last_index = self.last_index + 1
        return self.last_index

    def __init__(self, prog_name, owner, datasource):
        self.datasource = datasource
        self.last_index = 0
        self.current_param_id = 0
        template_path = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
        file_loader = FileSystemLoader(template_path)
        env = Environment(loader=file_loader)
        env.trim_blocks = True
        env.lstrip_blocks = True
        env.rstrip_blocks = True
        env.globals.update(idgen=self.indexgen)
        template_name = str(self.__class__.__name__).split('.')[-1].split(' ')[0]
        template_name = 'testprogram_template.jinja2'
        if not os.path.exists(os.path.join(template_path, template_name)):
            raise Exception(f"couldn't find the template : {template_name}")
        template = env.get_template(template_name)
        file_name = f"{prog_name}.py"

        rel_path_to_dir = self._generate_relative_path()
        abs_path_to_dir = os.path.join(datasource.project_directory, rel_path_to_dir)
        self.abs_path_to_file = os.path.join(abs_path_to_dir, file_name)

        if not os.path.exists(abs_path_to_dir):
            os.makedirs(abs_path_to_dir)

        if os.path.exists(self.abs_path_to_file):
            os.remove(self.abs_path_to_file)

        program_configuration = self.datasource.get_program_configuration_for_owner(owner, prog_name)
        test_list, test_imports = self.build_test_entry_list(datasource, owner, prog_name)

        output = template.render(test_list=test_list, test_imports=test_imports, program_configuration=program_configuration)

        with open(self.abs_path_to_file, 'w', encoding='utf-8') as fd:
            fd.write(output)

    def build_test_entry_list(self, datasource, owner, prog_name):
        # step 1: Get tests and test params in sequence
        tests_in_program = datasource.get_tests_for_program(prog_name, owner)

        # step 2: Get all testtargets for progname
        test_targets = datasource.get_test_targets_for_program(prog_name)

        # step 3: Augment sequences with actual classnames
        test_list = []
        test_imports = {}
        for program_entry in tests_in_program:
            test_class = self.resolve_class_for_test(program_entry.test, test_targets)
            test_module = self.resolve_module_for_test(program_entry.test, test_targets)
            params = program_entry.definition

            for op in params['output_parameters']:
                params['output_parameters'][op]['id'] = self.current_param_id
                self.current_param_id += 1

            test_imports.update({test_module: test_class})
            test_list.append({"test_name": program_entry.test,
                              "test_class": test_class,
                              "test_module": test_module,
                              "test_number": self.current_param_id,
                              "sbin": params['sbin'],
                              "instance_name": params['description'],
                              "output_parameters": params['output_parameters'],
                              "input_parameters": params['input_parameters']})

            self.current_param_id += 1

        return test_list, test_imports

    def resolve_class_for_test(self, test_name, test_targets):
        for target in test_targets:
            if target.test == test_name:
                if target.is_default:
                    return f"{test_name}"
                return f"{target.name}"
        raise Exception(f"Cannot resolve class for test {test_name}")

    def resolve_module_for_test(self, test_name, test_targets):
        for target in test_targets:
            if target.test == test_name:
                if target.is_default:
                    return f"{test_name}.{test_name}"
                return f"{test_name}.{target.name}"
        raise Exception(f"Cannot resolve module for test {test_name}")

    def _generate_relative_path(self):
        hardware = self.datasource.active_hardware
        base = self.datasource.active_base
        return os.path.join('src', hardware, base)

    def _generate_render_data(self, abs_path=''):
        pass

    def _render(self, template, render_data):
        pass

    @staticmethod
    def append_exception_code(prog_path: str):
        msg = "raise Exception('test program is invalid')\n"
        with open(prog_path, 'r+') as f:
            content = f.read()
            f.seek(0, 0)
            f.write(msg + content)
