apt-get install python3-pip gunicorn3 nginx
pip3 install flask flask_jsonrpc

cp gunicorn.service /etc/systemd/system/
cp gunicorn.socket /etc/systemd/system/
cp nginx.conf /etc/nginx/sites-available/gunicorn
ln -s /etc/nginx/sites-available/gunicorn /etc/nginx/sites-enabled
rm /etc/nginx/sites-enabled/default
cp tmpfiles.gunicorn.conf /etc/tmpfiles.d/gunicorn.conf
mkdir /opt/video/render/logs
