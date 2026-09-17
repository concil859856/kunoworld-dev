#!/usr/bin/env bash
# Runs on a rented GPU host before any MiniMax H3 weights are downloaded. Checks the host really is in the expected,
# licence-allowed country, three ways:
#   1. two IP geolocation databases agree on the country;
#   2. the host is close to a data centre in that country (TCP connect < NEAR_MS to the nearest of the listed regions);
#   3. every data centre in the licence's Excluded Territories is clearly farther than the near one: at least twice
#      the near time and at least FAR_MIN_MS. A host inside the US, EU, UK or Korea would be closest to that
#      territory's data centre. (A flat floor is wrong for neighbours: Tokyo to Seoul is about 30 ms.)
#
#   region-check.sh <expected ISO country> <AWS region[,region...] in that country>
#   region-check.sh JP ap-northeast-1,ap-northeast-3      Tokyo or Osaka, whichever is nearer
# Shadeform's `tokyo-japan-5` offer is displayed as "JP, Kagawa", which is nearer Osaka than Tokyo.
# Exit 0 = PASS; 1 = FAIL (details printed). The last line starts with PASS or FAIL.
# First used on 2026-09-15 (Tokyo 8x H200); Seoul is the close excluded neighbour to watch.
set -uo pipefail
EXPECTED="${1:?expected country code}"
NEAR_LIST="${2:?AWS region(s) in that country, comma-separated}"
NEAR_MS="${NEAR_MS:-20}"
FAR_MIN_MS="${FAR_MIN_MS:-20}"
# US east and west, EU (Ireland, Frankfurt, Paris, Stockholm), UK (London), Korea (Seoul).
FAR=(us-east-1 us-west-2 eu-west-1 eu-central-1 eu-west-3 eu-north-1 eu-west-2 ap-northeast-2)

connect_ms() { # the best of three TCP connects to the region's EC2 API endpoint, DNS excluded
  local best=99999 i t
  for i in 1 2 3; do
    t=$(curl -s -o /dev/null --max-time 5 -w '%{time_namelookup} %{time_connect}' "https://ec2.$1.amazonaws.com/" |
      awk '{ printf "%d", ($2 - $1) * 1000 }')
    [ -n "$t" ] && [ "$t" -gt 0 ] && [ "$t" -lt "$best" ] && best=$t
  done
  echo "$best"
}

ip=$(curl -s --max-time 10 https://api.ipify.org)
c1=$(curl -s --max-time 10 "https://ipinfo.io/$ip/country" | tr -d '[:space:]')
c2=$(curl -s --max-time 10 "http://ip-api.com/line/$ip?fields=countryCode" | tr -d '[:space:]')
fail=0
echo "public IP $ip; ipinfo country $c1; ip-api country $c2; expected $EXPECTED"
[ "$c1" = "$EXPECTED" ] && [ "$c2" = "$EXPECTED" ] || { echo "FAIL geolocation databases don't both say $EXPECTED"; fail=1; }
near=99999
for r in ${NEAR_LIST//,/ }; do
  ms=$(connect_ms "$r")
  echo "near  $r: ${ms} ms"
  [ "$ms" -lt "$near" ] && near=$ms
done
echo "nearest in $EXPECTED: ${near} ms (must be < $NEAR_MS)"
[ "$near" -lt "$NEAR_MS" ] || { echo "FAIL not close to any of $NEAR_LIST"; fail=1; }
far_floor=$((near * 2 > FAR_MIN_MS ? near * 2 : FAR_MIN_MS))
for r in "${FAR[@]}"; do
  ms=$(connect_ms "$r")
  echo "far   $r: ${ms} ms (must be >= $far_floor)"
  [ "$ms" -ge "$far_floor" ] || { echo "FAIL too close to $r, an Excluded Territory"; fail=1; }
done
if [ "$fail" = 0 ]; then echo "PASS host is in $EXPECTED and not in an Excluded Territory"; else echo "FAIL do not download or run H3 here"; fi
exit "$fail"
