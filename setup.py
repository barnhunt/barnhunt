import os
from setuptools import setup
import sys

version = '0.1a4'

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()

install_requires = [
    'click',
    'jinja2',
    'lxml',
    'pexpect',
    'shellescape',
    'six',
    ]

tests_require = [
    'pytest',
    'pytest-catchlog',
    ]

setup_requires = []

needs_pytest = {'pytest', 'test', 'ptr'}.intersection(sys.argv)
if needs_pytest:
    setup_requires.append('pytest-runner')

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
          'Programming Language :: Python :: 2.7',
          'Topic :: Multimedia :: Graphics :: Conversion',
          'Topic :: Printing',
          'Topic :: Utilities',
          ],
      keywords='barn hunt inkscape course maps',
      author='Jeff Dairiki',
      author_email='dairiki@dairiki.org',
      # url='https://github.com/dairiki/barnhunt',
      license='BSD',

      packages=['barnhunt'],
      zip_safe=True,

      setup_requires=setup_requires,
      tests_require=tests_require,
      install_requires=install_requires,
      extras_require={
          'test': tests_require,
          },
      entry_points={
          'console_scripts': [
              'barnhunt = barnhunt:main',
              ],
          },
      )
