# pull official base image
FROM python:3.6

# set work directory
WORKDIR ../../../build

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1


# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# copy project
COPY . .
#RUN echo $(pwd)
#RUN echo $(ls -la)
RUN python setup.py install

COPY ./tacc_stats.ini .
#RUN cd tacc_stats/site && python manage.py migrate

