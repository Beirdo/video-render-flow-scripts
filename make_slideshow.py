#! /usr/bin/env python3
# vim:ts=4:sw=4:ai:et:si:sts=4

import logging
import sys
import os
from tempfile import NamedTemporaryFile, TemporaryDirectory
from argparse import ArgumentParser, REMAINDER
from subprocess import Popen, PIPE, STDOUT
from pymediainfo import MediaInfo

FORMAT = "%(asctime)s: %(name)s:%(lineno)d (%(threadName)s) - %(levelname)s - %(message)s"
logging.basicConfig(format=FORMAT)
logging.getLogger(None).setLevel(logging.INFO)
logging.captureWarnings(True)
logger = logging.getLogger(__name__)


def execCommand(command):
    if not isinstance(command, list):
        command = command.split()

    logger.info("Running %s" % " ".join(command))
    retCode = -1
    #with Popen(command, shell=True, stdin=None, stdout=PIPE, stderr=STDOUT,
    #           bufsize=0) as p:
    with Popen(command, bufsize=0) as p:
        p.wait()
        retCode = p.returncode

    return retCode


parser = ArgumentParser()
parser.add_argument("--duration", "-d", default=5, type=int, help="Duration of each picture")
parser.add_argument("--outfile", "-o", required=True, help="Output filename")
parser.add_argument("--project", "-p", required=True, help="Project directory")
parser.add_argument("files", nargs=REMAINDER, help="Image files")
args = parser.parse_args()

videodir = "/opt/video/render/video"
projectdir = os.path.join(videodir, args.project)
inputdir = os.path.realpath(os.path.join(projectdir, "input"))

os.makedirs(inputdir, 0o755, exist_ok=True)

imagefiles = []
target_aspect = 1920 / 1080

with TemporaryDirectory(dir=projectdir) as tmpdir:
    for filename in args.files:
        infile = os.path.join(inputdir, filename)
        tmpfile = os.path.join(tmpdir, filename)
        (base, ext) = os.path.splitext(filename)
        basefile = "%s.png" % base
        outfile = os.path.join(tmpdir, basefile)

        if not os.path.exists(infile):
            continue

        with open(infile, "rb") as fi:
            with open(tmpfile, "wb") as fo:
                fo.write(fi.read())

        command = ["exifautotran", tmpfile]
        retCode = execCommand(command)
        if retCode != 0:
            continue

        media_info = MediaInfo.parse(tmpfile)
        for track in media_info.tracks:
            if track.track_type != 'Image':
                continue

            width = track.width
            height = track.height

            # Scale down to 1920x1080 max, keeping aspect ratio
            aspect = width / height

            scale = 1.0

            if aspect >= target_aspect:
                # too wide
                scale = 1920 / width
            elif aspect < target_aspect:
                # too high
                scale = 1080 / height

            # Never scale UP an image, only down
            if scale > 1.0:
                scale = 1.0

            scale_width = ((width * scale) // 2) * 2
            scale_height = ((height * scale) // 2) * 2

            pad_x = (1920 - scale_width) // 2
            pad_y = (1080 - scale_height) // 2

            command = ["convert", tmpfile, 
                       "-resize", "%dx%d!" % (scale_width, scale_height),
                       "-bordercolor", "black",
                       "-border", "%dx%d" % (pad_x, pad_y),
                       outfile]
            retCode = execCommand(command)
            if retCode != 0:
                continue

        imagefiles.append(basefile) 

    tfName = None
    with NamedTemporaryFile("w+", dir=tmpdir, suffix=".txt",
                            delete=False) as tf:
        for file_ in imagefiles:
            tf.write("file '%s'\n" % file_)
            tf.write("duration %d\n" % args.duration)
        tf.write("file '%s'\n" % args.files[-1])
        tfName = tf.name

    with NamedTemporaryFile(dir=tmpdir, suffix=".mp4") as mf:
        with NamedTemporaryFile(dir=tmpdir, suffix=".mp4") as mf2:
            command = ["ffmpeg", "-y", "-f", "concat", "-i", tfName,
                       "-vsync", "vfr", "-pix_fmt", "yuv420p", mf.name]
            retCode = execCommand(command)
            if retCode != 0:
                sys.exit(retCode)

            command = ["ffmpeg", "-y", "-i", mf.name, "-c:v", "h264", "-r", "30",
                       mf2.name]
            retCode = execCommand(command)
            if retCode != 0:
                sys.exit(retCode)

            command = ["ffmpeg", "-y", "-f", "lavfi", "-i", 
                       "anullsrc=channel_layout=stereo:sample_rate=48000",
                       "-i", mf2.name, "-c:v", "copy", "-c:a", "aac", "-shortest",
                       os.path.join(inputdir, args.outfile)]
            retCode = execCommand(command)
            if retCode != 0:
                sys.exit(retCode)
