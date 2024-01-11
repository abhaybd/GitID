from setuptools import setup

setup(
    name="gitid",
    version="0.2.4",
    author="Abhay Deshpande",
    description="Command-line tool for managing multiple git identities on the same machine",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/abhaybd/GitID",
    py_modules=["gitid.main"],
    scripts=["bin/gitid"],
    install_requires=[
        "PyYAML"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX",
        "Environment :: Console",
        "Topic :: Software Development :: Version Control :: Git",
        "Topic :: Utilities",
        "Intended Audience :: Developers"
    ]
)
