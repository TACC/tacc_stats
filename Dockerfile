FROM centos:centos7

MAINTAINER Ajit Gauli <agauli@tacc.utexas.edu>

RUN curl -O http://dl.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-7-2.noarch.rpm
RUN rpm -Uvh epel-release-7*.rpm

RUN curl -O http://dl.iuscommunity.org/pub/ius/stable/CentOS/7/x86_64/ius-release-1.0-13.ius.centos7.noarch.rpm
RUN rpm -Uvh ius-release*.rpm

RUN yum -y update
RUN yum groupinstall -y "development tools"
RUN yum install -y python python-devel python-setuptools nginx supervisor nfs-utils nfs-utils-lib

RUN easy_install pip

# setup project code
ADD . /project
WORKDIR /project

# web server conf
RUN echo "daemon off;" >> /etc/nginx/nginx.conf
RUN ln -s /home/docker/code/conf/nginx-app.conf /etc/nginx/conf.d/
RUN ln -s /home/docker/code/conf/supervisor-app.ini /etc/supervisord.d/

#this is where stats data is mounted
RUN mkdir /hpc

#RUN mount -t nfs 129.114.52.21:/corral-repl/tacc/hpc /hpc
#RUN echo 129.114.52.21:/corral-repl/tacc/hpc /hpc nfs rw,nosuid,rsize=1048576,wsize=1048576,intr,nfsvers=3,tcp,addr=129.114.52.21 0 0 >> /etc/fstab

# install pip dependencies
RUN yum -y install $(cat yum.txt)

# install pip dependencies
RUN pip install -r requirements.txt

# install non-pip dependencies
RUN python setup.py install

# setup static assets
RUN mkdir -p /var/www/static #&& cd tacc_stats/site && python manage.py collectstatic -link --noinput
RUN mkdir -p /var/www/media
# database migrations, if necessary
#RUN cd tacc_stats/site && python manage.py migrate

expose 80
cmd ["supervisord", "-n"]
