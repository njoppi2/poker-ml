import uuid
import random
import requests
from typing import List, Tuple

def reorder_list(old_list, condition):
    try:
        index = next(i for i, item in enumerate(old_list) if condition(item))
    except StopIteration:
        # If the condition is not satisfied by any element, return the original list
        return old_list

    return old_list[index:] + old_list[:index]