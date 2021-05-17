#!/bin/bash -x

FACTOR=0.5
if [ "$1" == "--factor" ]; then
    FACTOR=${2:-0.5}
    shift 2
fi

for i in "$@"; do
    FULLFILE=$(realpath $i)
    BASEFILE=$(basename $i)
    BASEFILE=${BASEFILE%%.*}
    INPUTDIR=$(dirname ${FULLFILE})
    BASEDIR=$(realpath ${INPUTDIR}/..)
    SOURCE=$(basename ${INPUTDIR})
    EDITDIR=${BASEDIR}/edit
    PROXYDIR=${BASEDIR}/proxy
    mkdir -p ${EDITDIR} ${PROXYDIR}

    PROXYHEIGHT=$(codec.py --height --factor ${FACTOR} --file ${FULLFILE})
    PROXYWIDTH=$(codec.py --width --factor ${FACTOR} --file ${FULLFILE})
    HASVIDEO=$(codec.py --video --file ${FULLFILE})
    HASAUDIO=$(codec.py --audio --file ${FULLFILE})

    if [ -z "${HASVIDEO}" ]; then
	continue
    fi

    if [ -z "${HASAUDIO}" ]; then
	# No audio
        time \
        gst-launch-1.0 -t filesrc location=${FULLFILE} ! decodebin name=dec \
            dec. ! queue ! videoconvert ! videorate ! \
	           video/x-raw,framerate=30/1 ! \
                   tee name=vid \
            vid. ! queue ! \
                 x264enc bitrate=10000 speed-preset=ultrafast name=vidA \
            vid. ! queue ! videoscale ! \
                 video/x-raw,height=${PROXYHEIGHT},width=${PROXYWIDTH} ! \
                 x264enc bitrate=2000 speed-preset=ultrafast name=vidB \
            vidA. ! queue ! matroskamux name=muxA ! \
                    filesink location=${EDITDIR}/${BASEFILE}.mkv \
            vidB. ! queue ! matroskamux name=muxB ! \
                    filesink location=${PROXYDIR}/${BASEFILE}.mkv 
    else
	# Has audio
        time \
        gst-launch-1.0 -t filesrc location=${FULLFILE} ! decodebin name=dec \
            dec. ! queue ! videoconvert ! videorate ! \
	           video/x-raw,framerate=30/1 ! \
                   tee name=vid \
            dec. ! queue ! audioconvert ! \
	           audio/x-raw,format=S16LE,channels=2 ! \
                   audioresample ! audio/x-raw,rate=48000 ! audiorate ! \
                   tee name=aud \
            vid. ! queue ! \
                 x264enc bitrate=10000 speed-preset=ultrafast name=vidA \
            vid. ! queue ! videoscale ! \
                 video/x-raw,height=${PROXYHEIGHT},width=${PROXYWIDTH} ! \
                 x264enc bitrate=2000 speed-preset=ultrafast name=vidB \
            vidA. ! queue ! matroskamux name=muxA ! \
                    filesink location=${EDITDIR}/${BASEFILE}.mkv \
            vidB. ! queue ! matroskamux name=muxB ! \
                    filesink location=${PROXYDIR}/${BASEFILE}.mkv \
            aud. ! queue ! muxA. \
            aud. ! queue ! muxB.
    fi
done

if [ -n "${BASEDIR}" ]; then
    echo ${FACTOR} > ${BASEDIR}/proxy/factor.txt
fi

