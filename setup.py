from setuptools import setup, find_packages

setup(
    name="gitid",
    version="0.1.0",
    author="Abhay Deshpande",
    description="Command-line tool for managing multiple git identities on the same machine",
    long_description=open("README.md").read(),
    packages=find_packages(include=["gitid", "gitid.*"]),
    scripts=["bin/gitid"],
    install_requires=[
        "PyYAML"
    ]
)
