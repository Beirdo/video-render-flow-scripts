#!/bin/bash -x

for i in "$@"; do
    FULLFILE=$(realpath $i)
    BASEFILE=$(basename $i)
    BASEFILE=${BASEFILE%%.*}
    INPUTDIR=$(dirname ${FULLFILE})
    BASEDIR=$(realpath ${INPUTDIR}/../..)
    SOURCE=$(basename ${INPUTDIR})
    EDITDIR=${BASEDIR}/edit/${SOURCE}
    PROXYDIR=${BASEDIR}/proxy/${SOURCE}
    mkdir -p ${EDITDIR} ${PROXYDIR}

    PROXYHEIGHT=$(codec.py --height --file ${FULLFILE})
    PROXYWIDTH=$(codec.py --width --file ${FULLFILE})

    time \
    gst-launch-1.0 -t filesrc location=${FULLFILE} ! decodebin name=dec \
        dec. ! queue ! videoconvert ! videorate ! video/x-raw,framerate=30/1 ! \
               tee name=vid \
        dec. ! queue ! audioconvert ! audio/x-raw,format=S16LE,channels=2 ! \
               audioresample ! audio/x-raw,rate=48000 ! audiorate ! \
               tee name=aud \
        vid. ! queue ! \
             x264enc pass=quant quantizer=17 speed-preset=ultrafast name=vidA \
        vid. ! queue ! videoscale ! \
             video/x-raw,height=${PROXYHEIGHT},width=${PROXYWIDTH} ! \
             x264enc pass=quant quantizer=19 speed-preset=ultrafast name=vidB \
        vidA. ! queue ! matroskamux name=muxA ! \
                filesink location=${EDITDIR}/${BASEFILE}.mkv \
        vidB. ! queue ! matroskamux name=muxB ! \
                filesink location=${PROXYDIR}/${BASEFILE}.mkv \
        aud. ! queue ! muxA. \
        aud. ! queue ! muxB.
done

