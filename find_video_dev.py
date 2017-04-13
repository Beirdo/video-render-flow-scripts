#! /usr/bin/env python3
# vim:ts=4:sw=4:ai:et:si:sts=4

import logging
import os
import sys
from subprocess import check_output, STDOUT, CalledProcessError
import re

description = sys.argv[1].strip()
if len(sys.argv) > 2:
    index = int(sys.argv[2])
else:
    index = 0

command = ["v4l2-ctl", "--list-devices"]

try:
    output = check_output(command, shell=False, stderr=STDOUT).decode("utf-8")
except CalledProcessError as e:
    message = "Command: %s returned %s" % (e.cmd, e.returncode)
    if e.output:
        message += "\n\nOutput: %s" % e.output.decode("utf-8")
    logger.error(message)
    raise Exception(message)

"""
USB2.0 Camera (usb-0000:00:1a.7-3):
	/dev/video0

HD Pro Webcam C920 (usb-0000:00:1d.7-2):
	/dev/video1
"""

regexp = re.compile(r"%s\s*\(.*?\):\s*\n\s*(/dev/video.*?)\s*\n" % description,
                    re.M)
matches = regexp.findall(output)
if index in range(len(matches)):
    print(matches[index])
    sys.exit(0)

raise NameError("%s [%s] not found" % (description, index))
