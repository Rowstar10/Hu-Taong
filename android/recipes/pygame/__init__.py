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
        # pygame 2.6.1's Android list of modules leaves out the SIMD blitters its desktop list has,
        # which surface needs on x86_64 (an emulator, a Chromebook)
        with current_directory(self.get_build_dir(arch.arch)):
            setup = open("Setup").read()
            simd = "src_c/simd_blitters_sse2.c src_c/simd_blitters_avx2.c "
            if simd not in setup:
                setup = setup.replace("surface src_c/surface.c", "surface " + simd + "src_c/surface.c")
                open("Setup", "w").write(setup)

    def build_arch(self, arch):
        # (here, not in prebuild_arch: p4a prebuilds every recipe before it builds any, so the
        # build machine's Python, which Cython runs in, isn't there yet then)
        self.make_cython_parts(arch)
        super().build_arch(arch)

    def make_cython_parts(self, arch):
        with current_directory(self.get_build_dir(arch.arch)):
            marker = ".cython-regenerated"
            if os.path.exists(marker):
                return
            # (Cython 3.1 and 3.2 understand the Python in the APK; 3.3 refuses pygame 2.6.1's _sprite.pyx)
            info("Making pygame's Cython parts afresh for this Python")
            self.install_hostpython_prerequisites(packages=["setuptools", "cython>=3.1,<3.3"])
            # only the C that Cython made (src_c/_sdl2/touch.c, for one, is written by hand)
            for pyx in glob.glob("src_c/cython/pygame/**/*.pyx", recursive=True):
                made = os.path.join("src_c", os.path.relpath(pyx, "src_c/cython/pygame"))[:-len(".pyx")] + ".c"
                if os.path.exists(made):
                    os.remove(made)
            env = self.get_hostrecipe_env(arch)
            shprint(sh.Command(self.real_hostpython_location), "setup.py", "cython_only", _env=env)
            open(marker, "w").close()


recipe = Pygame261Recipe()
