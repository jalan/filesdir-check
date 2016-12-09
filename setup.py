from setuptools import setup


setup(
    name="filesdir-check",
    entry_points={
        "console_scripts": ["filesdir-check = filesdir_check:main"],
    },
)
