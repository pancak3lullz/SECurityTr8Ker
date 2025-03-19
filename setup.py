from setuptools import setup, find_packages

setup(
    name="securitytr8ker",
    version="1.0.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "requests>=2.31.0",
        "xmltodict>=0.13.0",
        "colorlog>=6.7.0",
        "beautifulsoup4>=4.12.2",
        "tweepy>=4.14.0",
        "pytz>=2023.3",
        "python-dotenv>=1.0.0",
        "asyncio>=3.4.3",
        "aiohttp>=3.8.5"
    ]
) 