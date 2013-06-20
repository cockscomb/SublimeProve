import sublime, sublime_plugin
import os.path
import re
import subprocess

class ExecTestCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        current_region = self.view.sel()[0]
        current_class = self.get_region_name_by_selector(current_region, 'entity.name.type.class')
        current_function = self.get_region_name_by_selector(current_region, 'entity.name.function')
        self.execute(current_class, current_function)

    def execute(self, package, method):
        """execute test"""
        env = {}
        build_env = self.view.settings().get('build_env')
        if build_env and build_env.get('PATH'):
            env['PATH'] = build_env['PATH']

        test_file = self.test_file_name_by_class_name(package)

        args = self.commands(test_file, method)
        env = self.modified_environ(env, test_file, method)

        directory = self.get_project_root()
        if not directory:
            print('Cannot get project root')
            return

        def async_execute():
            with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=directory, env=env) as proc:
                output = proc.stdout.read().decode('utf-8')
                sublime.set_timeout(self.show_panel(output), 0) # Do in main thread

        sublime.set_timeout_async(async_execute, 0) # Async

    def commands(self, test_file, method_name):
        """override this"""
        return []

    def modified_environ(self, env, test_file, method_name):
        """override this"""
        return env

    def test_file_name_by_class_name(self, class_name):
        """override this"""
        return class_name

    def show_panel(self, text):
        """show output on panel"""
        output_panel = self.view.window().create_output_panel('prove_result_panel')
        output_panel.run_command('append', {'characters': text})
        self.view.window().run_command('show_panel', {'panel': 'output.prove_result_panel'})

    def get_project_root(self):
        """find git repository root with git command"""
        filename = self.view.file_name()
        if not filename:
            return None

        git_root = None
        with subprocess.Popen(['git', 'rev-parse', '--show-toplevel'], stdout=subprocess.PIPE, cwd=os.path.dirname(filename)) as proc:
            git_root = proc.stdout.read().decode('utf-8').strip()

        return git_root

    def get_region_name_by_selector(self, region, selector):
        """get name matching the selector lie directly on current cursor position
        Examples:
            'entity.name.type.class' for the class name,
            'entity.name.function' for the function name
        """
        name_regions = self.view.find_by_selector(selector)

        name = None
        for name_region in name_regions:
            line = self.view.line(name_region)
            if region.b < line.a:
                break
            name = self.view.substr(name_region)

        return name

class ProveCommand(ExecTestCommand):
    def commands(self, test_file, method_name):
        return ['carton', 'exec', '--', 'prove', test_file, '-v']

    def modified_environ(self, env, test_file, method_name):
        return env

    def test_file_name_by_class_name(self, class_name):
        if re.match('^t::', class_name):
            return self.view.file_name()

        parts = re.split('\W+', class_name)
        parts.pop(-1)
        name = '-'.join(parts)
        return "t/{}.t".format(name)

class ProveAllCommand(ProveCommand):
    def commands(self, test_file, method_name):
        return ['carton', 'exec', '--', 'prove', '-v']

class ProveMethodCommand(ProveCommand):
    def modified_environ(self, env, test_file, method_name):
        if method_name:
            env['TEST_METHOD'] = method_name
        return env

