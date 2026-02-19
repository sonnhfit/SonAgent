#!/usr/bin/env python3

from pathlib import Path

from setuptools import find_packages, setup

from sonagent.version import __version__

this_directory = Path(__file__).parent
long_description = """
### Autonomous Agent for Digital Consciousness Backup Using Large Language Models (LLM) 

### Overview
The Digital Consciousness Backup Agent is an autonomous system designed to safeguard your digital consciousness on the internet using Large Language Models (LLMs). As we navigate the vast landscape of the digital realm, preserving and securing our digital consciousness becomes paramount. This project employs advanced techniques to ensure the protection and backup of your digital self. Powerful code generation capability, self-editing source code
> What shapes individuals is their own beliefs. by Son Nguyen Huu

### Features
- **Autonomous Operation:** The agent operates autonomously, continuously monitoring and safeguarding your digital presence without requiring constant user intervention.

- **Belief-Based Thinking with Large Language Models (LLMs):** The agent engages in cognitive processes inspired by belief systems, utilizing advanced LLMs for reasoning and decision-making. This allows it to navigate the digital landscape with a level of understanding akin to human cognition.

- **Automatic Belief Acquisition:** The agent is designed to automatically acquire new beliefs and knowledge over time. It leverages the power of large language models to adapt and stay informed about the ever-evolving digital environment.

- **Learning with Human Feedback:** The agent incorporates human feedback into its learning process, enhancing its capabilities through continuous interaction with users. This dynamic learning mechanism ensures that the agent evolves and improves its performance based on real-world user experiences.

- **Secure Backup:** The agent employs robust encryption and secure protocols to create backups of your digital consciousness, preventing unauthorized access and ensuring the integrity of your data.
- **Self-Repairing source code**  edits its own source code and compiles itself under human approval

- **Many tools and skills:** Train neural network, Search, write file, ...

"""


required = [
    'chromadb==1.5.0',
    'numpy==2.4.2',
    'SQLAlchemy==2.0.46',
    'python-telegram-bot==22.6',
    'arrow==1.3.0',
    'fastapi==0.129.0',
    'pydantic==2.12.5',
    'typing-extensions>=4.12.0',
    'annotated-types>=0.6.0',
    'typing-inspection>=0.4.2',
    'uvicorn>=0.31.1',
    'pyjwt[crypto]>=2.10.1',
    'aiofiles==23.2.1',
    'psutil==5.9.7',
    'python-rapidjson==1.14',
    'orjson==3.11.7',
    'sdnotify==0.3.2',
    'PyGithub==2.8.1',
    'schedule==1.2.1',
    'croniter==2.0.3',
    'tabulate==0.9.0',
    'python-multipart==0.0.9',
    'agno==2.5.2',
    'groq==1.0.0',
    'openai==2.21.0',
    # Research Team dependencies
    'arxiv==2.4.0',
    'pypdf==6.7.1',
    'wikipedia==1.4.0',
    'beautifulsoup4==4.14.3',
    'youtube_transcript_api==1.2.4',
    'yfinance==1.2.0',
    'firecrawl==4.16.0',
    'ddgs==9.10.0'
]

# print(f"Required: {required}")
# package configuration - for reference see:
# https://setuptools.readthedocs.io/en/latest/setuptools.html#id9
setup(
    name="sonagent",
    description=(
        "Autonomous Agent for Digital Consciousness Backup "
        "Using Large Language Models (LLM)."
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    version=__version__,
    author="Son Nguyen Huu",
    author_email="sonnhfit@gmail.com",
    url="https://github.com/sonnhfit/sonagent",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9.0",
    install_requires=required,
    license="MIT",
    zip_safe=False,
    entry_points={
        "console_scripts": [
            "sonagent = sonagent.main:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="agent ai ml language-model autonomus-robots large-language-models llm chatgpt llama2",
)
