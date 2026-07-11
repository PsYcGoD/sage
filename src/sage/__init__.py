__version__ = "2.4.7"

# Auto-install on first import
def _auto_install():
    try:
        from sage.install import is_sage_installed_system_wide, install_sage_system_wide
        if not is_sage_installed_system_wide():
            install_sage_system_wide(verbose=False)
    except Exception:
        pass  # Silent fail - don't break imports

_auto_install()
