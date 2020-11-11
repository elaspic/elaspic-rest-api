from setuptools import find_packages, setup


def read_file(file):
    with open(file) as fin:
        return fin.read()


setup(
    name="elaspic-rest-api",
    version="0.1.0",
    description="ELASPIC REST API",
    long_description=read_file("README.md"),
    long_description_content_type="text/markdown",
    author="Alexey Strokach",
    author_email="alex.strokach@utoronto.ca",
    url="https://gitlab.com/elaspic/elaspic-rest-api",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "aiomysql>=0.0.20",
        "astapi>=0.61.1",
        "bleach>=3.2.1",
        "fire>=0.3.1",
        "jinja2>=2.11.2",
        "sentry-sdk>=0.19.2",
        "uvicorn>=0.11.8",
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
