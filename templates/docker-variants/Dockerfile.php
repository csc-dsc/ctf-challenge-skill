# PHP Apache Dockerfile for CTF challenges
FROM php:8.2-apache

RUN sed -i 's|http://deb.debian.org|http://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources

RUN groupadd -r ctf && useradd -r -g ctf -u 10001 ctf

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy app
COPY --chown=ctf:ctf ./app /var/www/html/

# Ensure Apache binds to 0.0.0.0
RUN sed -i 's/Listen 80/Listen 0.0.0.0:80/' /etc/apache2/ports.conf

# start.sh: write flag then start apache
COPY start.sh /start.sh
RUN chmod +x /start.sh

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

EXPOSE 80
USER ctf
CMD ["/start.sh"]
