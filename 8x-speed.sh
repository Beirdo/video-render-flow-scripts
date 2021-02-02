#! /bin/bash

INFILE=$1
OUTFILE=${INFILE/.mkv/_8x.mkv}

ffmpeg -i ${INFILE} -filter_complex "[0:v]setpts=0.125*PTS[v];[0:a]atempo=2.0[a1];[a1]atempo=2.0[a2];[a2]atempo=2.0[a]" -vn -map "[v]" -map "[a]" ${OUTFILE}

