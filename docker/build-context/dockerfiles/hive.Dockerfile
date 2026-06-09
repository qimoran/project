FROM eclipse-temurin:8-jre-jammy

ARG HADOOP_VERSION=3.3.6
ARG HIVE_VERSION=4.0.1
ARG MYSQL_CONNECTOR_VERSION=8.0.33
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash netcat-openbsd procps tini \
    && rm -rf /var/lib/apt/lists/*

COPY assets/hadoop-${HADOOP_VERSION}.tar.gz /tmp/hadoop.tar.gz
COPY assets/hive-${HIVE_VERSION}-bin.tar.gz /tmp/hive.tar.gz
COPY assets/mysql-connector-j-${MYSQL_CONNECTOR_VERSION}.jar /tmp/mysql-connector-j.jar

RUN tar -xzf /tmp/hadoop.tar.gz -C /opt \
    && ln -s /opt/hadoop-${HADOOP_VERSION} /opt/hadoop \
    && tar -xzf /tmp/hive.tar.gz -C /opt \
    && ln -s /opt/apache-hive-${HIVE_VERSION}-bin /opt/hive \
    && rm /tmp/hadoop.tar.gz /tmp/hive.tar.gz \
    && mv /tmp/mysql-connector-j.jar /opt/hive/lib/mysql-connector-j-${MYSQL_CONNECTOR_VERSION}.jar \
    && mkdir -p /opt/hive/logs /hadoop/tmp

ENV JAVA_HOME=/opt/java/openjdk
ENV HADOOP_HOME=/opt/hadoop
ENV HADOOP_CONF_DIR=/opt/hadoop/etc/hadoop
ENV HIVE_HOME=/opt/hive
ENV PATH="${HIVE_HOME}/bin:${HADOOP_HOME}/bin:${HADOOP_HOME}/sbin:${PATH}"

COPY config/hadoop/ /opt/hadoop/etc/hadoop/
COPY config/hive/hive-site.xml.template /opt/hive/conf/hive-site.xml.template
COPY entrypoints/hive-entrypoint.sh /usr/local/bin/hive-entrypoint

RUN chmod +x /usr/local/bin/hive-entrypoint

WORKDIR /opt/hive
ENTRYPOINT ["tini", "--", "hive-entrypoint"]
