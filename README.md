<!-- ![Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/vkudak/lkd_site_flask/master/test_status_shields.json) -->
<!-- ![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/vkudak/lkd_site_flask/master/coverage_shields.json) -->
![Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/vkudak/cd865320b628af7303721348b27ce3f0/raw/badges.json&label=Coverage)
![Tests](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/vkudak/cd865320b628af7303721348b27ce3f0/raw/badges.json&label=Tests)
![GitHub Issues or Pull Requests](https://img.shields.io/github/issues-raw/vkudak/lkd_site_flask)
![GitHub Issues or Pull Requests](https://img.shields.io/github/issues-closed/vkudak/lkd_site_flask)
![GitHub Release](https://img.shields.io/github/release/vkudak/lkd_site_flask)


### Powered by:
![Python](https://img.shields.io/badge/python-3670A0?style=flat-square&logo=python&logoColor=ffdd54)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=flat-square&logo=flask&logoColor=white)
![Postgres](https://img.shields.io/badge/postgres-%23316192.svg?style=flat-square&logo=postgresql&logoColor=white)
![sqlalchemy](https://img.shields.io/badge/-SqlAlchemy-FCA121?style=flat-square&logo=SqlAlchemy)

![Gunicorn](https://img.shields.io/badge/gunicorn-%298729.svg?style=flat-square&logo=gunicorn&logoColor=white)
![Nginx](https://img.shields.io/badge/nginx-%23009639.svg?style=flat-square&logo=nginx&logoColor=white)


LKD Site
==================

## Include:
 - **LKD overview**
 - **List of Instruments**
 - **User Authentication**
 - **Photometry of EB project**
 - **Photometry of Resident Space Objects**
 - **Calculation of RSO Passes**
 - **etc...**


Installation
------------
**Use `venv`**  
Run:  
`pip install -r requirements.txt`  
`gunicorn -c gunicorn_myconf.py --workers 1 --threads 3 run:app --log-level=debug --reload`  
or simply  
`gunicorn -c gunicorn_myconf.py run:app`

For server - write your own gunicorn_conf.py and  make a Service according to instruction from DigitalOcean website  
Server Tips:
[Flask + Gunicorn + NGINX](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-22-04#step-5-configuring-nginx-to-proxy-requests)  
Journal Tips:
[Journalctl to View and Manipulate Systemd Logs](https://www.digitalocean.com/community/tutorials/how-to-use-journalctl-to-view-and-manipulate-systemd-logs)


Test Coverage
------------
`pip install coverage-badge`  
`coverage run -m pytest`  
Generate Badge icon:  
`coverage-badge -o coverage.svg -f`  
Show Coverage Report:  
`coverage report -m`
