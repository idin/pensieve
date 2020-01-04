from setuptools import setup, find_packages


def readme():
    with open('./README.md') as f:
        return f.read()


setup(
    name='pensieve',
    version='2019.12.29.4',
    license='MIT',

    author='Idin',
    author_email='py@idin.ca',
    url='https://github.com/idin/pensieve',

    keywords='graph computation',
    description='Implementation of a computation graph',
    long_description=readme(),
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],

    packages=find_packages(exclude=("jupyter_tests", ".idea", ".git")),
    install_requires=['dill', 'toposort', 'disk', 'slytherin', 'chronometry', 'abstract', 'joblib', 'pandas'],
    python_requires='~=3.6',
    zip_safe=True,
    test_suite='nose.collector',
    tests_require=['nose', 'coverage']
)
