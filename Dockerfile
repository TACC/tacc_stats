# pull official base image
FROM python:3.6.15

RUN useradd -ms /bin/bash hpcperfstats
WORKDIR /home/hpcperfstats

# run as root
RUN apt-get update && apt-get upgrade -y
RUN apt-get install netcat supervisor -y


ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PATH $PATH:/home/hpcperfstats/.local/bin

# install dependencies
RUN pip install --upgrade pip
COPY --chown=hpcperfstats:hpcperfstats ./requirements.txt .
RUN pip install -r requirements.txt


# copy project
COPY --chown=hpcperfstats:hpcperfstats . .
# This includes the tacc_stats.ini
#COPY --chown=hpcperfstats:hpcperfstats ./tacc_stats.ini .


RUN pip install .

ADD services-conf/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

