#! /usr/bin/env python3
# vim:ts=4:sw=4:ai:et:si:sts=4

import logging
from flask import Flask, request
from flask_jsonrpc import JSONRPC
from flask_jsonrpc.helpers import extract_raw_data_request
import os
import sys
import shutil
import json
from subprocess import check_output, STDOUT, CalledProcessError
from bs4 import BeautifulSoup
from threading import Thread
from queue import Queue

FORMAT = "%(asctime)s: %(name)s:%(lineno)d (%(threadName)s) - %(levelname)s - %(message)s"
logging.basicConfig(format=FORMAT)
logging.getLogger(None).setLevel(logging.INFO)
logging.captureWarnings(True)
logger = logging.getLogger(__name__)

requestQ = Queue()
handlerThread = None
handlers = {}

def execCommand(command):
    if not isinstance(command, list):
        command = command.split()
    try:
        logger.info("Running %s" % " ".join(command))
        return check_output(command, shell=False, stderr=STDOUT).decode("utf-8")
    except CalledProcessError as e:
        message = "Command: %s returned %s" % (e.cmd, e.returncode)
        if e.output:
            message += "\n\nOutput: %s" % e.output.decode("utf-8")
        logger.error(message)
        raise Exception(message)

def get_remote_ip(remoteIP=None):
    if not remoteIP or remoteIP == '""':
        remoteIP=request.remote_addr
    if remoteIP == "localhost":
        remoteIP = "127.0.0.1"
    return remoteIP


class HandlerThread(Thread):
    def __init__(self, queue):
        Thread.__init__(self)

        self.queue = queue
        self.name = "handler_thread"

    def run(self):
        global handlers

        while True:
            item = self.queue.get()

            if not item:
                continue

            id_ = item.get('id', None)
            method = item.get('method', None)
            args = item.get('args', [])
            if not id_ or not method:
                continue

            if id_ not in handlers:
                handlers[id_] = {}
            handlers[id_]['status'] = 'in-progress'
            logger.info("Starting handler for method %s (id %s)" %
                        (method, id_))
            try:
                if not hasattr(self, method):
                    raise Exception("No thread handler exists for method %s" %
                                    method)
                methodFunc = getattr(self, method)
                data['result'] = methodFunc(**args)
            except Exception as e:
                data['error'] = str(e)

            data['status'] = "complete"
            logger.info("Finishing handler for method %s (id %s)" %
                        (method, id_))

    def upload_inputs(self, project, remoteIP=None, force=False):
        path = os.path.join("/opt/video/render/video", project, "input", "")
        command = ["rsync", "-avt", "%s:%s" % (remoteIP, path), path]
        if force:
            command.insert(2, "--delete")
        return execCommand(command)

    def convert_inputs(self, project, files=None, factor=0.5):
        path = os.path.join("/opt/video/render/video", project, "input", "")
        if not factor:
            factor = 0.5

        if not files:
            files = []
            for (root, dirs, files_) in os.walk(path):
                files.extend([os.path.join(root, file_) for file_ in files_])
        else:
            files = [os.path.join(path, file_) for file_ in files]

        # Dedupe and check existing files
        files = [file_ for file_ in set(files) if os.path.exists(file_)]

        if not files:
            return "No files in project %s" % project


        output = ""
        for file_ in files:
            command = ["convert_gstream.sh", "--factor", str(factor), file_]
            output += "\n\n"
            output += execCommand(command)

        return output

    def download_proxies(self, project, remoteIP=None, force=False):
        path = os.path.join("/opt/video/render/video", project, "proxy", "")
        command = ["rsync", "-avt", path, "%s:%s" % (remoteIP, path)]
        if force:
            command.insert(2, "--delete")
        return execCommand(command)

    def upload_proxy_edl(self, project, edlfile="edl.xml", remoteIP=None):
        path = os.path.join("/opt/video/render/video", project, "proxy",
                            edlfile)
        command = ["rsync", "-avt", "%s:%s" % (remoteIP, path), path]
        return execCommand(command)

    def render_edl(self, project, edlfile="edl.xml", outfile="output.mp4"):
        path = os.path.join("/opt/video/render/video", project, "proxy",
                            "factor.txt")
        if not os.path.exists(path):
            factor = 0.5
        else:
            with open(path, "r") as f:
                data = f.read()
            factor = float(data.strip())

        proxypath = os.path.join("/opt/video/render/video", project, "proxy")
        editpath = os.path.join("/opt/video/render/video", project, "edit")
        outputpath = os.path.join("/opt/video/render/video", project, "output")
        os.makedirs(outputpath, 0o755, exist_ok=True)

        inedlfile = os.path.join(proxypath, edlfile)
        edlfile = os.path.join(editpath, edlfile)
        batchfile = os.path.join(editpath, "batchlist.xml")
        outputfile = os.path.join(outputpath, outfile)

        output = ""

        # Copy the EDL file from proxy -> edit
        shutil.copy(inedlfile, edlfile)

        # Convert the EDL file to remove the proxy factor, convert filenames
        command = ["proxychange.py", edlfile, "-f", "%s/(.*)$" % proxypath,
                   "-t", "%s/\\1" % editpath, "-s", str(factor), "-v", "-a"]
        output += execCommand(command)

        # Create the batchfile
        soup = BeautifulSoup("", "xml")
        jobs = soup.new_tag("JOBS", WARN="1")
        soup.append(jobs)
        job = soup.new_tag("JOB", EDL_PATH=edlfile, STRATEGY="0", ENABLED="1",
                           ELAPSED="0")
        jobs.append(job)
        asset = soup.new_tag("ASSET", SRC=outputfile)
        job.append(asset)
        folder = soup.new_tag("FOLDER", NUMBER="6")
        folder.string = ""
        asset.append(folder)
        format_ = soup.new_tag("FORMAT", TYPE="FFMPEG", USE_HEADER="1",
                               FFORMAT="mp4")
        format_.string = ""
        asset.append(format_)
        audio = soup.new_tag("AUDIO", CHANNELS="2", RATE="48000", BITS="16",
                             BYTE_ORDER="1", SIGNED="1", HEADER="0", DITHER="0",
                             ACODEC="h265.mp4", AUDIO_LENGTH="0")
        audio.string = ""
        asset.append(audio)
        video = soup.new_tag("VIDEO", ACTUAL_HEIGHT="0", ACTUAL_WIDTH="0",
                             HEIGHT="0", WIDTH="0", LAYERS="0", PROGRAM="-1",
                             FRAMERATE="0", VCODEC="h264.mp4", VIDEO_LENGTH="0",
                             SINGLE_FRAME="0", INTERLACE_AUTOFIX='1',
                             INTERLACE_MODE="UNKNOWN",
                             INTERLACE_FIXMETHOD="SHIFT_UPONE",
                             REEL_NAME="cin0000", REEL_NUMBER="0", TCSTART="0",
                             TCEND="0", TCFORMAT="0")
        video.string = ""
        asset.append(video)
        job.append("PATH %s" % outputfile)
        job.append("AUDIO_CODEC h265.mp4")
        job.append("VIDEO_CODEC h264.mp4")
        job.append("FF_AUDIO_OPTIONS strict -2")
        job.append("FF_AUDIO_BITRATE 0")
        job.append("FF_VIDEO_OPTIONS crf=17")
        job.append("FF_VIDEO_BITRATE 0")
        job.append("FF_VIDEO_QUALITY -1")

        with open(batchfile, "w") as f:
            f.write(soup.prettify())

        # Run the batch
        command = ["cin", "-r", batchfile]
        output += execCommand(command)

        return output

def launch_thread(method, args):
    D = json.loads(extract_raw_data_request(request))
    id_ = D.get('id', None)
    if not id_:
        raise Exception("No ID found, screw this")

    data = {
        "method": method,
        "args": args,
        "id": id_,
    }
    requestQ.put(data, block=False)

    global handlers
    handlers[id_] = {"status": "queued"}

    global handlerThread
    if not handlerThread:
        handlerThread = HandlerThread(requestQ)
        handlerThread.daemon = True
        handlerThread.start()

    return "Please poll with id %s" % id_


# Put the script into the path for the other utils in that dir
scriptpath = os.path.dirname(os.path.realpath(sys.argv[0]))
path = os.environ.get("PATH", "")
if path:
    path += ":"
path += scriptpath
os.environ['PATH'] = path

app = Flask(__name__)
jsonrpc = JSONRPC(app, '/api', enable_web_browsable_api=True)

@jsonrpc.method("App.upload_inputs(project=String, remoteIP=String, force=Boolean) -> String",
                validate=True)
def upload_inputs(project, remoteIP=None, force=False):
    remoteIP = get_remote_ip(remoteIP)
    if remoteIP == '127.0.0.1':
        return "This is a local request, nothing to do"

    args = {
        "project": project,
        "remoteIP": remoteIP,
        "force": force,
    }
    return launch_thread("upload_inputs", args)

@jsonrpc.method("App.convert_inputs(project=String, files=Array, factor=Number) -> String",
                validate=True)
def convert_inputs(project, files=None, factor=0.5):
    args = {
        "project": project,
        "files": files,
        "factor": factor,
    }
    return launch_thread("convert_inputs", args)

@jsonrpc.method("App.download_proxies(project=String, remoteIP=String, force=Boolean) -> String",
                validate=True)
def download_proxies(project, remoteIP=None, force=False):
    remoteIP = get_remote_ip(remoteIP)
    if remoteIP == '127.0.0.1':
        return "This is a local request, nothing to do"

    args = {
        "project": project,
        "remoteIP": remoteIP,
        "force": force,
    }
    return launch_thread("download_proxies", args)

@jsonrpc.method("App.upload_proxy_edl(project=String, edlfile=String, remoteIP=String) -> String",
                validate=True)
def upload_proxy_edl(project, edlfile="edl.xml", remoteIP=None):
    remoteIP = get_remote_ip(remoteIP)
    if remoteIP == '127.0.0.1':
        return "This is a local request, nothing to do"

    args = {
        "project": project,
        "edlfile": edlfile,
        "remoteIP": remoteIP,
    }
    return launch_thread("upload_proxy_edl", args)

@jsonrpc.method("App.render_edl(project=String, edlfile=String, outfile=String) -> String",
                validate=True)
def render_edl(project, edlfile="edl.xml", outfile="output.mp4"):
    args = {
        "project": project,
        "edlfile": edlfile,
        "outfile": outfile,
    }
    return launch_thread("render_edl", args)

@jsonrpc.method("App.poll(id=String) -> String", validate=True)
def poll(id):
    global handlers
    logger.info("Polling id %s" % id)
    if id not in handlers:
        raise Exception("No record of id %s" % id)

    handler = handlers[id]
    status = handler['status']
    if status == "complete":
        del handlers[id]
        if "result" in handler:
            return handler['result']
        raise Exception(handler.get('error', "Unknown error"))

    return "status: %s" % status


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False)
