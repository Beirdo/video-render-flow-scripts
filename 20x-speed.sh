#! /bin/bash

INFILE=$1
OUTFILE=$2

ffmpeg -i ${INFILE} -filter_complex "[0:v]setpts=0.05*PTS[v];[0:a]atempo=2.0[a1];[a1]atempo=2.0[a2];[a2]atempo=2.0[a3];[a3]atempo=2.0[a4];[a4]atempo=1.25[a]" -vn -map "[v]" -map "[a]" ${OUTFILE}

