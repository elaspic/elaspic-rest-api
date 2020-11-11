from setuptools import find_packages, setup


def read_md(file):
    with open(file) as fin:
        return fin.read()


setup(
    name="elaspic-rest-api",
    version="0.1.0",
    description="ELASPIC REST API",
    long_description=read_md("README.md"),
    author="Alexey Strokach",
    author_email="alex.strokach@utoronto.ca",
    url="https://gitlab.com/elaspic/elaspic-rest-api",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "aiohttp[speedups]",
        "jinja2",
        "bleach",
        "sentry-sdk",
        "aiomysql",
    ],
    package_data={"elaspic_rest_api": ["scripts/*", "templates/*"]},
    include_package_data=True,
    zip_safe=False,
    keywords="elaspic_rest_api",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    test_suite="tests",
)
