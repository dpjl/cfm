from setuptools import setup

setup(name='camerafile',
      version='0.1',
      description = 'Camera File Manager',
      url='https://github.com/vivi-18133/vivi-cfm',
      author='dpjl',
      author_email='dpjl@gmail.com',
      license='MIT',
      packages=['camerafile'],
	package_data={'camerafile':  ["bin/exiftool-11.94.exe", 'conf/logging.json']},
      data_files=[('bin', ['bin/exiftool-11.94.exe']),('conf', ['conf/logging.json'])],
	entry_points={'console_scripts': ['cfm=camerafile.cfm:main']},
      zip_safe=False)