#! /usr/bin/env python3
# vim:ts=4:sw=4:ai:et:si:sts=4

import logging
import sys
import os
from tempfile import NamedTemporaryFile
from argparse import ArgumentParser, REMAINDER

FORMAT = "%(asctime)s: %(name)s:%(lineno)d (%(threadName)s) - %(levelname)s - %(message)s"
logging.basicConfig(format=FORMAT)
logging.getLogger(None).setLevel(logging.INFO)
logging.captureWarnings(True)
logger = logging.getLogger(__name__)

parser = ArgumentParser()
parser.add_argument("--duration", "-d", default=5, type=int, help="Duration of each picture")
parser.add_argument("--outfile", "-o", required=True, help="Output filename")
parser.add_argument("--project", "-p", required=True, help="Project directory")
parser.add_argument("files", nargs=REMAINDER, help="Image files")
args = parser.parse_args()

videodir = "/opt/video/render/video"
projectdir = os.path.join(videodir, args.project)
inputdir = os.path.realpath(os.path.join(projectdir, "input"))
outputdir = os.path.realpath(os.path.join(projectdir, "output"))
os.makedirs(inputdir, 0o755, exist_ok=True)
os.makedirs(outputdir, 0o755, exist_ok=True)

with NamedTemporaryFile() as tf:
    for file_ in args.files:
        tf.write("file '%s'\n" % os.path.join(inputdir, file_))
        tf.write("duration %d\n" % args.duration)
    tf.write("file '%s'\n" % os.path.join(inputdir, args.files[-1]))

    tf.flush()
    tf.seek(0)

    with NamedTemporaryFile(suffix=".mp4") as mf:
        command = "ffmpeg -f concat -i %s -vsync vfr -pix_fmt yuv420p %s" % \
                  (tf.name, mf.name)
        print(command)
        system(command)

        command = "ffmpeg -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=48000 -i %s -c:v copy -c:a aac -shortest %s" % (mf.name, os.path.join(outputdir, args.outfile))
        print(command)
        system(command)


