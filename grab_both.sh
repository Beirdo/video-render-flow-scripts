#!/bin/bash -x

HEADSET=
BUILTIN=
if [ "$1" == "--headset" ]; then
    HEADSET="1"
    shift 1
elif [ "$1" == "--builtin" ]; then
    BUILTIN="1"
    shift 1
fi

PREVIEW="yes"
if [ "$1" == "--nopreview" ]; then
    PREVIEW=""
fi

SCOPEVIDDEVICE=$(find_video_dev.py "USB2.0 Camera")
if [ $? -ne 0 ]; then
    exit 1
fi

CAMVIDDEVICE=$(find_video_dev.py "HD Pro Webcam C920")
if [ $? -ne 0 ]; then
    exit 1
fi


# This microphone in the microscope doesn't seem to do squat
#AUDDEVICE="alsa_input.usb-Etron_Technology__Inc._USB2.0_Camera-02.analog-mono"
# Use the laptop's builtin mic

AUDDEVICE="alsa_input.usb-046d_HD_Pro_Webcam_C920_4BB47EAF-02.analog-stereo"
if [ -n "$HEADSET" ]; then
    AUDDEVICE="alsa_input.usb-Logitech_Inc_Logitech_USB_Headset_H540_00000000-00.analog-stereo"
fi
if [ -n "$BUILTIN" ]; then
    AUDDEVICE="alsa_input.pci-0000_00_1b.0.analog-stereo"
fi

OUTDIR=/opt/video/render/rawinput
DATESTAMP=$(date +%F-%T | tr ':' '-')
SCOPEFILENAME=microscope-${DATESTAMP}.mkv
CAMFILENAME=webcam-${DATESTAMP}.mkv
PREVIEWFILENAME=preview-${DATESTAMP}.mkv

SCOPEVIEWWIDTH=${1:-448}
SCOPEVIEWHEIGHT=${2:-336}
SCOPETOP=-$(( 480 - ${SCOPEVIEWHEIGHT} ))
SCOPELEFT=-$(( 800 - ${SCOPEVIEWWIDTH} ))

CAMVIEWWIDTH=${3:-352}
CAMVIEWHEIGHT=${4:-288}
CAMBOTTOM=-$(( 480 - ${CAMVIEWHEIGHT} ))
CAMRIGHT=-$(( 800 - ${CAMVIEWWIDTH} ))

VIEWRATE=${5:-15/1}

if [ "$PREVIEW" = "yes" ]; then
    PREVIEW="vid1. ! queue ! videorate ! video/x-raw,framerate=$VIEWRATE ! "
    PREVIEW+="  videoscale ! "
    PREVIEW+="  video/x-raw,width=$SCOPEVIEWWIDTH,height=$SCOPEVIEWHEIGHT ! "
    PREVIEW+="  videobox border-alpha=0 top=${SCOPETOP} left=${SCOPELEFT} ! "
    PREVIEW+="  videoconvert ! queue name=xv1 "
    PREVIEW+="vid2. ! queue ! avdec_h264 ! "
    PREVIEW+="  videoscale ! videorate ! videoconvert ! "
    PREVIEW+="  video/x-raw,format=YUY2,framerate=$VIEWRATE,width=$CAMVIEWWIDTH,height=$CAMVIEWHEIGHT ! "
    PREVIEW+="  videoconvert ! queue name=xv2 "
    PREVIEW+="xv1. ! videomixer name=mix ! "
    PREVIEW+="  videoconvert ! queue name=out "
    PREVIEW+="xv2. ! mix. "
    PREVIEW+="out. ! tee name=out2 "
    PREVIEW+="out2. ! queue leaky=1 ! xvimagesink sync=false "
    PREVIEW+="out2. ! queue ! "
    PREVIEW+="  x264enc bitrate=2000 speed-preset=ultrafast ! queue name=videoq3 "
    PREVIEW+="videoq3. ! matroskamux name=mux3 ! "
    PREVIEW+="  filesink location=${OUTDIR}/${PREVIEWFILENAME} "
    PREVIEW+="audiotee. ! identity sync=true ! " \
    PREVIEW+="  queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 ! mux3. "
fi

gst-launch-1.0 -ve \
    v4l2src device="$SCOPEVIDDEVICE" typefind=true ! \
        video/x-raw,format=YUY2,framerate=30/1,width=640,height=480 ! \
        tee name=vid1 \
    pulsesrc device="$AUDDEVICE" ! \
        audio/x-raw,format=S16LE,rate=48000,channels=2 ! \
        tee name=audiotee \
    vid1. ! queue ! videoconvert ! identity sync=true ! \
        x264enc bitrate=3000 speed-preset=ultrafast ! queue name=videoq1 \
    videoq1. ! matroskamux name=mux1 ! filesink location=${OUTDIR}/${SCOPEFILENAME} \
    audiotee. ! identity sync=true ! \
        queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 ! mux1. \
    v4l2src device="$CAMVIDDEVICE" ! \
        video/x-h264 ! h264parse ! \
        tee name=vid2 \
    vid2. ! queue ! \
        video/x-h264,width=1920,height=1080,framerate=30/1,stream-format=avc ! \
        identity sync=true ! queue name=videoq2 \
    videoq2. ! mux2. \
    audiotee. ! identity sync=true ! \
        queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 ! mux2. \
    matroskamux streamable=true name=mux2 ! \
        filesink location=${OUTDIR}/${CAMFILENAME} \
    ${PREVIEW}

