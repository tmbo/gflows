from setuptools import setup, find_packages
import io
import os

here = os.path.abspath(os.path.dirname(__file__))

# Avoids IDE errors, but actual version is read from version.py
__version__ = None
exec(open('gflows/version.py').read())

# Get the long description from the README file
with io.open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

tests_requires = [
    "pytest~=3.5",
    "pytest-pep8~=1.0",
    "pytest-cov~=2.5",
    "httpretty~=0.9",
]

install_requires = [
    "flask~=1.0",
    "PyGithub~=1.43",
]

setup(
        name='gflows',
        packages=find_packages(exclude=["tests", "tools"]),
        version=__version__,
        classifiers=[
            "Programming Language :: Python :: 3.6"
        ],
        install_requires=install_requires,
        tests_require=tests_requires,
        include_package_data=True,
        description="GitHub workflow automation",
        long_description=long_description,
        long_description_content_type="text/markdown",
        license="MIT",
        author='tmbo',
        author_email='tombocklisch@gmail.com',
        project_urls={
            "Bug Reports": "https://github.com/tmbo/gflows/issues",
            "Source": "https://github.com/tmbo/gflows",
        },
)
