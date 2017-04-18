#!/bin/bash -x

BASEDIR=$(cd $(dirname $0); pwd)
DEFAULTAUDIO="webcam"
source ${BASEDIR}/select_audio.sh

PREVIEW="yes"
if [ "$1" == "--nopreview" ]; then
    PREVIEW=""
fi

VIDDEVICE=$(find_video_dev.py "HD Pro Webcam C920")
if [ $? -ne 0 ]; then
    exit 1
fi

OUTDIR=/opt/video/render/rawinput
DATESTAMP=$(date +%F-%T | tr ':' '-')
FILENAME=webcam-${DATESTAMP}.mkv

VIEWWIDTH=${1:-800}
VIEWHEIGHT=${2:-448}
VIEWRATE=${3:-15/1}

if [ "$PREVIEW" = "yes" ]; then
    PREVIEW="vid. ! queue ! avdec_h264 ! "
    PREVIEW+="  videoscale ! videorate ! videoconvert ! "
    PREVIEW+="  video/x-raw,format=YUY2,framerate=$VIEWRATE,width=$VIEWWIDTH,height=$VIEWHEIGHT ! "
    PREVIEW+="  videoconvert ! queue leaky=1 ! xvimagesink sync=false"
fi

export GST_PLUGIN_PATH=/usr/local/lib/gstreamer-1.0

gst-launch-1.0 -ve \
    v4l2src device="$VIDDEVICE" ! \
        video/x-h264 ! h264parse ! \
        tee name=vid \
    vid. ! queue ! \
        video/x-h264,width=1920,height=1080,framerate=30/1,stream-format=avc ! \
        identity sync=true ! queue name=videoq \
    pulsesrc device="$AUDDEVICE" ! \
        audio/x-raw,format=S16LE,rate=48000,channels=2 ! queue ! \
        audioconvert ! identity sync=true ! \
        queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 name=audioq \
    videoq. ! mux. \
    audioq. ! mux. \
    matroskamux streamable=true name=mux ! \
        filesink location=${OUTDIR}/${FILENAME} \
    ${PREVIEW}
