"""
Tools for interacting with Avrae's API
"""

from itertools import chain
import json
import typing
import requests

AVRAE_API_TIMEOUT = 3.0

class Alias(typing.NamedTuple):
    """
    Avrae Alias API response object
    """
    name: str
    code: str
    versions: list
    docs: str
    entitlements: list[str]
    collection_id: str
    id: str
    subcommand_ids: list[str]
    parent_id: str | None
    subcommands: list['Alias']

class Snippet(typing.NamedTuple):
    """
    Avrae Snippet API response object
    """
    name: str
    code: str
    versions: list
    docs: str
    entitlements: list[str]
    collection_id: str
    id: str

class Collection(typing.NamedTuple):
    """
    Avrae Collection API response object
    """
    name: str
    description: str
    image: str | None
    owner: str
    alias_ids: list[str]
    snippet_ids: list[str]
    publish_state: str
    num_subscribers: int
    num_guild_subscribers: int
    last_edited: str
    created_at: str
    tags: list[str]
    id: str
    aliases: list[Alias]
    snippets: list[Snippet]

class Gvar(typing.NamedTuple):
    """
    Avrae Gvar API response object
    """
    owner: str
    key: str
    owner_name: str
    value: str
    editors: list[str]

class CodeVersion(typing.NamedTuple):
    """
    Avrae API response for Alias/Snippet code versions
    """
    version: int
    content: str
    created_at: str
    is_current: bool

class ConstructedPath(typing.NamedTuple):
    """
    Associate repo files with Avrae collections
    """
    obj_name: str
    rel_path: str
    id: str
    type: str
    content: str

class RequestError(BaseException):
    """
    Wrapper for Avrae API response errors
    """

def _snippet_from_data(json_data) -> Snippet:
    """
    Extract a Snippet from an Avrae API response's JSON
    """
    return Snippet(
        name=json_data['name'],
        code=json_data['code'],
        versions=json_data.get('versions', []),
        docs=json_data.get('docs', ''),
        entitlements=json_data.get('entitlements', []),
        collection_id=json_data['collection_id'],
        id=json_data['_id'],
    )

def _alias_from_data(json_data) -> Alias:
    """
    Extract an Alias from an Avrae API response's JSON
    """
    return Alias(
        name=json_data['name'],
        code=json_data['code'],
        versions=json_data.get('versions', []),
        docs=json_data.get('docs', ''),
        entitlements=json_data.get('entitlements', []),
        collection_id=json_data['collection_id'],
        id=json_data['_id'],
        subcommand_ids=json_data.get('subcommand_ids', []),
        parent_id=json_data.get('parent_id', None),
        subcommands=[
            _alias_from_data(alias_data) for alias_data in json_data.get('subcommands', [])
        ],
    )

def _collection_from_data(json_data) -> Collection:
    """
    Extract a Collection from an Avrae API response's JSON
    """
    return Collection(
        name=json_data['name'],
        description=json_data['description'],
        image=json_data['image'],
        owner=json_data['owner'],
        alias_ids=json_data['alias_ids'],
        snippet_ids=json_data['snippet_ids'],
        publish_state=json_data['publish_state'],
        num_subscribers=json_data['num_subscribers'],
        num_guild_subscribers=json_data['num_guild_subscribers'],
        last_edited=json_data['last_edited'],
        created_at=json_data['created_at'],
        tags=json_data['tags'],
        id=json_data['_id'],
        aliases=[_alias_from_data(alias_data) for alias_data in json_data['aliases']],
        snippets=[_snippet_from_data(snippet_data) for snippet_data in json_data['snippets']],
    )

def _gvars_from_data(json_data) -> list[Gvar]:
    """
    Construct Gvars from an Avrae API response's JSON
    """
    def _gvar_from_data(gvar_json) -> Gvar:
        return Gvar(
            owner=gvar_json['owner'],
            key=gvar_json['key'],
            owner_name=gvar_json['owner_name'],
            value=gvar_json['value'],
            editors=gvar_json['editors']
        )
    owned_gvars = (_gvar_from_data(gvar_data) for gvar_data in json_data['owned'])
    editable_gvars = (_gvar_from_data(gvar_data) for gvar_data in json_data['editable'])
    return list(chain(owned_gvars, editable_gvars))

def _version_from_data(json_data) -> CodeVersion:
    """
    Construct a CodeVersion from an Avrae API response
    """
    return CodeVersion(
        version=json_data['version'],
        content=json_data['content'],
        created_at=json_data['created_at'],
        is_current=json_data['is_current']
    )

def _get_collection(api_key: str, collection_id: str) -> Collection:
    """
    Fetch a collection from Avrae
    """
    path = f'https://api.avrae.io/workshop/collection/{collection_id}/full'
    headers = {
        'Authorization': api_key
    }
    response = requests.get(
        url=path,
        headers=headers,
        timeout=AVRAE_API_TIMEOUT,
    )
    response.raise_for_status()
    response_data = response.json()
    if not response_data['success']:
        raise RequestError(f'{collection_id} collection data grab did not succeed.\n'
                           f'{json.dumps(response_data, indent=4)}')
    return _collection_from_data(response.json()['data'])

def _get_gvars(api_key: str) -> list[Gvar]:
    """
    Fetch the set of all gvars the user can edit from avrae
    """
    path = 'https://api.avrae.io/customizations/gvars'
    headers = {
        'Authorization': api_key
    }
    response = requests.get(
        url=path,
        headers=headers,
        timeout=AVRAE_API_TIMEOUT,
    )
    response.raise_for_status()
    response_data = response.json()
    return _gvars_from_data(response_data)

def _recent_matching_version(
    api_key: str,
    resource_type: typing.Literal['snippet'] | typing.Literal['alias'],
    item_id: str,
    code: str
    ) -> CodeVersion | None:
    item_limit = 10
    request_limit = 5 # better to skip the oldest versions than flood avrae with requests

    headers = {
        'Authorization': api_key
    }

    skip = 0
    page = 0
    fetch_next_page = True
    while fetch_next_page and page < request_limit:
        page += 1

        path = (
            f'https://api.avrae.io/workshop/{resource_type}/{item_id}/code'
            f'?skip={skip}&limit={item_limit}'
        )

        response = requests.get(
            url=path,
            headers=headers,
            timeout=AVRAE_API_TIMEOUT,
        )
        response.raise_for_status()
        response_data = response.json()
        if not response_data['success']:
            raise RequestError(f'{resource_type}/{item_id} failed to fetch code versions.\n'
                           f'{json.dumps(response_data, indent=4)}')
        versions_data = response.json()['data']
        for version_data in versions_data:
            if version_data['content'] == code:
                return _version_from_data(version_data)

        skip += len(versions_data)
        fetch_next_page = len(versions_data) == item_limit
    return None

class AvraeClient():
    """
    An object for managing interactions with Avrae's API on behalf of a specific account.

    Caches collection and gvar responses to avoid repeated API calls when possible.
    """

    _collections: list[Collection] | None = None
    _gvars: list[Gvar] | None = None

    def __init__(self, api_key: str, collection_ids: list[str]) -> None:
        self.api_key = api_key
        self.collection_ids = collection_ids

    def _clear_collection_from_cache(self, collection_id: str):
        if self._collections is None:
            return
        self._collections = list(
            filter(
                lambda collection: collection.id != collection_id, self._collections
            )
        )

    def get_collections(self) -> list[Collection]:
        """
        Return the set of collections registered with this client.
        """

        if not self._collections:
            self._collections = [
                _get_collection(
                    api_key=self.api_key,
                    collection_id=collection_id
                ) for collection_id in self.collection_ids
            ]
        return self._collections

    def get_collection(self, collection_id: str) -> Collection | None:
        """
        Return a specific collection registered with this client.
        """

        return next(
            filter(
                lambda collection: collection.id == collection_id, self.get_collections()
            ),
            None
        )

    def get_gvars(self) -> list[Gvar]:
        """
        Return the set of all gvars editable by client's account.
        """

        if not self._gvars:
            self._gvars = _get_gvars(api_key=self.api_key)
        return self._gvars

    def recent_matching_version(self, item: Alias | Snippet) -> CodeVersion | None:
        """
        Return the most recent version of a snippet or alias with the same code as the given item.

        Used to identify if the current repository code exists in an avrae version but is out of
        date due to edits uploaded directly to avrae.
        """

        return _recent_matching_version(
            api_key=self.api_key,
            resource_type='alias' if isinstance(item, Alias) else 'snippet',
            item_id=item.id,
            code=item.code
        )

    def create_new_code_version(self, item: Alias | Snippet, code: str) -> CodeVersion:
        """
        Creates a new code version containing the item's current code.
        """

        resource_type='alias' if isinstance(item, Alias) else 'snippet'
        response = requests.post(
            url=f'https://api.avrae.io/workshop/{resource_type}/{item.id}/code',
            headers={
                'Authorization': self.api_key
            },
            timeout=AVRAE_API_TIMEOUT,
            json={
                'content': code
            }
        )
        response.raise_for_status()
        response_data = response.json()
        if not response_data['success']:
            raise RequestError(f'{resource_type}/{id} failed to create new code versions.\n'
                f'{json.dumps(response_data, indent=4)}')
        self._clear_collection_from_cache(item.collection_id)

        new_version = _version_from_data(response_data['data'])
        return new_version

    def set_active_code_version(self, item: Alias | Snippet, version: int) -> Alias | Snippet:
        """
        Sets a specific code version of an item to be active.
        """

        resource_type='alias' if isinstance(item, Alias) else 'snippet'
        response = requests.put(
            url=f'https://api.avrae.io/workshop/{resource_type}/{item.id}/active-code',
            headers={
                'Authorization': self.api_key
            },
            timeout=AVRAE_API_TIMEOUT,
            json={
                'version': version
            }
        )
        response.raise_for_status()
        response_data = response.json()
        if not response_data['success']:
            raise RequestError(f'{resource_type}/{id} failed to create new code versions.\n'
                f'{json.dumps(response_data, indent=4)}')
        self._clear_collection_from_cache(item.collection_id)

        if isinstance(item, Alias):
            return _alias_from_data(response_data['data'])
        return _snippet_from_data(response_data['data'])

    def update_docs(self, item: Alias | Snippet, yaml: str) -> Alias | Snippet:
        """
        Sets the yaml docs for a given item.

        Note: docs are not tied to a code version.
        """

        resource_type='alias' if isinstance(item, Alias) else 'snippet'
        response = requests.patch(
            url=f'https://api.avrae.io/workshop/{resource_type}/{item.id}',
            headers={
                'Authorization': self.api_key
            },
            timeout=AVRAE_API_TIMEOUT,
            json={
                'docs': yaml,
                'name': item.name,
            }
        )
        response.raise_for_status()
        response_data = response.json()
        if not response_data['success']:
            raise RequestError(f'{resource_type}/{id} failed to update docs.\n'
                f'{json.dumps(response_data, indent=4)}')
        self._clear_collection_from_cache(item.collection_id)

        if isinstance(item, Alias):
            return _alias_from_data(response_data['data'])
        return _snippet_from_data(response_data['data'])

    def update_gvar(self, gvar: Gvar, value: str):
        """
        Updates the contents of the given gvar.
        """

        response = requests.post(
            url=f'https://api.avrae.io/customizations/gvars/{gvar.key}',
            headers={
                'Authorization': self.api_key
            },
            timeout=AVRAE_API_TIMEOUT,
            json={
                'value': value
            }
        )
        response.raise_for_status()
        response_content = response.content.decode('ascii')
        if response_content != 'Gvar updated.':
            raise RequestError(f'Updating gvar {gvar.key} failed.\n{response_content}')
