from .monkey_patch import is_patched, patch


if not is_patched():
    patch()
