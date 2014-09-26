from .monkey_patch import is_patched, monkey_patch_orm


if not is_patched():
    monkey_patch_orm()
