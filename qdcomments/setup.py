from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="qdcomments",
    version="0.1.0",
    author="Albert Margolis",
    author_email="almargolis@gmail.com",
    description="Reusable Flask commenting system with moderation and content filtering",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/almargolis/quickdev",
    project_urls={
        "Bug Tracker": "https://github.com/almargolis/quickdev/issues",
        "Documentation": "https://github.com/almargolis/quickdev/blob/master/qdcomments/README.md",
        "Source Code": "https://github.com/almargolis/quickdev/tree/master/qdcomments",
    },
    license="MIT",
    packages=['qdcomments'],
    include_package_data=True,
    package_data={
        'qdcomments': [
            'templates/qdcomments/*.html',
            'static/qdcomments/*',
            'data/*.yaml',
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: Flask",
    ],
    python_requires=">=3.7",
    install_requires=[
        "Flask>=2.0.0",
        "Flask-SQLAlchemy>=2.5.0",
        "Flask-Login>=0.5.0",
        "PyYAML>=6.0",
        "Markdown>=3.3.0",
        "Werkzeug>=2.0.0",
    ],
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-flask>=1.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'qdcomments-migrate-users=qdcomments.cli:migrate_user_table',
            'qdcomments-init-blocked-words=qdcomments.cli:init_blocked_words_file',
            'qdcomments-pending=qdcomments.cli:list_pending_comments',
            'qdcomments-approve=qdcomments.cli:approve_comment_cli',
            'qdcomments-reject=qdcomments.cli:reject_comment_cli',
        ],
    },
)
