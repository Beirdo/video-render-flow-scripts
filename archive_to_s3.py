#! /usr/bin/env python3
# vim:ts=4:sw=4:ai:et:si:sts=4
# See http://s3-accelerate-speedtest.s3-accelerate.amazonaws.com/en/accelerate-speed-comparsion.html?region=us-west-2&origBucketName=beirdo-videos

import logging
import argparse
import os
import sys
import json
import boto3
from botocore.client import Config
import shutil
import threading
import time

def getUploadFiles(fileHash, rootdir, videodir):
    for (root, dirs, files) in os.walk(rootdir):
        for file_ in files:
            filename = os.path.join(root, file_)
            keyname = filename.split(videodir + "/", 1)[1]
            fileHash[filename] = keyname

def numToReadable(value):
    prefixes = ["", "k", "M", "G", "T", "P"]
    index = 0
    for (index, prefix) in enumerate(prefixes):
        if value <= 700.0:
            break
        value /= 1024.0
    return "%.2f%s" % (value, prefixes[index])

class ProgressPercentage(object):
    def __init__(self, filename):
        self.startTime = time.time()
        self._filename = filename
        self.basename = os.path.basename(filename)
        self._size = float(os.path.getsize(filename))
        self.printSize = numToReadable(self._size)
        self._seen_so_far = 0.0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        # To simplify we'll assume this is hooked up
        # to a single filename.
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            seen = numToReadable(self._seen_so_far)
            speed = self._seen_so_far / (time.time() - self.startTime) * 8.0
            speed = numToReadable(speed)
            sys.stdout.write("\r%s  %sB / %sB  (%.2f%%)  %sb/s    " %
                (self.basename, seen, self.printSize, percentage, speed))
            sys.stdout.flush()

FORMAT = "%(asctime)s: %(name)s:%(lineno)d (%(threadName)s) - %(levelname)s - %(message)s"
logging.basicConfig(format=FORMAT)
logging.getLogger(None).setLevel(logging.INFO)
logging.captureWarnings(True)
logger = logging.getLogger(__name__)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('boto3').setLevel(logging.CRITICAL)

parser = argparse.ArgumentParser(description="Archive project to S3")
parser.add_argument("--project", '-p', action="store", required=True,
                    help="Project to upload")
parser.add_argument("--skip", '-s', action="store_true", 
                    help="Skip uploading")
parser.add_argument("--inputs", '-i', action="store_true", 
                    help="Archive inputs too")
parser.add_argument("--delete", '-D', action="store_true", 
                    help="Delete project locally after upload")
parser.add_argument("--accelerate", '-a', action="store_true", 
                    help="Use S3 Transfer Acceleration")
args = parser.parse_args()

basedir = os.path.realpath(os.path.dirname(sys.argv[0]))
credsfile = os.path.join(basedir, "aws-config.json")

videodir = "/opt/video/render/video"
projectdir = os.path.join(videodir, args.project)

if not args.skip:
    with open(credsfile, "r") as f:
        config = json.load(f)

    botoconfig = {
        "s3": {
            "use_accelerate_endpoint": args.accelerate
        }
    }
    s3 = boto3.client("s3", config['region'],
                      aws_access_key_id=config['accessKey'],
                      aws_secret_access_key=config['secretKey'],
                      config=Config(**botoconfig))

    uploadFiles = {}
    sourcedir = os.path.join(projectdir, "output")
    getUploadFiles(uploadFiles, sourcedir, videodir)

    if args.inputs:
        sourcedir = os.path.join(projectdir, "input")
        getUploadFiles(uploadFiles, sourcedir, videodir)

    bucket = config['bucket']
    for (filename, keyname) in uploadFiles.items():
        logger.info("Uploading %s to %s:%s" % (filename, bucket, keyname))
        s3.upload_file(filename, bucket, keyname,
                       Callback=ProgressPercentage(filename))
        sys.stdout.write("\n")
        sys.stdout.flush()

if args.delete:
    logger.info("Deleting %s" % projectdir)
    shutil.rmtree(projectdir)
