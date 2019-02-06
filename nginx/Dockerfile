FROM nginx:1.14-alpine

RUN cat /etc/nginx/conf.d/default.conf
RUN rm /etc/nginx/conf.d/*.conf

COPY *.conf /etc/nginx/conf.d
RUN ls /etc/nginx/conf.d
