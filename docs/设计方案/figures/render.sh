#!/bin/zsh
# usage: ./render.sh name height
CH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
D=$(cd "$(dirname "$0")" && pwd)
"$CH" --headless=new --use-angle=swiftshader --enable-unsafe-swiftshader --no-sandbox --hide-scrollbars --force-device-scale-factor=2 --window-size=1600,$2 --user-data-dir=/tmp/chprof2 --screenshot="/tmp/$1.png" "file://$D/src/$1.html" >/dev/null 2>&1
cp "/tmp/$1.png" "$D/$1.png" && echo "ok $1"
