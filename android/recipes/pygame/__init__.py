"""pygame 2.6.1 for Android: the same pygame the PC game uses.

python-for-android's own recipe is pygame 2.1.0, which no longer builds against its SDL2 and
Python.  This one builds 2.6.1 from its source release (which has pygame's Android build
settings), with its Cython parts made afresh for the Python inside the APK.
"""
import glob
import os

from pythonforandroid.recipes.pygame import Pygame2Recipe
from pythonforandroid.toolchain import current_directory, info, shprint
import sh


class Pygame261Recipe(Pygame2Recipe):
    version = "2.6.1"
    url = "https://files.pythonhosted.org/packages/source/p/pygame/pygame-{version}.tar.gz"
    sha512sum = "67ae07be50822dac5b2ce4b04a04920dc22ac4d43c348e2a95646c7646ca82b822a1fd7b89a295406581969303235831e00aeec4ea29e975a80f8013170eee5d"

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            marker = ".cython-regenerated"
            if os.path.exists(marker):
                return
            info("Making pygame's Cython parts afresh for this Python")
            self.install_hostpython_prerequisites(packages=["setuptools", "cython>=3.1"])
            generated = glob.glob("src_c/_sdl2/*.c") + ["src_c/_sprite.c", "src_c/pypm.c"]
            for path in generated:
                if os.path.exists(path):
                    os.remove(path)
            env = self.get_hostrecipe_env(arch)
            shprint(sh.Command(self.real_hostpython_location), "setup.py", "cython_only", _env=env)
            open(marker, "w").close()


recipe = Pygame261Recipe()
