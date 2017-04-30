#!/bin/bash -x

BASEFILE=$1
INDEX=$2
OUTPUT=$3

time \
gst-launch-1.0 -t multifilesrc location=${BASEFILE} index=${INDEX} \
	caps="image/png,framerate=1/2,pixel-aspect-ratio=1/1" ! \
	pngdec ! videoconvert ! videorate ! theoraenc ! oggmux ! \
	filesink location=${OUTPUT}
