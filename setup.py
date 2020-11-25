import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='django-cas-provider',
    version='0.3.3',
    description='A "provider" for the Central Authentication Service (http://jasig.org/cas)',
    author='MIT Open Learning',
    author_email='mitx-devops@mit.edu',
    url='https://github.com/mitocw/django-cas-provider',
    packages=find_packages(),
    include_package_data=True,
    license='MIT',
    long_description=read('README.rst'),
    zip_safe=False,
    install_requires=['setuptools'],
    classifiers = [
        "Development Status :: 3 - Alpha",
        "Framework :: Django :: 2.2",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires='>=3.8'
)
