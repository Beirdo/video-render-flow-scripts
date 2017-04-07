Workflow
--------

1) Transfer all raw video files into inputs/ directory
2) (optional but recommended) Transfer inputs/ directory to render server
3) (on render server or local) Convert inputs into editable video in the
   edit/ directory
4) (on render server or local) Convert editable video to proxy files in the
   proxy/ directory
5) (if using render server) Transfer proxy/ directory to editing machine
6) Edit in cinelerra, save .XML file in proxy/ directory
7) (optional but recommended) Transfer proxy .XML to render server
8) (on render server or local) Translate proxy .XML to full-size, save in
   edit/ directory (convert files from proxy to edit as well)
9) (on render server or local) Render video from edit/ to output/ dir
10) Post output video to YouTube
11) Sync entire folder structure to render server
12) Backup output video from render server to S3
