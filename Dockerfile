FROM python:3.11.6-slim-bookworm as base

# Setup env
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER 1
ENV PATH=/home/root/.local/bin:$PATH
ENV FT_APP_ENV="docker"

# Prepare environment
RUN mkdir /sonagent \
  && apt-get update \
  && apt-get -y install sudo libatlas3-base curl sqlite3 libhdf5-serial-dev libgomp1 \
  && apt-get -y install build-essential libssl-dev git libffi-dev libgfortran5 pkg-config cmake gcc \
  && apt-get clean \
  && pip install --upgrade pip wheel

COPY  . /sonagent/


WORKDIR /sonagent

# Install dependencies
COPY  requirements.txt  /sonagent/requirements.txt
# USER root
RUN  pip install --user --no-cache-dir numpy \
  && pip install --user --no-cache-dir -r requirements.txt

RUN pip install -e . --user --no-cache-dir --no-build-isolation \
  && mkdir /sonagent/user_data/

RUN python setup.py install
ENTRYPOINT ["sonagent"]
# Default to trade mode
CMD [ "run" ]