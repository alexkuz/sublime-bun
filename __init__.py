import sys
import os
import threading 
import fnmatch
import json

import sublime
import sublime_plugin
from subprocess import PIPE, Popen

PLUGIN_NAME = "Bun"

def check_syntax(syntax = ""):
    if syntax.startswith("scope:") and sublime.find_syntax_by_scope(syntax.split(":")[1]):
        return True
    if sublime.find_syntax_by_name(syntax):
        return True
    if sublime.syntax_from_path(syntax):
        return True
    return False

def get_setting(view, key, default_value=None):
    settings_filename = '{0}.sublime-settings'.format(PLUGIN_NAME)

    settings = view.settings().get(PLUGIN_NAME)
    if settings is None or settings.get(key) is None:
        settings = sublime.load_settings(settings_filename)

    value = settings.get(key, default_value)

    return value

def expand_var(window, var_to_expand):
    if var_to_expand:
        expanded = os.path.expanduser(var_to_expand)
        expanded = os.path.expandvars(expanded)
        if window:
            window_variables = window.extract_variables()
            expanded = sublime.expand_variables(expanded, window_variables)
        return expanded

    return var_to_expand


def is_supported_file(view, filename):
    bun_binary_files = get_setting(view, "bun_binary_files", [])

    return next(True for file in bun_binary_files if fnmatch.fnmatch(filename, file["pattern"]))


def update_hint(view, text):
    view.erase_phantoms("bun-prettify")
    if text:
        template = '<body style="background-color: #a8201a; padding: 3px 10px;">{0}</body>'
        view.add_phantom("bun-prettify", sublime.Region(0), template.format(text), sublime.LAYOUT_INLINE)


class BunPreviewBinaryCommand(sublime_plugin.TextCommand):
    def run(self, edit, prettified_text):
        try:
            if not self.is_supported_file():
                return
            if prettified_text:
                self.preview_prettified(edit, prettified_text)
            else:
                self.preview_binary(edit)

        except Exception as err:
            self.view.replace(edit, sublime.Region(0), "\n")
            print("ERROR: {0}".format(err))
            update_hint(self.view, str(err))
            self.view.set_scratch(True)

    def is_supported_file(self):
        filepath = self.view.file_name()
        if not filepath:
            return False

        [dirname, filename] = os.path.split(filepath)

        if not is_supported_file(self.view, filename):
            return False

        return True

    def preview_prettified(self, edit, prettified_text):
        region = sublime.Region(0, self.view.size())
        self.view.set_read_only(False)
        update_hint(self.view, None)
        self.view.replace(edit, region, prettified_text)
        self.view.set_read_only(True)
        self.view.set_scratch(True)

    def preview_binary(self, edit):
        filepath = self.view.file_name()
        [dirname, filename] = os.path.split(filepath)

        region = sublime.Region(0, self.view.size())
        
        command = ["./%s" % filename]

        bun_path = expand_var(self.view.window(), get_setting(self.view, "bun_path"))

        env = os.environ.copy()
        if bun_path + ":" not in env["PATH"]:
            env["PATH"] = bun_path + ":" + env["PATH"]

        with Popen(command, cwd=dirname, stdout=PIPE, stderr=PIPE, shell=False, env=env) as process:
            res = process.communicate()
            if process.returncode != 0:
                raise RuntimeError("{0}\n(Return code: {1})".format(res[1].decode("utf-8"), process.returncode))
            output = res[0].decode("utf-8")

        bun_binary_files = get_setting(self.view, "bun_binary_files", [])
        config = next(file for file in bun_binary_files if fnmatch.fnmatch(filename, file["pattern"]))

        syntax = config.get("syntax", "scope:text.plain")
        if not check_syntax(syntax):
            syntax = "scope:text.plain"

        # Bun doesn't use node_modules.bun anymore, so there's no need to prettify

        prettify = False # config.get("pretty", False)

        prettify_options = get_setting(self.view, "prettify_options", {})
        win_id = self.view.window().id()

        self.view.set_read_only(False)
        replace_text = "\n\n{0}".format(output) if prettify else output
        self.view.replace(edit, region, replace_text)
        self.view.assign_syntax(syntax)

        if prettify:
            update_hint(self.view, "Prettifying...")
            sublime.set_timeout_async(lambda: self.prettify(output, filepath, win_id, prettify_options), 0)

        self.view.set_read_only(True)
        self.view.set_scratch(True)

    def prettify(self, output, filepath, win_id, prettify_options):
        try:
            import dprint_python_bridge
            options = json.dumps(prettify_options)
            prettified = dprint_python_bridge.format_text(filepath, output, options)
        except Exception as err:
            update_hint(self.view, str(err))

        for window in sublime.windows():
            if window.id() == win_id:
                window.active_view().run_command("bun_preview_binary", {'prettified_text': prettified})


class BunLockbViewEventListener(sublime_plugin.ViewEventListener):
    def on_load(self):
        [dirname, filename] = os.path.split(self.view.file_name())

        if not is_supported_file(self.view, filename):
            return

        self.view.run_command("bun_preview_binary", {'prettified_text': None})
