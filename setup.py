from setuptools import setup, find_packages

setup(
    name="driftwatch",
    version="0.1.0",
    description="Real-time training/serving skew detector for ML pipelines",
    long_description="Real-time training/serving skew detector for ML pipelines",
    long_description_content_type="text/markdown",
    author="DriftWatch",
    python_requires=">=3.10",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.26.0",
        "pandas>=2.2.0",
        "scipy>=1.12.0",
        "scikit-learn>=1.4.0",
        "fastapi>=0.111.0",
        "uvicorn>=0.30.0",
        "pydantic>=2.7.0",
        "anthropic>=0.28.0",
    ],
    extras_require={
        "api": ["fastapi>=0.111.0", "uvicorn>=0.30.0", "python-multipart>=0.0.9"],
        "dev": ["httpx>=0.27.0", "pytest>=8.0.0"],
    },
    entry_points={
        "console_scripts": [
            "driftwatch=driftwatch.cli.main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)