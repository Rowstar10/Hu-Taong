"""six, which python-for-android's pyjnius recipe asks for.

With no recipe of its own, p4a installs it with pip in a virtualenv it makes for each kind of
phone processor, and the second one breaks the first's pip. As a recipe it's simply installed.
"""
from pythonforandroid.recipe import PythonRecipe


class SixRecipe(PythonRecipe):
    version = "1.17.0"
    url = "https://files.pythonhosted.org/packages/source/s/six/six-{version}.tar.gz"
    depends = ["setuptools"]
    call_hostpython_via_targetpython = False
    install_in_hostpython = False


recipe = SixRecipe()
