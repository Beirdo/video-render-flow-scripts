#!/usr/bin/env python3
# vim:ts=4:sw=4:ai:et:si:sts=4

# Based on a script
# (c) 2006 Hermann Vosseler <Ichthyostega@web.de>
# This code is free software and may be used under the
# terms and conditions of the GPL version 2

# Modifications and rewrite
# (c) 2017 Gavin Hurlbut <gjhurlbu@gmail.com>


import sys
import os
import re
import codecs
from optparse import OptionParser
from bs4 import BeautifulSoup
from bs4.diagnose import diagnose


#------------CONFIGURATION----------------------------
PROGVER  = 0.1
ENCODING = 'latin1'
#------------CONFIGURATION----------------------------


# -----------parse-cmdline----------------------------
def parseAndDo():
    # -----------------DEBUG
    #    sys.argv = ['proxychange.py', 'proxy.xml', '--from', r'toc/(\w+)\.toc', '--to', r'toc/\1.proxy.mov']
#    sys.argv = ['proxychange.py', 'proxy.xml', '--from', r'toc/(\w+)\.toc', '--to', r'toc/\1.proxy.mov']
    print(sys.argv)
    # -----------------DEBUG

    usage = "usage: %prog filename.xml --search <PATTERN> --replace <PATTERN> [options]"

    parser = OptionParser(usage=usage, version="proxychange %1.2f" % PROGVER) 

    parser.add_option("-f", "--from",   type="string", dest="src"                                         ,help="Regular Expression to match against the footage filenames")
    parser.add_option("-t", "--to",     type="string", dest="dest"                                        ,help="Template to substitute for the region matched by --from in footage filenames")
    parser.add_option("-v", "--video",                 dest="doVideo", action="store_true", default=False ,help="process video tracks. defaults to True if neither --video nor --audio given")
    parser.add_option("-a", "--audio",                 dest="doAudio", action="store_true", default=False ,help="process audio tracks. defaults to False")
    parser.add_option("-s", "--scale",  type="float",  dest="scale",                        default=1.0   ,help="Scale factor to apply to any camera automation on all processed video tracks")
    parser.add_option("-o", "--offset", type="int",    dest="offset",                       default=0     ,help="Offset added to the start position of any modyfied edits.")

    (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.error("at least the name of the cinelerra session file is required.")

    if (options.src and not (options.doVideo or options.doAudio)):
        options.doVideo=True

    if (options.doVideo or options.doAudio) and not (options.src and options.dest):
        parser.error("need to specify search and replace patterns (--from and --to).")

    # compile regular expression for filename search and replace
    try :
        nameRegExp = re.compile(options.src)
        nameTempl  = options.dest
    except:
        __exerr("Syntax error in regular expression.")


    #------dispatch-action--------------
    if options.doVideo or options.doAudio:
        dom = readSession(filename=args[0])
        doTransform(dom, doVideo=options.doVideo,doAudio=options.doAudio,
                         regExp=nameRegExp, template=nameTempl,
                         scale=options.scale)
        writeSession(dom,filename=args[0])
        sys.exit(0)

    parser.error("no action specified.")




def readSession(filename):
    # read in a cinelerra session file (XML)
    print("read session %s"%filename)
    if not os.path.exists(filename):
        __err("can't find cinelerra session file \"%s\"." % filename)
    with open(filename, 'r') as f:
        dom = BeautifulSoup(f, "xml")
    return dom


def writeSession(dom,filename):
    # wirtes the (probably modified) dom into the given session file,
    # creates a backup beforehand if necessary
    print("writing session %s ...."%filename)
    try:
        if os.path.exists(filename):
            if os.path.exists(filename+".bak"):
                os.remove(filename+".bak")
            os.rename(filename,filename+".bak")
    except:
        __exerr("Exception while creating backup")

    try:
        with open(filename, "w") as f:
            f.write(dom.prettify())
    except:
        __exerr("can't write to target file \"%s\"" % filename)

    print("modified %s written to disk."%filename)


def transformPath(node, attrib, fromRe, to):
    path = node.get(attrib)
    match = fromRe.search(path)
    if not match:
        return False

    repl = match.expand(to)
    repl = path[:match.start()] + repl + path[match.end():]
    node[attrib] = repl
    return True


def doTransform(dom, **args):
    # do the actual work:
    # visit all edits on all audio/video tracks and try to
    # match the footage filename against a regular expression.
    # Modify this filename if it matches.
    # (TODO) Apply offset to any edit source start positions
    print("transform args=%s"%args)
    edl = dom.select('EDL')[0]
    if transformPath(edl, 'PATH', args['regExp'], args['template']):
        print("Modified EDL Path")

    localsession = edl.select('LOCALSESSION')[0]
    if transformPath(localsession, 'CLIP_TITLE', args['regExp'], 
                     args['template']):
        print("Modified localsession")

    assets = edl.select('ASSETS > ASSET')
    for asset in assets:
        if transformPath(asset, 'SRC', args['regExp'], args['template']):
            print("Modified asset")

    tracks = edl.select('TRACK')
    for track in tracks:
        # only Tracks in Timeline, not in Clips, not in viewer window
        isVideo = track.get('TYPE') == 'VIDEO'
        isAudio = track.get('TYPE') == 'AUDIO'
        if isVideo and not args['doVideo']: continue
        if isAudio and not args['doAudio']: continue

        # modify track data
        edits = track.select('EDIT > FILE')
        for edit in edits:
            if transformPath(edit, 'SRC', args['regExp'], args['template']):
                print("modified Track...")
            
        # rewrite the camera automation to account for the
        # different size of the proxy clip (only if parameter 'scale' given)

    if args['scale'] != 1.0:
        camautos = edl.select('CAMERA_Z > AUTO')
        for camauto in camautos:
            value = camauto.get('VALUE')
            value = float(value)
            value *= args['scale']
            value = "%10.8e" % value
            camauto['VALUE'] = value
            print("rescaled camera automation...")

        videovalues = ["ACTUAL_HEIGHT", "ACTUAL_WIDTH", "HEIGHT", "WIDTH"]
        videos = edl.select('VIDEO')
        for video in videos:
            changed = False
            for key in videovalues:
                value = video.get(key, None)
                if not value:
                    continue
                value = float(value)
                value /= args['scale']
                value = "%d" % int(value)
                video[key] = value
                changed = True

            if changed:
                print("rescaled video definition...")

    all_tags = dom.find_all()
    for tag in all_tags:
        if tag.is_empty_element:
            tag.can_be_empty_element = False

#
# --Messages-and-errors-------------------------------------
#
def __err(text):
    print("--ERROR-------------------------")
    print(text)
    sys.exit(255)

def __exerr(text):
    raise sys.exc_type(sys.exc_value)
    __err(text+": »%s« (%s)" % (sys.exc_type,sys.exc_value))


if __name__=="__main__":
    parseAndDo()

