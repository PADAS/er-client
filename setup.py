from setuptools import setup
import re

version_file = open("dasclient/version.py").read()
version_data = dict(re.findall("__([a-z]+)__\s*=\s*'([^']+)'", version_file))

setup(
      name='dasclient',
      version=version_data['version'],
      description='DAS Client Tools For Python',
      url='http://github.com/PADAS/das-clients/python',
      author='Chris Doehring',
      author_email='integration@pamdas.org',
      license='MIT',
      packages=['dasclient'],
      platforms=u'Posix; MacOS X; Windows',
      install_requires=['requests',],
      zip_safe=False,
      classifiers=[
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.4',
      ]
      )
