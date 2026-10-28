FROM python:3.13-alpine@sha256:8bcfa47b04b853a17aaf909362b847b2112fd6ec4105ea553ef9a43bafbb5916 AS build
WORKDIR /src
COPY thinkpad_archive/ thinkpad_archive/
COPY data/ data/
COPY locales/ locales/
COPY assets/ assets/
COPY tests/ tests/
COPY tools/ tools/
COPY deploy/ deploy/
COPY Dockerfile .dockerignore VERSION ./
RUN python -m unittest discover -s tests -v \
    && python -m thinkpad_archive build --output /public \
    && python tools/check_site.py /public

FROM caddy:2-alpine@sha256:eb4d35b7452d1ab6171fbdbe8d9275b2301dad6dad92115d91e19fb9b24d510f
COPY --from=build /public /srv
COPY deploy/Caddyfile /etc/caddy/Caddyfile
# The unprivileged HTTP listener needs no file capabilities.
RUN setcap -r /usr/bin/caddy
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
