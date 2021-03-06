#!/bin/bash -x

BASEDIR=$(cd $(dirname $0); pwd)
DEFAULTAUDIO="builtin"
source ${BASEDIR}/select_audio.sh

VIDDEVICE=$(find_video_dev.py "USB2.0 Camera")
if [ $? -ne 0 ]; then
    exit 1
fi

PREVIEW="yes"
if [ "$1" == "--nopreview" ]; then
    PREVIEW=""
fi

OUTDIR=/opt/video/render/rawinput
DATESTAMP=$(date +%F-%T | tr ':' '-')
FILENAME=microscope-${DATESTAMP}.mkv

VIEWWIDTH=${1:-640}
VIEWHEIGHT=${2:-480}
VIEWRATE=${3:-15/1}

if [ "$PREVIEW" = "yes" ]; then
    PREVIEW="vid. ! queue ! videorate ! video/x-raw,framerate=$VIEWRATE ! "
    PREVIEW+="  videoscale ! video/x-raw,width=$VIEWWIDTH,height=$VIEWHEIGHT ! "
    PREVIEW+="  videoconvert ! queue leaky=1 ! xvimagesink sync=false"
fi

gst-launch-1.0 -ve \
    v4l2src device="$VIDDEVICE" typefind=true ! \
        video/x-raw,format=YUY2,framerate=30/1,width=640,height=480 ! \
        tee name=vid \
    pulsesrc device="$AUDDEVICE" ! \
        audio/x-raw,format=S16LE,rate=48000,channels=2 ! queue name=audioq \
    vid. ! queue ! videoconvert ! \
        x264enc bitrate=3000 speed-preset=ultrafast ! queue name=videoq \
    videoq. ! matroskamux name=mux ! filesink location=${OUTDIR}/${FILENAME} \
    audioq. ! mux. \
    ${PREVIEW}

