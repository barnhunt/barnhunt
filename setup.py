from setuptools import setup, find_packages
import os

version = '0.1a1'

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()
CHANGES = open(os.path.join(here, 'CHANGES.rst')).read()

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
      #url='https://github.com/dairiki/barnhunt',
      license='BSD',

      packages=['barnhunt'],

      install_requires=[
          'click',
          'lxml',
          'pexpect',
          'shellescape',
          ],
      zip_safe=True,

      entry_points={
          'console_scripts': [
              'barnhunt = barnhunt:main',
              ],
          },

      #test_suite='xsendfile_middleware.test',
      )
