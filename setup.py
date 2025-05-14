from setuptools import setup, find_packages

setup(
    name='analytics_dashboard',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'flask',
        'flask-sqlalchemy',
        'flask-migrate',
        'flask-cors',
        'psycopg2-binary',
        'celery',
        'redis',
        'python-dotenv'
    ],
) 