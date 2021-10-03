#!/bin/bash

INFILE=$1
BASEDIR=/opt/video/render/video/${VID_PROJECT}

ffmpeg -i ${BASEDIR}/input/${INFILE} -codec copy ${BASEDIR}/edit/${INFILE/\.?*/.mkv}
