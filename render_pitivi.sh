#!/bin/bash -x

XGES_FILE=$1
OUT_FILE=$2
DEBUG=0

export GST_PLUGIN_PATH=/usr/local/lib/gstreamer-1.0:/usr/lib/gstreamer-1.0

ges-launch-1.0 --gst-debug-level ${DEBUG} -l ${XGES_FILE} -o ${OUT_FILE} -f "video/quicktime,variant=iso:video/x-raw,width=1920,height=1080->video/x-h264+youtube9m:audio/mpeg,mpegversion=4,rate=48000"
