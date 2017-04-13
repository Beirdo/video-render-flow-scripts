#!/bin/bash -x

HEADSET=
if [ "$1" == "--headset" ]; then
    HEADSET="1"
    shift 1
fi

BUILTIN=
if [ "$1" == "--builtin" ]; then
    BUILTIN="1"
    shift 1
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
SCOPEFILENAME=microscope-$(date +%F-%T).mkv
CAMFILENAME=webcam-$(date +%F-%T).mkv
PREVIEWFILENAME=preview-$(date +%F-%T).mkv

SCOPEVIEWWIDTH=${1:-448}
SCOPEVIEWHEIGHT=${2:-336}
SCOPETOP=-$(( 480 - ${SCOPEVIEWHEIGHT} ))
SCOPELEFT=-$(( 800 - ${SCOPEVIEWWIDTH} ))

CAMVIEWWIDTH=${3:-352}
CAMVIEWHEIGHT=${4:-288}
CAMBOTTOM=-$(( 480 - ${CAMVIEWHEIGHT} ))
CAMRIGHT=-$(( 800 - ${CAMVIEWWIDTH} ))

VIEWRATE=${5:-15/1}

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
    vid1. ! queue ! videorate ! video/x-raw,framerate=$VIEWRATE ! \
        videoscale ! video/x-raw,width=$SCOPEVIEWWIDTH,height=$SCOPEVIEWHEIGHT ! \
        videobox border-alpha=0 top=${SCOPETOP} left=${SCOPELEFT} ! \
        videoconvert ! queue name=xv1 \
    vid2. ! queue ! avdec_h264 ! \
        videoscale ! videorate ! videoconvert ! \
        video/x-raw,format=YUY2,framerate=$VIEWRATE,width=$CAMVIEWWIDTH,height=$CAMVIEWHEIGHT !\
        videoconvert ! queue name=xv2 \
    xv1. ! videomixer name=mix ! \
        videoconvert ! queue name=out \
    xv2. ! mix. \
    out. ! tee name=out2 \
    out2. ! queue leaky=1 ! xvimagesink sync=false \
    out2. ! queue ! \
        x264enc bitrate=2000 speed-preset=ultrafast ! queue name=videoq3 \
    videoq3. ! matroskamux name=mux3 ! \
	filesink location=${OUTDIR}/${PREVIEWFILENAME} \
    audiotee. ! identity sync=true ! \
        queue max-size-buffers=0 max-size-bytes=0 max-size-time=0 ! mux3. \

