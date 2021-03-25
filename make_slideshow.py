#! /usr/bin/env python3
# vim:ts=4:sw=4:ai:et:si:sts=4

import logging
import sys
import os
from tempfile import NamedTemporaryFile
from argparse import ArgumentParser, REMAINDER
from subprocess import Popen, PIPE, STDOUT

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
tmpdir = os.path.realpath(os.path.join(projectdir, "tmp"))
os.makedirs(inputdir, 0o755, exist_ok=True)
os.makedirs(tmpdir, 0o755, exist_ok=True)

with NamedTemporaryFile("w+", dir=inputdir, suffix=".txt", delete=False) as tf:
    for file_ in args.files:
        tf.write("file '%s'\n" % file_)
        tf.write("duration %d\n" % args.duration)
    tf.write("file '%s'\n" % args.files[-1])
    tfName = tf.name

with NamedTemporaryFile(dir=tmpdir, suffix=".mp4") as mf:
    command = ["/usr/bin/ffmpeg", "-y", "-f", "concat", "-i", tfName,
               "-vsync", "vfr", "-pix_fmt", "yuv420p", mf.name]
    retCode = execCommand(command)
    os.unlink(tfName)

    if retCode != 0:
        sys.exit(retCode)


    command = ["ffmpeg", "-y", "-f", "lavfi", "-i", 
               "anullsrc=channel_layout=stereo:sample_rate=48000",
               "-i", mf.name, "-c:v", "copy", "-c:a", "aac", "-shortest",
               os.path.join(inputdir, args.outfile)]
    retCode = execCommand(command)
    if retCode != 0:
        sys.exit(retCode)

