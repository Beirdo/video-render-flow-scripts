#!/bin/bash -x

HEADSET=
if [ "$1" == "--headset" ]; then
    HEADSET="1"
    shift 1
fi

VIDDEVICE=$(find_video_dev.py "HD Pro Webcam C920")
if [ $? -ne 0 ]; then
    exit 1
fi

AUDDEVICE="alsa_input.usb-046d_HD_Pro_Webcam_C920_4BB47EAF-02.analog-stereo"
if [ -n "$HEADSET" ]; then
    AUDDEVICE="alsa_input.usb-Logitech_Inc_Logitech_USB_Headset_H540_00000000-00.analog-stereo"
fi
OUTDIR=/opt/video/render/rawinput
FILENAME=webcam-$(date +%F-%T).mkv

VIEWWIDTH=${1:-800}
VIEWHEIGHT=${2:-448}
VIEWRATE=${3:-15/1}

export GST_PLUGIN_PATH=/usr/local/lib/gstreamer-1.0

gst-launch-1.0 -ve \
    v4l2src device="$VIDDEVICE" ! \
        video/x-h264 ! h264parse ! \
        tee name=vid \
    vid. ! queue ! avdec_h264 ! \
        videoscale ! videorate ! videoconvert ! \
        video/x-raw,format=YUY2,framerate=$VIEWRATE,width=$VIEWWIDTH,height=$VIEWHEIGHT !\
        videoconvert ! queue name=xv leaky=1 \
    xv. ! xvimagesink sync=false \
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
