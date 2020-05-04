from setuptools import setup

setup(name='vivicfm',
      version='0.1',
      description = 'Camera File Manager',
      url='https://github.com/vivi-18133/vivi-cfm',
      author='vivi-18133 (D.L.)',
      author_email='vivi.18133@gmail.com',
      license='MIT',
      packages=['vivicfm'],
	  package_data={'vivicfm':  ["bin/exiftool-11.94.exe", 'conf/logging.json']},
      data_files=[('bin', ['bin/exiftool-11.94.exe']),('conf', ['conf/logging.json'])],
	  entry_points={'console_scripts': ['cfm=vivicfm.cfm:main']},
      zip_safe=False)