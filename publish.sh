#! /bin/bash
rsync -vaC --delete --delete-excluded --include="*.png" --include="*.html" --include="*.js" --include="*.jpg" --include="*.gif" --include="parsemap.py" --exclude="*" ./ grumdrig.com:www/grumdrig.com/u6map/
