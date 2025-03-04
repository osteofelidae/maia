"""
Module to manage extensions (function calling)
"""

# INTERNAL DEPENDENCIES
from src.modules.module import AsyncModule
from abc import ABC
from src.utils.config_utils import config
from src.utils.path_utils import path, Path

# DEPENDENCIES
import importlib
import importlib.util
import inspect

# EXTENSION DECORATOR
def extension(func):
    """
    Decorator to mark functions as extensions
    :param func: function
    :return: func
    """

    func.is_extension = True
    return func

# FUNCTIONS
def _parse_docstring(
        func
):
    # TODO docstring

    # Get lines
    docstring_lines = inspect.getdoc(func).split("\n")

    # Description
    description_lines = [line.strip() for line in docstring_lines if not line.strip().startswith(":")]
    description = " ".join(description_lines).replace("\n", " ")

    # Params
    param_lines = [line.strip() for line in docstring_lines if line.strip().startswith(":param")]
    params = {}
    for param_line in param_lines:
        items = param_line.split(":")
        params.update({
            items[1][5:].strip(): items[2].strip()
        })

    # Return value
    return_lines = [line.strip() for line in docstring_lines if line.strip().startswith(":return")]
    return_val = return_lines[-1][8:].strip()

    return [description, params, return_val]

# EXTENSION MANAGER MODULE
class ExtensionManagerAsyncModule(AsyncModule, ABC):

    def __init__(
            self,
            module_id: str = "extension_manager",
            extension_dir_path: str = config.get("extension_dir_path"),
            **kwargs
    ):
        # TODO docstring

        # Instance variables
        self._extension_functions = {}  # Extension functions

        # Detect modules
        module_paths = [p for p in list(path(extension_dir_path).iterdir()) if p.is_file()]

        # Import extension functions
        for module_path in module_paths:
            self.load_extension(module_path)

        # Super init
        super().__init__(
            module_id,
            **kwargs
        )

    def load_extension(
            self,
            extension_path: Path
    ):
        """
        Load a single extension
        :param extension_path: path to extension
        :return: self
        """

        # Get extension path
        extension_path = str(extension_path)
        module_name = extension_path.split("/")[-1].split(".")[0]

        # Import module
        spec = importlib.util.spec_from_file_location(module_name, extension_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Get functions from module
        funcs_parsed = [[func, str(name)] + _parse_docstring(func) for name, func in inspect.getmembers(module, inspect.isfunction) if getattr(func, 'is_extension', False)]

        # Add each function to extension functions
        for func, name, description, parameters, return_value in funcs_parsed:

            # Check whether function already exists
            if name in self._extension_functions.keys():
                pass  # TODO exception

            # Add entry
            self._extension_functions.update({
                name: {
                    "description": description,
                    "parameters": parameters,
                    "return_value": return_value,
                    "function": func
                }
            })

        # Chaining
        return self

    def get_extension_descriptions(self):
        # TODO docstring

        result_str = ""

        # Add each line
        for name in self._extension_functions.keys():

            entry = self._extension_functions.get(name)

            result_str += f"* {name}: {entry.get('description')}\n"

            result_str += "\t* Parameters:\n"
            parameters = entry.get('parameters')
            for parameter in parameters.keys():

                result_str += f"\t\t{parameter}: {parameters.get(parameter)}\n"

            result_str += f"\t* Return value: {entry.get('return_value')}\n"

        return result_str

    def process_instruction(
            self,
            instruction
    ) -> None:
        return  # TODO