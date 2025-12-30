import re


def natural_sort_key(s):
    """
    Generates a sorting key for natural alphanumeric sorting.
    """
    return [
        int(text) if text.isdigit() else text.lower()
        for text in re.split("([0-9]+)", s)
    ]
