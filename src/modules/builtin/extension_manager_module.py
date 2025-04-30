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
import json

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
    """
    Parse docstring of a function
    :param func: function
    :return: docstring attributes as dict
    """

    # Get function signature
    sig = inspect.signature(func)

    # Required params
    required_params = [
        name for name, param in sig.parameters.items()
        if param.default == inspect.Parameter.empty
    ]

    # Param types
    param_types = {name: param.annotation for name, param in sig.parameters.items()}

    # Get docstring lines
    docstring_lines = str(inspect.getdoc(func)).split("\n")

    # Description
    description_lines = [line.strip() for line in docstring_lines if not line.strip().startswith(":")]
    description = " ".join(description_lines).replace("\n", " ")

    # Params
    param_lines = [line.strip() for line in docstring_lines if line.strip().startswith(":param")]
    params = {}
    for param_line in param_lines:
        items = param_line.split(":")
        name = items[1][5:].strip()
        params.update({
            name: {
                "type": param_types.get(name),
                "description": items[2].strip(),
                "required": name in required_params
            }
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
        """
        Constructor
        :param module_id: provided
        :param extension_dir_path: directory where extension files are located; provided
        :param kwargs: kwargs to module
        """

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
                raise KeyError(f"Function '{name}' already registered")

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
        """
        Get function descriptions as str (for system prompt)
        :return: function descriptions
        """

        # List of funcs
        func_strings = []

        # For each func
        for func_name in self._extension_functions.keys():

            # Get func entry
            func_entry = self._extension_functions.get(func_name)

            # Assemble dictionary
            func_dict = {
                "name": func_name,
                "description": func_entry.get("description"),
                "parameters": {
                    parameter_name: {
                        "type": parameter_entry.get("type").__name__,
                        "description": parameter_entry.get("description"),
                        "required": "true" if parameter_entry.get("required") else "false"
                    }
                    for parameter_name, parameter_entry in func_entry.get("parameters").items()
                }
            }

            # Dump to string
            func_string = json.dumps(func_dict, indent=4)
            func_strings.append(func_string)

        return ",\n".join(func_strings)

    def function_call(
            self,
            func_name,
            kwargs
    ):
        """
        Do function call
        :param func_name: function name
        :param kwargs: kwargs for function call (as dict)
        :return: Function result
        """

        # Get target function
        target = self._extension_functions.get(func_name)

        # Call function if found
        if target:
            return target.get("function")(**kwargs)

        # Exception if not found
        else:
            raise KeyError(f"Function '{func_name} not found")


    def process_instruction(
            self,
            instruction
    ) -> None:
        """
        Overloaded - process single instruction
        :param instruction: provided
        :return: None
        """

        # Function call instruction
        if instruction.get("instruction_type") == "function_call":

            # Parse to json
            parsed = json.loads(instruction.get("message"))

            # Do function call
            self.function_call(
                func_name=parsed.get("function_name"),
                kwargs=parsed.get("arguments")
            )
