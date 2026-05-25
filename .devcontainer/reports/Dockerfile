FROM miktex/miktex:basic

USER root

RUN apt-get update && apt-get install -y curl

RUN curl -fsSL https://miktex.org/download/key | gpg --dearmor -o /usr/share/keyrings/miktex.gpg

RUN echo "deb [signed-by=/usr/share/keyrings/miktex.gpg] https://miktex.org/download/ubuntu jammy universe" > /etc/apt/sources.list.d/miktex.list

RUN apt-get update && apt-get install -y git locales

RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8
