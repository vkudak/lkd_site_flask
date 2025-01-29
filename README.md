![GitHub Issues or Pull Requests](https://img.shields.io/github/issues-raw/vkudak/lkd_site_flask)
![GitHub Release](https://img.shields.io/github/release/vkudak/lkd_site_flask)

### Powered by:
![Python](https://img.shields.io/badge/python-3670A0?style=flat-square&logo=python&logoColor=ffdd54)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=flat-square&logo=flask&logoColor=white)
![Postgres](https://img.shields.io/badge/postgres-%23316192.svg?style=flat-square&logo=postgresql&logoColor=white)
![sqlalchemy](https://img.shields.io/badge/-SqlAlchemy-FCA121?style=flat-square&logo=SqlAlchemy)

![Gunicorn](https://img.shields.io/badge/gunicorn-%298729.svg?style=flat-square&logo=gunicorn&logoColor=white)
![Nginx](https://img.shields.io/badge/nginx-%23009639.svg?style=flat-square&logo=nginx&logoColor=white)


# LKD Site

## Include:
 - **LKD overview**
 - **List of Instruments**
 - **User Authentication**
 - **Photometry of EB project**
 - **Photometry of Resident Space Objects**
 - **Calculation of RSO Passes**
 - **etc...**


## Install
**Use `venv` and**

`$ pip install -r requirements.txt`

`$ gunicorn -c gunicorn_myconf.py --workers 1 --threads 3 run:app --log-level=debug --reload`

**OR**

Use instruction from DigitalOcean website -
[Flask + Gunicorn + NGINX](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-22-04#step-5-configuring-nginx-to-proxy-requests)

Useful:
[Journalctl to View and Manipulate Systemd Logs](https://www.digitalocean.com/community/tutorials/how-to-use-journalctl-to-view-and-manipulate-systemd-logs)

