#! /usr/bin/env python3
# vim:ts=4:sw=4:ai:et:si:sts=4

import argparse
import logging
import json
from flask_jsonrpc.proxy import ServiceProxy
import os
import sys
import re
import time

FORMAT = "%(asctime)s: %(name)s:%(lineno)d (%(threadName)s) - %(levelname)s - %(message)s"
logging.basicConfig(format=FORMAT)
logging.getLogger(None).setLevel(logging.INFO)
logging.captureWarnings(True)
logger = logging.getLogger(__name__)

progname = os.path.basename(sys.argv[0])
if progname == "rpcclient.py" or progname == "common" or len(progname) < 7:
    logger.error("This must be run via a symlink")
    sys.exit(1)

# Strip the video_ off the beginning
progname = progname[6:]

nonProjectMethods = ["poll", "list_outstanding"]
parameters = {
    "common": {
        "arguments": [
            {
                "args": ["--debug", "-d"],
                "kwargs": {
                    "action": "store_true",
                    "help": "Use debug mode",
                }
            },
            {
                "args": ["--verbose", "-v"],
                "kwargs": {
                    "action": "store_true",
                    "help": "Use verbose mode",
                }
            },
            {
                "args": ["--project", "-p"],
                "kwargs": {
                    "action": "store",
                    "required": progname not in nonProjectMethods,
                    "help": "Video project to upload",
                }
            },
            {
                "args": ["--serverIP", "-i"],
                "kwargs": {
                    "action": "store",
                    "required": True,
                    "help": "Specify the server's IP",
                }
            },
            {
                "args": ["--remoteIP", "-I"],
                "kwargs": {
                    "action": "store",
                    "default": "",
                    "help": "Override the client IP",
                }
            },
            {
                "args": ['--nopoll'],
                "kwargs": {
                    "action": "store_false",
                    "dest": "poll",
                    "help": "Disable the poll for completion",
                }
            },
        ],
    },
    "upload_inputs": {
        "description": "Upload input video files to server for processing",
        "params": ["project", "remoteIP", "force"],
        "arguments": [
            {
                "args": ["--force", "-f"],
                "kwargs": {
                    "action": "store_true",
                    "help": "Force deletion of old files on target",
                }
            }
        ]
    },
    "convert_inputs": {
        "description": "Convert videos to editable and proxy versions",
        "params": ["project", "files", "factor"],
        "arguments" : [
            {
                "args": ["--file", "-f"],
                "kwargs": {
                    "action": "append",
                    "dest": "files",
                    "help": "Choose specific files to run (one per --file)",
                }
            },
            {
                "args": ["--factor", "-F"],
                "kwargs": {
                    "action": "store",
                    "type": float,
                    "default": 0.5,
                    "help": "Set the shrink factor for proxy files (default %(default)s)",
                }
            }
        ]
    },
    "download_editables": {
        "description": "Download editable video files from server for editing",
        "params": ["project", "remoteIP", "force"],
        "arguments": [
            {
                "include": "upload_inputs"
            }
        ]
    },
    "download_proxies": {
        "description": "Download proxy video files from server for editing",
        "params": ["project", "remoteIP", "force"],
        "arguments": [
            {
                "include": "upload_inputs"
            }
        ]
    },
    "upload_edl": {
        "description": "Upload the EDL to the server",
        "params": ["project", "remoteIP", "edlfile"],
        "arguments": [
            {
                "args": ["--edlfile", '-e'],
                "kwargs": {
                    "required": True,
                    "action": "store",
                    "help": "The EDL File to send",
                }
            }
        ]
    },
    "upload_proxy_edl": {
        "description": "Upload the proxy EDL to the server",
        "params": ["project", "remoteIP", "edlfile"],
        "arguments": [
            {
                "include": "upload_edl"
            }
        ]
    },
    "render_edl": {
        "description": "Render the EDL file on the server",
        "params": ["project", "outfile", "edlfile", "proxy", "mode"],
        "arguments": [
            {
                "include": "upload_edl"
            },
            {
                "args": ["--outfile", '-o'],
                "kwargs": {
                    "action": "store",
                    "required": True,
                    "help": "Set the output filename",
                }
            },
            {
                "args": ["--proxy", '-P'],
                "kwargs": {
                    "action": "store_true",
                    "help": "Render using proxy files",
                }
            },
            {
                "args": ["--mode", '-m'],
                "kwargs": {
                    "action": "store",
                    "choices": ["cinelerra", "pitivi"],
                    "default": "pitivi",
                    "help": "Editing mode (default %(default)s)",
                },
            },
        ]
    },
    "upload_to_youtube": {
        "description": "Upload the output video to YouTube",
        "params": ["project", "outfile", "title", "description", "category",
                   "keywords"],
        "arguments": [
            {
                "args": ["--outfile", '-o'],
                "kwargs": {
                    "action": "store",
                    "required": True,
                    "help": "Set the output filename",
                }
            },
            {
                "args": ["--title", "-t"],
                "kwargs": {
                    "action": "store",
                    "required": True,
                    "help": "Title for the video",
                }
            },
            {
                "args": ["--description", "-D"],
                "kwargs": {
                    "action": "store",
                    "required": True,
                    "help": "Description for the video",
                }
            },
            {
                "args": ["--category", "-c"],
                "kwargs": {
                    "action": "store",
                    "default": 28,
                    "type": int,
                    "help": "Category for the video (default %(default)s)",
                }
            },
            {
                "args": ["--keywords", "-k"],
                "kwargs": {
                    "action": "store",
                    "required": True,
                    "help": "Keywords for the video (comma separated)",
                }
            },
        ]
    },
    "archive_to_s3": {
        "description": "Archive a project to S3",
        "params": ["project", "skip", "inputs", "delete", "accelerate"],
        "arguments": [
            {
                "args": ["--skip", '-s'],
                "kwargs": {
                    "action": "store_true", 
                    "help": "Skip uploading",
                }
            },
            {
                "args": ["--inputs"],
                "kwargs": {
                    "action": "store_true", 
                    "help": "Archive inputs too",
                }
            },
            {
                "args": ["--delete", '-D'],
                "kwargs": {
                    "action": "store_true", 
                    "help": "Delete project locally after upload",
                }
            },
            {
                "args": ["--accelerate", '-a'],
                "kwargs": {
                    "action": "store_true", 
                    "help": "Use S3 Transfer Acceleration",
                }
            },
        ],
    },
    "poll": {
        "description": "Poll for completion of a task",
        "params": ["id"],
        "arguments": [
            {
                "args": ["--id", '-u'],
                "kwargs": {
                    "action": "store",
                    "required": True,
                    "help": "Set the id to poll for",
                }
            }
        ]
    },
    "list_outstanding": {
        "description": "List outstanding tasks",
        "params": [],
        "arguments": [
        ]
    }
}

def add_parser_args(parser, progname):
    arguments = parameters.get(progname, {}).get("arguments", [])
    for arg in arguments:
        if "include" in arg:
            add_parser_args(parser, arg['include'])
            continue
        args = arg.get('args', [])
        kwargs = arg.get('kwargs', {})
        parser.add_argument(*args, **kwargs)

def print_response(response):
    global verbose
    if not verbose:
        result = response.get('result', None)
        if result is not None:
            if isinstance(result, dict):
                result = result.get('result', "")
                if result:
                    print(result)
                return 0

    print(json.dumps(response, indent=2))

    if "errors" in response:
        return 1
    return 0

if progname not in parameters:
    logger.error("RPC service %s is not defined" % progname)
    sys.exit(1)

parser = argparse.ArgumentParser(prog=progname,
            description=parameters[progname].get("description", None))
add_parser_args(parser, 'common')
add_parser_args(parser, progname)
args = parser.parse_args()

logger.info("Args: %s" % args)

if progname in nonProjectMethods:
    args.poll = False

if args.debug:
    logging.getLogger(None).setLevel(logging.DEBUG)

if hasattr(args, "files") and not args.files:
    args.files = []

verbose = args.verbose

apiurl = "http://%s:5005/api" % args.serverIP
logger.info("Using service at %s" % apiurl)
proxy = ServiceProxy(apiurl)
apifunc = getattr(proxy.App, progname)

params = parameters[progname].get('params', [])
apiparams = {param: getattr(args, param) for param in params}

if progname != "poll":
    response = apifunc(**apiparams)

    retCode = print_response(response)

    if not args.poll:
        sys.exit(retCode)

    uuid = response['id']
else:
    uuid = args.id

sleepTime = 0
while True:
    logger.info("Sleeping for %ss" % sleepTime)
    time.sleep(sleepTime)
    sleepTime = max(min(sleepTime * 2, 300), 10)

    response = proxy.App.poll(id=uuid)
    retCode = print_response(response)
    if retCode:
        output = None
        break

    output = response.get("result", {})
    if output.get("status", "complete") == "complete":
        break

sys.exit(retCode)
