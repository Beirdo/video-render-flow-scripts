#! /usr/bin/env python3
# vim:ts=4:sw=4:ai:et:si:sts=4

import argparse
import logging
import json
from flask_jsonrpc.proxy import ServiceProxy
import os
import sys

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

if progname not in parameters:
    logger.error("RPC service %s is not defined" % progname)
    sys.exit(1)

parser = argparse.ArgumentParser(prog=progname,
            description=parameters[progname].get("description", None))
add_parser_args(parser, 'common')
add_parser_args(parser, progname)
args = parser.parse_args()

print(args)

if args.debug:
    logging.getLogger(None).setLevel(logging.DEBUG)

if hasattr(args, "files") and not args.files:
    args.files = []

apiurl = "http://%s:5000/api" % args.serverIP
logger.info("Using service at %s" % apiurl)
proxy = ServiceProxy(apiurl)
apifunc = getattr(proxy.App, progname)

params = parameters[progname].get('params', [])
apiparams = {param: getattr(args, param) for param in params}
response = apifunc(**apiparams)

output = response.get("result", None)
if output:
    response['result'] = ""
    print(output)
print(json.dumps(response, indent=2))
