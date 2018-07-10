from setuptools import setup, find_packages

setup(name='django-softdelete-kourts',
      version='0.8.6',
      description='Soft delete support for Django ORM, with undelete and many more!',
      author='Kourts',
      author_email='support@kourts.com',
      maintainer='Kourts',
      maintainer_email='ricardo@kourts.com',
      license="BSD",
      url="https://github.com/ricardobanegas/django-softdelete",
      packages=find_packages(),
      install_requires=['setuptools',],
      include_package_data=True,
      setup_requires=['setuptools_hg',],
      classifiers=[
        'Framework :: Django',
        'License :: OSI Approved :: BSD License',
        'Environment :: Web Environment',
        ]
)
