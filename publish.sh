#! /usr/bin/sh
rsync -vaC --delete --delete-excluded --include="*.png" --include="*.xul" --include="*.css" --include="*.js" --include="*.php" --exclude="*" ./ grumdrig.com:/www/grumdrig.com/www/u6map/