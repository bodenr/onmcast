from setuptools import setup, find_packages

setup(
    name='onmcast',
    version='0.1',
    description='oslo-messaging notification multicast',
    author='Boden',
    author_email='bodenru@gmail.com',
    classifiers=[
        'Development Status :: 1 - Beta',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Intended Audience :: Developers'
    ],
    platforms=['Any'],
    include_package_data=True,
    zip_safe=False,
    provides=['onmcast'],
    scripts=[],
    packages=find_packages(),
    install_requires=[],
    setup_requires=[],
    entry_points={
        'oslo.messaging.notify.drivers': [
            'messaging-multicast = onmcast.notify.driver:AMQPMulticastDriver'
        ]
    }
)