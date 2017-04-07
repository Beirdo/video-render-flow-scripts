#! /usr/bin/env python3
# vim:ts=4:sw=4:ai:et:si:sts=4

import argparse
import sys
import json

from pymediainfo import MediaInfo

parser = argparse.ArgumentParser(description="Extract codec info from a video")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("--video", '-v', action="store_const", const="video",
                   dest="action", help="Give video codec name")
group.add_argument("--audio", '-a', action="store_const", const="audio",
                   dest="action", help="Give audio codec name")
group.add_argument("--halfsize", '-H', action="store_const", const="halfsize",
                   dest="action",
                   help="Return resolution of half-size video (approx)")
group.add_argument("--framerate", '-F', action="store_const", const="framerate",
                   dest="action", help="Return video framerate")
group.add_argument("--dump", '-d', action="store_const", const="dump",
                   dest="action", help="Dump all codec information (in JSON)")
parser.add_argument("--file", '-f', action="store", required=True,
                    help="Video filename")
args = parser.parse_args()

action = args.action

media_info = MediaInfo.parse(args.file)

for track in media_info.tracks:
    if action == "dump":
        print(json.dumps(track.to_data(), indent=2))

    if action == "video":
        if track.track_type == 'Video':
            print(track.codec)
            sys.exit(0)

    if action == "audio":
        if track.track_type == 'Audio':
            print(track.codec)
            sys.exit(0)

    if action == "halfsize":
        if track.track_type == 'Video':
            width = int(track.width / 2)
            height = int(track.height / 2)
            print("%sx%s" % (width, height))
            sys.exit(0)

    if action == "framerate":
        if track.track_type == 'Video':
            if track.frame_rate:
                print(track.frame_rate)
            elif track.frame_rate_mode:
                print(track.frame_rate_mode)
            else:
                print("Unknown")
            sys.exit(0)

if action == "dump":
    sys.exit(0)

sys.exit(1)

