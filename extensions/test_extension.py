from src.modules.builtin.extension_manager_module import extension

@extension
def add_two(a: int, b: int):
    """
    Adds two numbers
    :param a: int value 1
    :param b: int value 2
    :return: int result
    """

    return a+b

@extension
def sub_two(a: int, b: int):
    """
    Subtract b from a
    :param a: int value 1
    :param b: int value 2
    :return: int result
    """

    return a-b

def not_test_extension():
    return