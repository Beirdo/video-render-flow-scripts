#! /bin/bash

OUTFILE=$1
shift
TEMPFILE=/tmp/tempfile.$$
echo $* | xargs -n 1 echo > ${TEMPFILE}
INFILES=`cat ${TEMPFILE} | xargs -n 1 echo -i`
COUNT=`wc -l ${TEMPFILE} | cut -d ' ' -f 1`

ffmpeg ${INFILES} -filter_complex "[0:v] [0:a] concat=n=${COUNT}:v=1:a=1 [v] [a] ; [v]setpts=0.05*PTS[vout];[a]atempo=2.0[a1];[a1]atempo=2.0[a2];[a2]atempo=2.0[a3];[a3]atempo=2.0[a4];[a4]atempo=1.25[aout]" -vn -map "[vout]" -map "[aout]" ${OUTFILE}

rm ${TEMPFILE}
