from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="qwen-tts-client",
    version="0.1.0",
    author="Qwen TTS Developers",
    author_email="developer@example.com",
    description="A Python client for Qwen3 TTS service",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/samsha1971/qwen-tts-client",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.7",
    install_requires=[
        "requests>=2.25.0",
        "sseclient-py>=1.8.0"
    ],
)
