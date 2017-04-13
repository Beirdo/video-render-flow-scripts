#!/bin/bash -x

VIDDEVICE=$(find_video_dev.py "USB2.0 Camera")
if [ $? -ne 0 ]; then
    exit 1
fi

# This microphone in the microscope doesn't seem to do squat
#AUDDEVICE="alsa_input.usb-Etron_Technology__Inc._USB2.0_Camera-02.analog-mono"
# Use the laptop's builtin mic
AUDDEVICE="alsa_input.pci-0000_00_1b.0.analog-stereo"
OUTDIR=/opt/video/render/rawinput
FILENAME=microscope-$(date +%F-%T).mkv

VIEWWIDTH=${1:-640}
VIEWHEIGHT=${2:-480}
VIEWRATE=${3:-15/1}

gst-launch-1.0 -ve \
    v4l2src device="$VIDDEVICE" typefind=true ! \
        video/x-raw,format=YUY2,framerate=30/1,width=640,height=480 ! \
        tee name=vid \
    pulsesrc device="$AUDDEVICE" ! \
        audio/x-raw,format=S16LE,rate=48000,channels=2 ! queue name=audioq \
    vid. ! queue ! videorate ! video/x-raw,framerate=$VIEWRATE ! \
        videoscale ! video/x-raw,width=$VIEWWIDTH,height=$VIEWHEIGHT ! \
        videoconvert ! xvimagesink \
    vid. ! queue ! videoconvert ! \
        x264enc bitrate=3000 speed-preset=ultrafast ! queue name=videoq \
    videoq. ! matroskamux name=mux ! filesink location=${OUTDIR}/${FILENAME} \
    audioq. ! mux.

