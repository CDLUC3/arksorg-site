# ARKSORG

Provides the arks.org website and ARK resolver service.

## Installation on AWS EC2

Deployment and configuration is performed by a combination of puppet and ansible.
These provide a deployment of arks.org on AWS EC2 instance listening on HTTP port 18880.

See UC3 Puppet module [`uc3_ezid_arks`](https://github.com/CDLUC3/uc3-ops-puppet-modules/tree/main/modules/uc3_ezid_arks) and ansible playbook [`deploy_arksorg_site`](./ansible/README.md).

For manual installation notes see [Manual Installation on AWS EC2](./ansible/notes/original_manual_deployment_notes.md).

## Local Development

1. Create and activate a virtual environment.

2. Clone the repo
```
git clone https://github.com/CDLUC3/arksorg-site.git
cd arksorg-site
```
3. Install using `poetry` or `pip`

```
poetry install
```
or
```
pip install -r requirements.txt
```

4. Set a local configuration, dev-config.env

```
ARKS_DEVHOST=localhost
ARKS_DEVPORT=8000
ARKS_DB_CONNECTION_STRING="sqlite:///data/registry.sqlite"
ARKS_ENVIRONMENT="development"
ARKS_SERVICE_PATTERN="(^https?://localhost:8000/)|(^https?://localhost:8000/)|(^https?://?n2t.net/)|(^https?://?arks.org/)"
LOG_LEVEL="debug"
DEBUG_SQL=false
ARKS_NAANS_SOURCE="https://cdluc3.github.io/naan_reg_priv/naan_records.json"
```

5. Configure the local NAAN database

```
mkdir data
python -m arks -c dev-config.env load-naans
```

Note that this operation should be run periodically to keep the local NAAN registry up to date with the source.


6. Run the local server

Install `uvicorn` to enable the local server:

```
pip install uvicorn
```

Then run the local server:

```
python -m arks -c dev-config.env serve
```

## Run a Docker image

```shell
docker run -p 8000:8000 -v $PWD/data:/data ghcr.io/cdluc3/arksorg-site
```

And open http://localhost:8000 in your browser.
