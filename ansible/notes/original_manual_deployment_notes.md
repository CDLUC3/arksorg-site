# Manual Installation on AWS EC2

Provides a deployment of arks.org on AWS EC2 instance listening on HTTP port 18880.

Prerequisites:
- pyenv
- python >= 3.11
- python poetry
- ruby, bundle, jekyll

**Setup python `pyenv`**

This sets up a locally installed version of python 3.11 for the resolver application.

```
# install direnv, optional but helpful for automating python env invocation
curl -sfL https://direnv.net/install.sh | bash

# Install dependencies for python build
sudo yum install gcc zlib-devel bzip2 bzip2-devel readline-devel \
  sqlite sqlite-devel openssl-devel tk-devel libffi-devel

# Install pyenv
git clone https://github.com/pyenv/pyenv.git ~/.pyenv
echo -e 'if command -v pyenv 1>/dev/null 2>&1; then\n  eval "$(pyenv init -)"\nfi' >> .bashrc_local

## restart shell
# install python 3.11
pyenv install 3.11

# set default python for shell
pyenv global 3.11
```

**Install `jekyll` and `bundler`**

Sets up `ruby`, `bundler`, and `jekyll` for building the `arks.org` static site.

```
sudo yum install ruby-devel
gem install jekyll bundler
```

**Install `nginx unit`**

This is the web server. It serves up the static pages and the resolver application on port 18880.

Add a yum repo for the Nginx `unit` distribution, `cat unit.repo`:
```
[unit]
name=unit repo
baseurl=https://packages.nginx.org/unit/amzn/2023/$basearch/
gpgcheck=0
enabled=1
```

Add the repo and install `unit`.
```
sudo yum-config-manager --add-repo unit.repo
sudo yum update
sudo yum install unit
sudo yum install unit-devel unit-python311
sudo systemctl restart unit
```

**Install the `arks.org` site**

1. Checkout this repository:
```
git clone --recursive https://github.com/CDLUC3/arksorg-site.git
```

2. Build the site documents using Jekyll. 
```
cd arksorg/arks.github.io
bundle exec jekyll build --config _config.yml,../_config.local.yml
```

The generated documents are in the `site` folder of the root.


3. Setup a virtual environment and activate
```
python -m venv ${HOME}/venv
source ${HOME}/venv/bin/activate
```

4. Install dependencies
```
cd resolver
pip install -e .
```

5. Deploy `unit` application

This populates some environment variable which are used to fill in values in the `unit.json.template`
configuration file for `unit`:

```
export APP_ROOT="$(pwd)"
export APP_PORT="18880"
export DLR='$'
mkdir -p "${APP_ROOT}/resolver/rslv/data"
envsubst < unit.json.template | curl -X PUT --data-binary @- \
  --unix-socket /usr/local/var/run/unit/control.sock \
  http://localhost/config/
```

At this point the service should be running on port 18880.

```
curl "http://localhost:18880"

<!doctype html>
<html lang="en" data-bs-theme="auto">
  <head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
...
```

