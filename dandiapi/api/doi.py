import logging
import os

from django.conf import settings
import requests

from dandiapi.api.models import Version


def _generate_doi_data(version: Version):
    if settings.DANDI_ALLOW_LOCALHOST_URLS:
        # If this environment variable is set, the pydantic model will allow URLs with localhost
        # in them. This is important for development and testing environments, where URLs will
        # frequently point to localhost.
        os.environ['DANDI_ALLOW_LOCALHOST_URLS'] = 'True'
    from dandischema.datacite import to_datacite

    publish = settings.DANDI_DOI_PUBLISH
    prefix = settings.DANDI_DOI_API_PREFIX or '10.80507'
    dandiset_id = version.dandiset.identifier
    version_id = version.version
    doi = f'{prefix}/dandi.{dandiset_id}/{version_id}'
    metadata = version.metadata
    metadata['doi'] = doi
    return (doi, to_datacite(metadata, publish=publish))


def doi_configured() -> bool:
    return (
        settings.DANDI_DOI_API_URL is not None
        or settings.DANDI_DOI_API_USER is not None
        or settings.DANDI_DOI_API_PASSWORD is not None
        or settings.DANDI_DOI_API_PREFIX is not None
    )


def create_doi(version: Version) -> str:
    doi, request_body = _generate_doi_data(version)
    # If DOI isn't configured, skip the API call
    if doi_configured():
        try:
            requests.post(
                settings.DANDI_DOI_API_URL,
                json=request_body,
                auth=requests.auth.HTTPBasicAuth(
                    settings.DANDI_DOI_API_USER,
                    settings.DANDI_DOI_API_PASSWORD,
                ),
            ).raise_for_status()
        except requests.exceptions.HTTPError as e:
            logging.error('Failed to create DOI %s', doi)
            logging.error(request_body)
            raise e
    return doi


def delete_doi(doi: str) -> None:
    # If DOI isn't configured, skip the API call
    if doi_configured():
        doi_url = settings.DANDI_DOI_API_URL.rstrip('/') + '/' + doi
        with requests.Session() as s:
            s.auth = (settings.DANDI_DOI_API_USER, settings.DANDI_DOI_API_PASSWORD)
            try:
                r = s.get(doi_url, headers={'Accept': 'application/vnd.api+json'})
                r.raise_for_status()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    logging.warning('Tried to get data for nonexistent DOI %s', doi)
                    return
                else:
                    logging.error('Failed to fetch data for DOI %s', doi)
                    raise e
            if r.json()['data']['attributes']['state'] == 'draft':
                try:
                    s.delete(doi_url).raise_for_status()
                except requests.exceptions.HTTPError as e:
                    logging.error('Failed to delete DOI %s', doi)
                    raise e
