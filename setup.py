from setuptools import setup, find_packages

setup(
    name='petro_station_frappe',
    version='0.0.1',
    description='Petro Station App for Frappe',
    author='GORM SOLUTIONS',
    author_email='mututapaul02@gmail.com',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=('frappe',),
)
