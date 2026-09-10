#!/bin/bash
# verify-login.sh — ground truth: does the LIVE server accept a password typed HERE?
# Reads the credentials hidden, prints only a fingerprint (lengths + first/last char)
# and the HTTP status code. Nothing secret is ever printed or stored.
#
# Run ON THE SERVER:  bash /root/verify-login.sh   (or wherever you uploaded it)

set -u
DOMAIN=nata-yisi.cn

read -rsp "display name : " NAME; echo
read -rsp "password     : " PW; echo
echo "  fingerprint: name_len=${#NAME} pw_len=${#PW} first='${PW:0:1}' last='${PW: -1}'"

code=$(curl -s -o /tmp/vl.json -w '%{http_code}' \
  -X POST "https://${DOMAIN}/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"display_name\":\"${NAME}\",\"event_password\":\"${PW}\"}")
echo "  HTTP ${code}  $(head -c 160 /tmp/vl.json)"

case "$code" in
  200) echo "  => the server accepts exactly this string, so the browser must be"
       echo "     sending something different (autofill, IME, stray whitespace)." ;;
  401) echo "  => the server rejects this string: the stored hash is NOT this password."
       echo "     Re-run fix-login.sh and type slowly at its prompts." ;;
  429) echo "  => this IP is locked out by the failure throttle. Clear it with:"
       echo "     cd /opt/wedding-app && docker compose -f infra/docker-compose.prod.yml \\"
       echo "       exec -T redis sh -c 'redis-cli --scan --pattern \"wmp:login:fail:*\" | xargs -r redis-cli del'" ;;
  400|422) echo "  => the JSON body was malformed: the password contains a double quote"
           echo "     or a backslash, which this quick test cannot embed." ;;
  *)   echo "  => unexpected status; see the body above." ;;
esac
rm -f /tmp/vl.json
