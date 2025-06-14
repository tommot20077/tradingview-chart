from setuptools import setup, find_packages

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='person-chart',
    version='1.0.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=[
        'binance_futures_connector==4.1.0',
        'fastapi==0.115.12',
        'influxdb3_python==0.13.0',
        'numpy==2.3.0',
        'pandas==2.3.0',
        'python-dotenv==1.1.0',
        'uvicorn==0.34.3',
        'starlette==0.46.2',
        'SQLAlchemy==2.0.41',
    ],
    extras_require={
        'kafka': ['kafka-python==2.2.11'],
        'postgresql': ['psycopg2-binary'],
    },
    entry_points={
        'console_scripts': [
            'person-chart-enhanced=person_chart.enhanced_main:app',
            'person-chart-basic=person_chart.main:app',
            'person-chart-test-db=person_chart.tools.influx_connector:main',
            'person-chart-analyze=person_chart.analysis.data_analyzer:main',
        ],
    },
    author='Yuan ',
    author_email='tommot20077@gmail.com',
    description='一個即時加密貨幣價格串流服務器，集成 InfluxDB 存儲、數據分析和監控功能。',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/tommot20077/tradingview-chart',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Framework :: FastAPI',
        'Topic :: Office/Business :: Financial :: Investment',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    python_requires='>=3.9',
)
