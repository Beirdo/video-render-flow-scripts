#!/bin/bash -x

WHAT="startx=800 starty=0 endx=2080 endy=800"
CROP="videocrop left=800 ! "

if [ "$1" = "--xid" ]; then
    WHAT="xid=$2"
    CROP=""
    shift 2
fi

if [ "$1" == "--right" ]; then
    WHAT="startx=0 starty=0 endx=1280 endy=800"
    CROP="videocrop right=800 ! "
    shift 1
fi

# Use the headset
AUDDEVICE="alsa_input.usb-Logitech_Inc_Logitech_USB_Headset_H540_00000000-00.analog-stereo"
OUTDIR=/opt/video/render/rawinput
FILENAME=screencapture-$(date +%F-%T).mkv

VIEWWIDTH=${1:-768}
VIEWHEIGHT=${2:-480}
VIEWRATE=${3:-15/1}

gst-launch-1.0 -ve \
    ximagesrc $WHAT use-damage=false do-timestamp=true ! \
        video/x-raw,framerate=15/1 ! $CROP \
        tee name=vid \
    pulsesrc device="$AUDDEVICE" ! \
        audio/x-raw,format=S16LE,rate=48000,channels=2 ! identity sync=true ! \
        queue name=audioq \
    vid. ! queue ! videorate ! video/x-raw,framerate=$VIEWRATE ! \
        videoscale ! video/x-raw,width=$VIEWWIDTH,height=$VIEWHEIGHT ! \
        videoconvert ! queue leaky=1 ! xvimagesink sync=false \
    vid. ! queue ! identity sync=true ! videoconvert ! \
        x264enc bitrate=6000 speed-preset=ultrafast ! queue name=videoq \
    videoq. ! matroskamux name=mux ! filesink location=${OUTDIR}/${FILENAME} \
    audioq. ! mux.

