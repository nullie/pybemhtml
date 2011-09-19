try:
    from setuptools import setup, find_packages
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages
    
version = '0.1'

setup(
    name="pybemhtml",
    version=version,
    description="BEM Javascript to Python compiler",
    long_description="""""",
    keywords='bem javascript ecmascript compiler',
    license='BSD License',
    author='Ilya Novoselov',
    author_email='ilya.novoselov@gmail.com',
    url='https://github.com/nullie/pybemhtml',
    packages=['pybemhtml'],
    zip_safe=False,
    include_package_data=True,
    test_suite = 'nose.collector',
    setup_requires=[
        'nose'
    ],
    install_requires=[
        "pyjsparser>=0.1",
        "simplejson>=2.1",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
    ]
)
