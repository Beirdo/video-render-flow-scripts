#!/bin/bash -x

if [ "$1" == "--help" ]; then
    v4l2-ctl --list-devices
    exit 0
fi

VIDDEVICE=${1:-/dev/video1}
AUDDEVICE="alsa_card.usb-Etron_Technology__Inc._USB2.0_Camera-02.analog-mono"
OUTDIR=/opt/video/render/rawinputs
FILENAME=microscope-$(date +%F-%T).mkv

VIEWWIDTH=${2:-320}
VIEWHEIGHT=${3:-240}

gst-launch-1.0 -t \
    v4l2src device=$VIDDEVICE ! \
        video/x-raw,format=YUY2,framerate=30/1,width=640,height=480 ! \
        tee name=vid \
    pulsesrc device="$AUDDEVICE" ! \
	audio/x-raw,format=S16LE,rate=48000,channels=1 ! audioconvert ! \
        audio/x-raw,format=S16LE,rate=48000,channels=2 ! queue name=audioq \
    vid. ! videorate ! video/x-raw,framerate=5 ! \
        videoscale ! video/x-raw,width=$VIEWWIDTH,height=$VIEWHEIGHT ! \
        xvimagesink \
    vid. ! queue ! videoconvert ! \
        x264enc bitrate=3000 speed-preset=ultrafast ! queue name=videoq \
    videoq. ! matroskamux name=mux ! filesink location=${OUTDIR}/${FILENAME} \
    audioq. ! mux.

