FROM ubuntu:14.04
MAINTAINER Varun Mittal <varun91@uw.edu>
MAINTAINER Somebody <somebody@acme.com>
ENV DEBIAN_FRONTEND noninteractive
ENV HOME /root
RUN apt-get update
RUN apt-get install -y --force-yes --no-install-recommends software-properties-common
#GUIdock.json
#cynetwork_bma.json
#cytoscape_3_3.json
#openjre8.json
RUN add-apt-repository -y 'ppa:openjdk-r/ppa'
RUN apt-get -y update 
RUN apt-get install -y --force-yes --no-install-recommends openjdk-8-jre
#--
add http://chianti.ucsd.edu/cytoscape-3.3.0/cytoscape-3.3.0.tar.gz /deps/cytoscape-3.3.0.tar.gz
#--
add lib/cytoscape_3_3/cytoscape_setup.sh /81e383d2-b8d0-46c8-ac8b-2783eaacc07e
add lib/cynetwork_bma/CyNetworkBMA-1.0.0_1.jar /deps/CytoscapeConfiguration/3/apps/installed/CyNetworkBMA-1.0.0_1.jar
#--
#r.json
RUN apt-get install -y --force-yes --no-install-recommends apt-transport-https
RUN add-apt-repository -y 'deb https://cran.rstudio.com/bin/linux/ubuntu/ trusty/'
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys E084DAB9 
RUN apt-get -y update 
RUN apt-get install -y --force-yes --no-install-recommends r-base-dev
add lib/r/deps.R /tmp/deps.R
RUN Rscript /tmp/deps.R 
RUN rm /tmp/deps.R 
RUN apt-get install -y --force-yes --no-install-recommends r-base
RUN apt-get purge -y --force-yes apt-transport-https r-base-dev
#--
#novnc.json
#broker_base.json
RUN apt-get install -y --force-yes --no-install-recommends python-django python-pip build-essential python-dev
RUN pip install librabbitmq mongoengine 
RUN apt-get purge -y --force-yes python-pip build-essential python-dev
copy lib/broker_base/broker.tar.gz /
#--
add lib/broker_base/init.sh /7e1a6bb2-cd08-4db1-9c9b-1483059ddbf6
RUN apt-get install -y --force-yes --no-install-recommends supervisor openssh-server pwgen sudo vim-tiny
RUN apt-get install -y --force-yes --no-install-recommends net-tools lxde x11vnc x11vnc-data xvfb
RUN apt-get install -y --force-yes --no-install-recommends gtk2-engines-murrine ttf-ubuntu-font-family
RUN apt-get install -y --force-yes --no-install-recommends nginx
RUN apt-get install -y --force-yes --no-install-recommends python-pip python-dev build-essential
RUN apt-get install -y --force-yes --no-install-recommends mesa-utils libgl1-mesa-dri
add lib/novnc/web /web/
RUN pip install -r /web/requirements.txt 
RUN apt-get purge -y --force-yes python-pip python-dev build-essential
add lib/novnc/noVNC /noVNC/
add lib/novnc/nginx.conf /etc/nginx/sites-enabled/default
add lib/novnc/startup.sh /
add lib/novnc/supervisord.conf /etc/supervisor/conf.d/
add lib/novnc/doro-lxde-wallpapers /usr/share/doro-lxde-wallpapers/
#--
copy lib/GUIdock/DEMO.tar.gz /
#--
add lib/GUIdock/init.sh /1730aa02-d1bb-48ad-9129-9895c9b1ef3c
RUN apt-get purge software-properties-common -y --force-yes
RUN apt-get -y autoclean
RUN apt-get -y autoremove
RUN rm -rf /var/lib/apt/lists/*
RUN rm -rf /tmp/*
RUN rm -rf /var/tmp/*
EXPOSE 6080
RUN bash -c 'echo -e "#!/bin/bash\nchmod +x /81e383d2-b8d0-46c8-ac8b-2783eaacc07e\n/81e383d2-b8d0-46c8-ac8b-2783eaacc07e\nrm -rf /81e383d2-b8d0-46c8-ac8b-2783eaacc07e\nchmod +x /7e1a6bb2-cd08-4db1-9c9b-1483059ddbf6\n/7e1a6bb2-cd08-4db1-9c9b-1483059ddbf6\nchmod +x /1730aa02-d1bb-48ad-9129-9895c9b1ef3c\n/1730aa02-d1bb-48ad-9129-9895c9b1ef3c\nrm -rf /1730aa02-d1bb-48ad-9129-9895c9b1ef3c\n/startup.sh" >> /entrypoint.sh'
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
