#! /bin/bash

OUTFILE=$1
shift
TEMPFILE=/tmp/tempfile.$$
echo $* | xargs -n 1 echo > ${TEMPFILE}
INFILES=`cat ${TEMPFILE} | xargs -n 1 echo -i`
COUNT=`wc -l ${TEMPFILE} | cut -d ' ' -f 1`

ffmpeg ${INFILES} -filter_complex "[0:v] [0:a] concat=n=${COUNT}:v=1:a=1 [v] [a]" -vn -map "[v]" -map "[a]" ${OUTFILE}

rm ${TEMPFILE}
