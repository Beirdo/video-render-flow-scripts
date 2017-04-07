#! /usr/bin/env python3
# vim:ts=4:sw=4:ai:et:si:sts=4

import argparse
import sys
import os
import json

from pymediainfo import MediaInfo
from ffmpy import FFmpeg

parser = argparse.ArgumentParser(description="Convert video(s) to editable and proxy versions")
parser.add_argument("--session", '-s', action="store",
                    help="Name of editing session")
parser.add_argument("--source", '-S', action="store",
                    help="Name of video source")
parser.add_argument("--mjpeg", action="store_true",
                    help="Force a transcode to MJPEG during cleanup phase")
parser.add_argument("--mpeg4", action="store_true",
                    help="Force a remuxing to MPEG4 during cleanup phase")
parser.add_argument("--nodelete", action="store_false", dest="delete",
                    help="Don't delete intermediate files")
parser.add_argument("files", nargs=argparse.REMAINDER,
                    help="Video filenames")
args = parser.parse_args()

curdir = os.path.realpath(os.path.curdir)
parts = curdir.split('/')

if not args.session:
    args.session = parts[-3]

if not args.source:
    args.source = parts[-1]

parts[-2] = "edit"
editdir = "/".join(parts)

parts[-2] = "proxy"
proxydir = "/".join(parts)

os.makedirs(editdir, 0o755, exist_ok=True)
os.makedirs(proxydir, 0o755, exist_ok=True)

for file_ in args.files:
    cleanupfiles = []
    mediaInfo = MediaInfo.parse(file_)
    (basename, _) = os.path.splitext(os.path.basename(file_))
    infile = os.path.realpath(os.path.join(curdir, file_))

    for track in mediaInfo.tracks:
        if track.track_type == 'Video':
            videoCodec = track.codec
            videoWidth = track.width
            videoHeight = track.height
            videoFrameRate = track.frame_rate or 0
        elif track.track_type == 'Audio':
            audioCodec = track.codec
            audioSampleRate = track.sampling_rate

    # First pass is used to clean up video into a format we can convert to the
    # "raw" editable video sanely, if needed
    outext = None
    outcodecs = {"v": "copy", "a": "copy"}
    outargs = ""
    if args.mjpeg or videoFrameRate not in [30, 29.97]:
        outext = "mp4"
        outcodecs['v'] = "mjpeg"
        outargs = "-q:v 2 -r:v 30 -vsync vfr"
        videoCodec = "MJPEG"
    elif videoCodec in ["DV"]:
        # If this is raw DV, copy into an AVI first, MP4 can't handle DV
        # video
        outext = "avi"
    elif args.mpeg4:
        # Remux to MP4 first to fix videos from the Toshiba Camileo X100
        # which have invalid timestamps in the video apparently
        outext = 'mp4'

    if outext:
        outcodecs = ["-c:%s %s" % (k, v) for (k, v) in outcodecs.items()]
        intfile = os.path.join(editdir, "%s.%s" % (basename, outext))
        ffmpeg = FFmpeg(
            inputs={infile: "-hide_banner -y"},
            outputs={intfile: "%s %s" % (" ".join(outcodecs), outargs)}
        )
        ffmpeg.run()
        cleanupfiles.append(intfile)
    else:
        intfile = infile

    # During the second pass, we convert all audio to 48kHz PCM to overcome an 
    # apparent bug in cinelerra, and convert video to lossless H264 in MKV
    outext = "mkv"
    outcodecs = {"v": "copy", "a": "copy"}
    outargs = []
    if audioCodec not in ["PCM"] or audioSampleRate != 48000:
        # Transcode audio to PCM as cinelerra doesn't like cutting audio in
        # the middle of compressed frames and gives glitchy audio at cutpoints
        outcodecs['a'] = "pcm_s16le"
        outargs.append("-ar 48000")

    if videoCodec not in ["V_MPEG4/ISO/AVC", "H264"]:
        outcodecs['v'] = "libx264"
        outargs.append("-preset ultrafast -crf 17")

    editfile = os.path.join(editdir, "%s.%s" % (basename, outext))

    outcodecs = ["-c:%s %s" % (k, v) for (k, v) in outcodecs.items()]
    ffmpeg = FFmpeg(
        inputs={intfile: "-hide_banner -y"},
        outputs={editfile: "%s %s" % (" ".join(outcodecs), " ".join(outargs))}
    )
    ffmpeg.run()

    if args.delete:
        for file_ in cleanupfiles:
            os.unlink(file_)

    # Third pass creates proxy files (at half resolution, using H264 in MKV
    resolution = "%sx%s" % (int(videoWidth / 2.0), int(videoHeight / 2.0))
    outext = "mkv"
    outcodecs = {"v": "libx264", "a": "copy"}
    outargs = "-preset ultrafast -crf 19 -s:v %s" % resolution
    proxyfile = os.path.join(proxydir, "%s.%s" % (basename, outext))

    outcodecs = ["-c:%s %s" % (k, v) for (k, v) in outcodecs.items()]
    ffmpeg = FFmpeg(
        inputs={editfile: "-hide_banner -y"},
        outputs={proxyfile: "%s %s" % (" ".join(outcodecs), outargs)}
    )
    ffmpeg.run()
