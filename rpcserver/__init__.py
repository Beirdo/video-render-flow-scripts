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

logdir = "/opt/video/render/logs"
logfile = os.path.join(logdir, "rpcserver.log")

FORMAT = "%(asctime)s: %(name)s:%(lineno)d (%(threadName)s) - %(levelname)s - %(message)s"
logging.basicConfig(filename=logfile, format=FORMAT)
logging.getLogger(None).setLevel(logging.INFO)
logging.captureWarnings(True)
logger = logging.getLogger(__name__)

queues = {
    "cpu-bound": Queue(),
    "internal-network-bound": Queue(),
    "external-network-bound": Queue(),
    "local": Queue(),
}

queueMap = {
    "upload_inputs": "internal-network-bound",
    "convert_inputs": "cpu-bound",
    "download_proxies": "internal-network-bound",
    "download_editables": "internal-network-bound",
    "upload_edl": "local",
    "upload_proxy_edl": "local",
    "render_edl": "cpu-bound",
    "upload_to_youtube": "external-network-bound",
    "archive_to_s3": "external-network-bound",
}

handlerThreads = {}
handlers = {}
outputThread = None


class OutputThread(Thread)
    def __init__(self):
        Thread.__init__(self)

        self.sel = selectors.DefaultSelector()
        self.idMap = {}
        self.name = "OutputThread"
        self.daemon = True
        global handlers
        self.handlers = handlers

    def run(self):
        while True:
            events = sel.select()
            for (key, mask) in events:
                callback = key.data
                callback(key.fileobj, mask)

    def add(self, id_):
        fd = self.handlers[id_]['pipe']
        self.idMap[fd] = id_
        self.sel.register(fd, selectors.EVENT_READ, self.read)

    def removeId(self, id_):
        fd = self.handlers[id_]['pipe']
        self.remove(fd)

    def remove(self, fd):
        del self.idMap[fd]
        self.sel.unregister(fd)
        fd.close()

    def read(self, fd, mask):
        data = fd.read(1024)
        if data:
            id_ = self.idMap.get(fd, None)
            handler = self.handlers.get(id_, None)
            if id_ and handler:
                handler['data'].append(data)
                return

        self.remove(fd)


def get_remote_ip(remoteIP=None):
    logger.info("Remote IP: %s" % remoteIP)
    if not remoteIP or remoteIP == '""':
        logger.info(dir(request))
        logger.info(request.__dict__)
        remoteIP = request.environ.get("HTTP_X_REAL_IP",  None)
    logger.info("Remote IP: %s" % remoteIP)
    if not remoteIP or remoteIP == "localhost":
        remoteIP = "127.0.0.1"
    logger.info("Remote IP: %s" % remoteIP)
    return remoteIP


class HandlerThread(Thread):
    def __init__(self, queue, queueName, handlers):
        Thread.__init__(self)

        self.queue = queue
        self.name = "%s-handler" % queueName
        self.daemon = True
        self.handlers = handlers

    def run(self):
        while True:
            item = self.queue.get()

            if not item:
                continue

            id_ = item.get('id', None)
            method = item.get('method', None)
            args = item.get('args', [])
            if not id_ or not method:
                continue

            if id_ not in self.handlers:
                self.handlers[id_] = {}
            data = self.handlers[id_]
            data['status'] = 'in-progress'
            data['processTime'] = time.time()
            data['queueTime'] = time.time() - data['queueTime']
            data['data'] = []
            logger.info("Starting handler for method %s (id %s)" %
                        (method, id_))
            args['myId'] = id_
            try:
                if not hasattr(self, method):
                    raise Exception("No thread handler exists for method %s" %
                                    method)
                methodFunc = getattr(self, method)
                output = methodFunc(**args)
                if output:
                    data['results'] = output
            except Exception as e:
                data['error'] = str(e)

            data['status'] = "complete"
            data['processTime'] = time.time() - data['processTime']
            logger.info("Finishing handler for method %s (id %s)" %
                        (method, id_))

    def execCommand(self, command, id_):
        global outputThread
        if not isinstance(command, list):
            command = command.split()

        logger.info("Running %s" % " ".join(command))
        if not outputThread or not outputThread.is_alive():
            outputThread = OutputThread()
            outputThread.start()

        retCode = -1
        handler = self.handlers[id_]
        with Popen(command, shell=False, stdin=None, stdout=PIPE,
                   stderr=STDOUT, bufsize=0) as p:
            handler['pipe'] = p.stdout
            outputThread.add(id_)
            p.wait()
            retCode = p.returncode
        finally:
            outputThread.removeId(id_)

        if handler['data']:
            output = b" ".join(handler['data']).decode("utf-8")

        if retCode:
            message = "Command: %s returned %s" % (" ".join(command), retCode)
            if output:
                message += "\n\nOutput: %s" % output
            logger.error(message)
            raise Exception(message)

        handler['result'] = output

    def upload_inputs(self, myId, project, remoteIP=None, force=False):
        path = os.path.join("/opt/video/render/video", project, "input", "")
        command = ["rsync", "-avt", "%s:%s" % (remoteIP, path), path]
        if force:
            command.insert(2, "--delete")
        self.execCommand(command, myId)

    def convert_inputs(self, myId, project, files=None, factor=0.5):
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
        r
        files = [file_ for file_ in set(files) if os.path.exists(file_)]

        if not files:
            return "No files in project %s" % project

        for file_ in files:
            command = ["convert_gstream.sh", "--factor", str(factor), file_]
            self.handlers[myId]['output'].append("\n\n")
            self.execCommand(command, myId)

    def download_proxies(self, myId, project, remoteIP=None, force=False):
        path = os.path.join("/opt/video/render/video", project, "proxy", "")
        command = ["rsync", "-avt", path, "%s:%s" % (remoteIP, path)]
        if force:
            command.insert(2, "--delete")
        self.execCommand(command, myId)

    def download_editables(self, myId, project, remoteIP=None, force=False):
        path = os.path.join("/opt/video/render/video", project, "edit", "")
        command = ["rsync", "-avt", path, "%s:%s" % (remoteIP, path)]
        if force:
            command.insert(2, "--delete")
        self.execCommand(command, myId)

    def upload_edl(self, myId, project, edlfile="edl.xges", remoteIP=None):
        path = os.path.join("/opt/video/render/video", project, "edit",
                            edlfile)
        command = ["rsync", "-avt", "%s:%s" % (remoteIP, path), path]
        self.execCommand(command, myId)

    def upload_proxy_edl(self, myId, project, edlfile="edl.xges",
                         remoteIP=None):
        path = os.path.join("/opt/video/render/video", project, "proxy",
                            edlfile)
        command = ["rsync", "-avt", "%s:%s" % (remoteIP, path), path]
        self.execCommand(command, myId)

    def render_edl(self, myId, project, edlfile="edl.xges",
                   outfile="output.mp4", proxy=False, mode="pitivi"):
        if proxy:
            path = os.path.join("/opt/video/render/video", project, "proxy",
                                "factor.txt")
            if not os.path.exists(path):
                factor = 0.5
            else:
                with open(path, "r") as f:
                    data = f.read()
                factor = float(data.strip())

            proxypath = os.path.join("/opt/video/render/video", project,
                                     "proxy")
            inedlfile = os.path.join(proxypath, edlfile)

        editpath = os.path.join("/opt/video/render/video", project, "edit")
        outputpath = os.path.join("/opt/video/render/video", project, "output")
        os.makedirs(outputpath, 0o755, exist_ok=True)

        edlfile = os.path.join(editpath, edlfile)
        batchfile = os.path.join(editpath, "batchlist.xml")
        outputfile = os.path.join(outputpath, outfile)

        output = ""

        if mode == 'cinelerra':
            if proxy:
                # Copy the EDL file from proxy -> edit
                shutil.copy(inedlfile, edlfile)

                # Convert the EDL file to remove the proxy factor,
                # convert filenames
                command = ["cinelerra-proxychange.py", edlfile, "-f",
                           "%s/(.*)$" % proxypath, "-t", "%s/\\1" % editpath,
                           "-s", str(factor), "-v", "-a"]
                self.execCommand(command, myId)

            # Create the batchfile
            soup = BeautifulSoup("", "xml")
            jobs = soup.new_tag("JOBS", WARN="1")
            soup.append(jobs)
            job = soup.new_tag("JOB", EDL_PATH=edlfile, STRATEGY="0",
                               ENABLED="1", ELAPSED="0")
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
                                 BYTE_ORDER="1", SIGNED="1", HEADER="0",
                                 DITHER="0", ACODEC="h265.mp4",
                                 AUDIO_LENGTH="0")
            audio.string = ""
            asset.append(audio)
            video = soup.new_tag("VIDEO", ACTUAL_HEIGHT="0", ACTUAL_WIDTH="0",
                                 HEIGHT="0", WIDTH="0", LAYERS="0",
                                 PROGRAM="-1", FRAMERATE="0", VCODEC="h264.mp4",
                                 VIDEO_LENGTH="0", SINGLE_FRAME="0",
                                 INTERLACE_AUTOFIX='1',
                                 INTERLACE_MODE="UNKNOWN",
                                 INTERLACE_FIXMETHOD="SHIFT_UPONE",
                                 REEL_NAME="cin0000", REEL_NUMBER="0",
                                 TCSTART="0", TCEND="0", TCFORMAT="0")
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
            self.execCommand(command, myId)
        elif mode == 'pitivi':
            command = ["render_pitivi.sh", edlfile, outputfile]
            self.execCommand(command, myId)

    def upload_to_youtube(self, myId, project, outfile="output.mp4", params={}):
        path = os.path.join("/opt/video/render/video", project, "output",
                            outfile)
        command = ["upload_video.py", "--file", path,
                   "--title", params.get('title', "Title"),
                   "--description", params.get('description', "Description"),
                   "--category", str(int(params.get('category', 28))),
                   "--keywords", params.get('keywords', "None"),
                   "--privacyStatus", "public", "--noauth_local_webserver"]
        self.execCommand(command, myId)

    def archive_to_s3(self, myId, project, skip=False, inputs=False,
                      delete=False, accelerate=False):
        command = ["archive_to_s3.py", "--project", project]
        if skip:
            command.append("--skip")
        if inputs:
            command.append("--inputs")
        if delete:
            command.append("--delete")
        if accelerate:
            command.append("--accelerate")
        self.execCommand(command, myId)


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
    queueName = queueMap.get(method, "local")
    queue = queues.get(queueName, None)
    if not queue:
        queueName = "local"
        queue = queues['local']

    global handlers
    handlers[id_] = {
        "status": "queued",
        "queueTime": time.time(),
    }

    logger.info("Queuing request for %s method %s (id %s)" %
                (queueName, method, id_))
    queue.put(data, block=False)

    global handlerThreads
    if not handlerThreads.get(queueName, None):
        handlerThreads[queueName] = HandlerThread(queue, queueName, handlers)
        handlerThreads[queueName].start()

    return "Please poll with id %s" % id_


# Put the script into the path for the other utils in that dir
scriptpath = os.path.dirname(os.path.realpath(sys.argv[0]))
path = os.environ.get("PATH", "")
if path:
    path += ":"
path += scriptpath
path += ":/opt/video/render/scripts"
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

@jsonrpc.method("App.download_editables(project=String, remoteIP=String, force=Boolean) -> String",
                validate=True)
def download_editables(project, remoteIP=None, force=False):
    remoteIP = get_remote_ip(remoteIP)
    if remoteIP == '127.0.0.1':
        return "This is a local request, nothing to do"

    args = {
        "project": project,
        "remoteIP": remoteIP,
        "force": force,
    }
    return launch_thread("download_editables", args)

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

@jsonrpc.method("App.upload_edl(project=String, edlfile=String, remoteIP=String) -> String",
                validate=True)
def upload_edl(project, edlfile="edl.xges", remoteIP=None):
    remoteIP = get_remote_ip(remoteIP)
    if remoteIP == '127.0.0.1':
        return "This is a local request, nothing to do"

    args = {
        "project": project,
        "edlfile": edlfile,
        "remoteIP": remoteIP,
    }
    return launch_thread("upload_edl", args)

@jsonrpc.method("App.upload_proxy_edl(project=String, edlfile=String, remoteIP=String) -> String",
                validate=True)
def upload_proxy_edl(project, edlfile="edl.xges", remoteIP=None):
    remoteIP = get_remote_ip(remoteIP)
    if remoteIP == '127.0.0.1':
        return "This is a local request, nothing to do"

    args = {
        "project": project,
        "edlfile": edlfile,
        "remoteIP": remoteIP,
    }
    return launch_thread("upload_proxy_edl", args)

@jsonrpc.method("App.render_edl(project=String, edlfile=String, outfile=String, proxy=Boolean, mode=String) -> String",
                validate=True)
def render_edl(project, edlfile="edl.xges", outfile="output.mp4", proxy=False,
               mode='pitivi'):
    args = {
        "project": project,
        "edlfile": edlfile,
        "outfile": outfile,
        "proxy": proxy,
        "mode": mode,
    }
    return launch_thread("render_edl", args)

@jsonrpc.method("App.upload_to_youtube(project=String, outfile=String, title=String, description=String, category=Number, keywords=String) -> String",
                validate=True)
def upload_to_youtube(project, outfile="output.mp4", title="Title",
                      description="Description", category=28, keywords="none"):
    args = {
        "project": project,
        "outfile": outfile,
        "params": {
            "title": title,
            "description": description,
            "category": category,
            "keywords": keywords,
        }
    }
    return launch_thread("upload_to_youtube", args)

@jsonrpc.method("App.archive_to_s3(project=String, skip=Boolean, inputs=Boolean, delete=Boolean, accelerate=Boolean) -> String",
                validate=True)
def archive_to_s3(**kwargs):
    return launch_thread("archive_to_s3", kwargs)


@jsonrpc.method("App.poll(id=String) -> String", validate=True)
def poll(id):
    global handlers
    logger.info("Polling id %s" % id)
    if id not in handlers:
        raise Exception("No record of id %s" % id)

    handler = handlers[id]
    status = handler['status']
    result = {
        "status": status,
        "result": b"".join(handler['data']).decode("utf-8"),
        "queueDuration": handler['queueTime'],
    }

    if status == "complete":
        result["processDuration"] = time.time() - handler['processTime']
        del handlers[id]
        if not handler.get('data', None):
            raise Exception(handler.get('error', "Unknown error"))

    return json.dumps(result)

@jsonrpc.method("App.list_outstanding() -> Array", validate=True)
def list_outstanding():
    global handlers
    logger.info("Listing outstanding tasks")
    return list(handlers.keys())


if __name__ == '__main__':
    logHandler = logging.StreamHandler()
    logFormatter = logging.Formatter(fmt=FORMAT)
    logHandler.setFormatter(logFormatter)
    logging.getLogger(None).addHandler(logHandler)
    app.run(host='0.0.0.0', debug=False)
