# MAIA
**THIS IS CURRENTLY A WORK IN PROGRESS**\
MAIA stands for Modular AI Assistant. It features a full, upgradeable API, pretrained LLM (coming soon), RAG/HyDE, and a 
user-friendly extension system for adding callable functions. See below for details.

## Configuration
By default, the configuration file is in `config/config.json`. **DOCUMENTATION TO BE ADDED**

## Extensions
Any `.py` file in `extensions/` will be scanned for decorated functions. To mark a function as callable,
import the decorator then decorate the function like so:
```python
from src.modules.builtin.extension_manager_module import extension

@extension
def add_two(a: int, b: int):
    """
    Adds two numbers.
    :param a: int value 1
    :param b: int value 2
    :return: int result
    """

    return a+b
```
For best results, annotate the types of all parameters and include a docstring as shown above.