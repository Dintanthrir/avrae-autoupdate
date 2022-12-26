import json
import os
import sys

from .avrae import AvraeClient
from .sources import ComparisonResult, UpdatesRepository, compare_repository_with_avrae

def pull() -> int:
    """
    Overwrite local sources with the current content from avrae and create a pull request to apply
    the changes.
    """

    def apply_repository_changes(comparison_results: list[ComparisonResult]):
        """
        From the set of all ComparisonResults apply only those which update the repository.
        """
        for result in comparison_results:
            if isinstance(result, UpdatesRepository):
                sys.stdout.write(result.summary())
                result.apply()

    # The repository checkout path
    repo_base_path = os.getenv('GITHUB_WORKSPACE')

    # Check for expected config files
    gvar_config_path = os.getenv('GVARS_CONFIG')
    if not os.path.exists(repo_base_path / gvar_config_path):
        sys.stderr.write(
            f"::error title=Missing gvars config file.::Gvar config not found at " \
            f"{gvar_config_path} create the file or specify a path using the 'gvars' " \
            "workflow input.\n"
        )
        return 1
    with open(gvar_config_path, mode='r', encoding='utf-8') as gvar_config_file:
        gvar_config = json.load(gvar_config_file)

    collections_config_path = os.getenv('COLLECTIONS_CONFIG')
    if not os.path.exists(repo_base_path / collections_config_path):
        sys.stderr.write(
            f"::error title=Missing collections config file.::Collections config not found at " \
            f"{collections_config_path} create the file or specify a path using the " \
            "'collections' workflow input.\n"
        )
        return 1
    with open(collections_config_path, mode='r', encoding='utf-8') as collections_config_file:
        collections_config = json.load(collections_config_file)

    client = AvraeClient(
        api_key=os.getenv('AVRAE_TOKEN'),
        collection_ids=collections_config.keys()
    )
    collections = client.get_collections()
    gvars = client.get_gvars()
    results = compare_repository_with_avrae(
        collections=collections,
        gvars=gvars,
        gvar_config=gvar_config,
        base_path=repo_base_path
    )
    for collection_result in results['collections']:
        apply_repository_changes(collection_result['aliases'])
        apply_repository_changes(collection_result['snippets'])
    apply_repository_changes(results['gvars'])

    return 0
