#!/bin/sh

PYPI_DEPS=" \
BeautifulSoup==3.2.0 \
Tempita \
configparser \
python_dateutil==1.5 \
lockfile \
ordereddict \
pyes \
templeton \
"

MOZAUTOLOG_REPO=http://hg.mozilla.org/users/jgriffin_mozilla.com/mozautolog/
MOZAUTOESLIB=http://hg.mozilla.org/automation/mozautoeslib/
ISTHISBUILDFASTER=http://hg.mozilla.org/users/jgriffin_mozilla.com/isthisbuildfaster/

virtualenv .
./bin/easy_install $PYPI_DEPS

# Clone/install custom Mozilla eggs
for I in $MOZAUTOLOG_REPO $MOZAUTOESLIB $ISTHISBUILDFASTER; do
    PKGNAME=$(basename $I)
    hg clone $I src/$PKGNAME
    ./bin/easy_install src/$PKGNAME
done

# Utility scripts to manage the queue
for I in add-job process-next-job show-pending-jobs clear-jobs; do
    SCRIPT=./bin/$I
    cat > $SCRIPT << EOF
#!/bin/sh

PYTHON=\$(dirname \$0)/python
SCRIPT_DIR=\$(dirname \$0)/../src/dashboard/server/itbf

\$PYTHON \$SCRIPT_DIR/$I.py
EOF
    chmod a+x $SCRIPT
done
