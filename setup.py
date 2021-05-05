import os
from pkg_resources import require
from setuptools import setup, find_packages

version = '0.5.post1.dev0'

# Environment markers aren't sufficiently support with earlier setuptools
require('setuptools >= 20.8.1')

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()

install_requires = [
    'click',
    'jinja2',
    'lxml',
    'pdfrw',
    'pexpect',
    'shellescape',
    'tinycss2',
    'webencodings',
    ]

setup(name='barnhunt',
      version=version,
      description="Helpers for drawing Barn Hunt course maps",
      long_description=README + "\n\n" + CHANGES,
      platforms=['Any'],
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'Intended Audience :: End Users/Desktop',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Python :: 3',
          'Topic :: Multimedia :: Graphics :: Conversion',
          'Topic :: Printing',
          'Topic :: Utilities',
          ],
      keywords='barn hunt inkscape course maps',
      author='Jeff Dairiki',
      author_email='dairiki@dairiki.org',
      url='https://gitlab.com/dairiki/barnhunt',
      license='BSD',

      packages=find_packages(exclude=('tests', 'tests.*')),
      zip_safe=True,

      install_requires=install_requires,
      entry_points={
          'console_scripts': [
              'barnhunt = barnhunt:main',
              ],
          },
      )
