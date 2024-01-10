FROM python:3.11.6-slim-bookworm as base

# Setup env
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER 1
ENV PATH=/home/sonagent_user/.local/bin:$PATH
ENV FT_APP_ENV="docker"

# Prepare environment
RUN mkdir /sonagent \
  && apt-get update \
  && apt-get -y install sudo libatlas3-base curl sqlite3 libhdf5-serial-dev libgomp1 \
  && apt-get clean \
  && useradd -u 1000 -G sudo -U -m -s /bin/bash sonagent_user \
  && chown sonagent_user:sonagent_user /sonagent \
  # Allow sudoers
  && echo "sonagent_user ALL=(ALL) NOPASSWD: /bin/chown" >> /etc/sudoers

WORKDIR /sonagent

# Install dependencies
FROM base as python-deps
RUN  apt-get update \
  && apt-get -y install build-essential libssl-dev git libffi-dev libgfortran5 pkg-config cmake gcc \
  && apt-get clean \
  && pip install --upgrade pip wheel

# Install TA-lib
# COPY build_helpers/* /tmp/
# RUN cd /tmp && /tmp/install_ta-lib.sh && rm -r /tmp/*ta-lib*
# ENV LD_LIBRARY_PATH /usr/local/lib

# Install dependencies
COPY --chown=sonagent_user:sonagent_user requirements.txt  /sonagent/
USER sonagent_user
RUN  pip install --user --no-cache-dir numpy \
  && pip install --user --no-cache-dir -r requirements.txt

# Copy dependencies to runtime-image
FROM base as runtime-image
COPY --from=python-deps /usr/local/lib /usr/local/lib
ENV LD_LIBRARY_PATH /usr/local/lib

COPY --from=python-deps --chown=sonagent_user:sonagent_user /home/sonagent_user/.local /home/sonagent_user/.local

USER sonagent_user
# Install and execute
COPY --chown=sonagent_user:sonagent_user . /sonagent/

RUN pip install -e . --user --no-cache-dir --no-build-isolation \
  && mkdir /sonagent/user_data/

ENTRYPOINT ["sonagent"]
# Default to trade mode
CMD [ "run" ]