from pathlib import Path

from setuptools import find_packages, setup

# Read README if available
this_dir: Path = Path(__file__).parent
readme_path: Path = this_dir / "README.md"
long_description: str = (readme_path.read_text(
    encoding="utf-8") if readme_path.exists() else "")

setup(
    name="wizedispatcher",
    version="0.1.0",
    author="Joao Lopes",
    author_email="joaoslopes@gmail.com",
    description=("Multiple-dispatch method and function overloading system "
                 "with advanced type matching."),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kairos-xx/wizedispatcher",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.9",
    install_requires=[],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries",
    ],
    license="MIT",
    keywords="dispatch multiple-dispatch overloading typing",
)
