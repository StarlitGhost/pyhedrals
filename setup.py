import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name = "pyhedrals",
    version = "0.1.2",
    author = "StarlitGhost",
    author_email = "starlitwraith@gmail.com",
    description = "A library for evaluating tabletop dice roll expressions",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/StarlitGhost/pyhedrals",
    packages = setuptools.find_packages(),
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Games/Entertainment",
        "Topic :: Games/Entertainment :: Role-Playing",
    ],
    install_requires = [
        "sly>=0.3",
    ],
    python_requires = ">=3.6"
)
