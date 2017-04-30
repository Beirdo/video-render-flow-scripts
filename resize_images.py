#! /usr/bin/env python3
# vim:ts=4:sw=4:ai:et:si:sts=4

import logging
import PythonMagick as Magick
import sys
import os

FORMAT = "%(asctime)s: %(name)s:%(lineno)d (%(threadName)s) - %(levelname)s - %(message)s"
logging.basicConfig(format=FORMAT)
logging.getLogger(None).setLevel(logging.INFO)
logging.captureWarnings(True)
logger = logging.getLogger(__name__)

rect = Magick.DrawableRectangle(0, 0, 1920, 1080)

for file_ in sys.argv[1:]:
    basedir = os.path.realpath(os.path.dirname(file_))
    outdir = os.path.join(basedir, "out")
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    basename = os.path.basename(file_)
    (basename, _) = os.path.splitext(basename)
    outfile = os.path.join(outdir, basename + ".png")

    logger.info("Processing %s" % file_)
    img = Magick.Image(file_)
    logger.info("From %s @ %sx%s" % (img.magick(), img.columns(), img.rows()))
    img.quality(100)
    img.magick('PNG')
    img.resize('1920x1080')

    bg = Magick.Image()
    bg.size("1920x1080")
    bg.strokeColor("black")
    bg.fillColor("black")
    bg.draw(rect)

    bg.composite(img, Magick.GravityType.CenterGravity,
                 Magick.CompositeOperator.SrcOverCompositeOp)
    bg.quality(100)
    bg.magick('PNG')
    logger.info("To %s @ %sx%s" % (bg.magick(), bg.columns(), bg.rows()))
    bg.write(outfile)
