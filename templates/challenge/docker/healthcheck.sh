#!/bin/sh
# Health check for CTF challenge container
# Returns 0 if healthy, non-zero if unhealthy

curl -f -s -o /dev/null http://localhost:80/ || exit 1
exit 0
