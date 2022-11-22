"""
Compares local repository source files to avrae API responses objects.
Identifies differences and constructs a set of recommended actions to bring avrae in sync
with the local repository.
"""

import os

from .avrae import (
    Alias,
    Collection,
    Gvar,
    Snippet,
)


class ComparisonResult:
    """
    The result of a comparison between a single resource in the current repository and the avrae API
    Each result can explain any difference in state between the two locations
    Applying a result attempt to bring the two locations into sync,
      e.g. by updating an alias' contents
    """

    def summary(self) -> str:
        """
        Returns a description of the difference between the local repository and avrae API.
        """

    def apply(self):
        """
        Attempts to syncronize this resource in the local repository with avrae.
        """

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and self.__dict__ == other.__dict__)

# Aliases


class _AliasComparisonResult(ComparisonResult):
    def __init__(self, alias_path: os.PathLike) -> None:
        super().__init__()
        self.alias_path = alias_path


class LocalAliasNotFoundInAvrae(_AliasComparisonResult):
    """
    A .alias file is present in the collection directory
    but wad not found in the matching avrae collection.
    """


class _AliasComparisonResultWithAlias(_AliasComparisonResult):
    def __init__(self, alias_path: os.PathLike, alias: Alias) -> None:
        super().__init__(alias_path)
        self.alias = alias


class LocalAliasMatchesAvrae(_AliasComparisonResultWithAlias):
    """
    The local .alias file matches the current active version code in the avrae collection.
    """


class LocalAliasMissing(_AliasComparisonResultWithAlias):
    """
    An alias was found in the avrae collection which has no corresponding .alias file
    in the repository at its expected location.
    """


class LocalAliasDoesNotMatchAvrae(_AliasComparisonResultWithAlias):
    """
    The local .alias file contains code which does not match the active version on avrae.
    """

# Snippets


class _SnippetComparisonResult(ComparisonResult):
    def __init__(self, snippet_path: os.PathLike) -> None:
        super().__init__()
        self.snippet_path = snippet_path


class LocalSnippetNotFoundInAvrae(_SnippetComparisonResult):
    """
    A .snippet file is present in the collection directory
    but wad not found in the matching avrae collection.
    """


class _SnippetComparisonResultWithSnippet(_SnippetComparisonResult):
    def __init__(self, snippet_path: os.PathLike, snippet: Snippet) -> None:
        super().__init__(snippet_path)
        self.snippet = snippet


class LocalSnippetMatchesAvrae(_SnippetComparisonResultWithSnippet):
    """
    The local .snippet file matches the current active version code in the avrae collection.
    """


class LocalSnippetMissing(_SnippetComparisonResultWithSnippet):
    """
    A snippet was found in the avrae collection which has no corresponding .snippet file
    in the repository at its expected location.
    """


class LocalSnippetDoesNotMatchAvrae(_SnippetComparisonResultWithSnippet):
    """
    The local .snippet file contains code which does not match the active version on avrae.
    """

# GVars


class _GvarComparisonResult(ComparisonResult):
    def __init__(self, gvar_path: os.PathLike) -> None:
        super().__init__()
        self.gvar_path = gvar_path


class LocalGvarNotFoundInAvrae(_GvarComparisonResult):
    """
    A .gvar file is present in the configuration
    but wad not found in the matching avrae collection.
    """


class _GvarComparisonResultWithGvar(_GvarComparisonResult):
    def __init__(self, gvar_path: os.PathLike, gvar: Gvar) -> None:
        super().__init__(gvar_path)
        self.gvar = gvar


class LocalGvarMatchesAvrae(_GvarComparisonResultWithGvar):
    """
    The local .gvar file contents match the gvar in the avrae collection.
    """


class LocalGvarMissing(_GvarComparisonResultWithGvar):
    """
    A .gvar file is present in the configuration and avrae
    but was not found on disk at the expected location.
    """


class LocalGvarDoesNotMatchAvrae(_GvarComparisonResultWithGvar):
    """
    The local .gvar file contents do not match the gvar in the avrae collection.
    """


def _compare_aliases(
    collection: Collection,
    base_path: os.PathLike
) -> list[_AliasComparisonResult]:
    """
    Generate AliasComparisonResults for the given Collection
    """
    def build_alias_map(path_segments: list, alias: Alias):
        alias_map = {}
        file_name = alias.name + '.alias'
        alias_map[os.path.join(*path_segments, alias.name, file_name)] = alias
        for subalias in alias.subcommands or []:
            alias_map.update(build_alias_map(
                path_segments + [alias.name], subalias))
        return alias_map

    def build_alias_comparison(alias_path: str, alias: Alias) -> _AliasComparisonResult:
        if not os.path.exists(alias_path):
            return LocalAliasMissing(alias_path, alias)
        else:
            with open(alias_path, mode='r', encoding='utf-8') as alias_file:
                local_code = alias_file.read()
                if local_code == alias.code:
                    return LocalAliasMatchesAvrae(alias_path, alias)
                else:
                    return LocalAliasDoesNotMatchAvrae(alias_path, alias)

    def find_aliases(base_path: os.PathLike) -> list[os.PathLike]:
        found_aliases = []
        for dirpath, _, filenames in os.walk(base_path):
            shared = os.path.commonprefix([dirpath, base_path])
            dirname = os.path.relpath(dirpath, shared)
            found_aliases += [os.path.join(dirname, filename)
                              for filename in filenames if filename.endswith('.alias')]
        return found_aliases

    path_segments = [base_path, collection.name]
    aliases_map: dict[str, Alias] = {}
    for alias in collection.aliases or []:
        aliases_map.update(build_alias_map(path_segments, alias))
    comparison_results = [build_alias_comparison(alias_path, alias) for (
        alias_path, alias) in aliases_map.items()]

    local_aliases = find_aliases(base_path=os.path.join(*path_segments))
    full_local_aliases = (os.path.join(*path_segments, local_alias)
                          for local_alias in local_aliases)
    missing_aliases = (
        alias for alias in full_local_aliases if not alias in aliases_map)
    comparison_results += [LocalAliasNotFoundInAvrae(alias)
                           for alias in missing_aliases]
    return comparison_results


def _compare_snippets(
    collection: Collection,
    base_path: os.PathLike
) -> list[_SnippetComparisonResult]:
    """
    Generate SnippetComparisonResults for the given Collection
    """
    def build_snippet_comparison(snippet_path: str, snippet: Snippet) -> _AliasComparisonResult:
        if not os.path.exists(snippet_path):
            return LocalSnippetMissing(snippet_path, snippet)
        else:
            with open(snippet_path, mode='r', encoding='utf-8') as snippet_file:
                local_code = snippet_file.read()
                if local_code == snippet.code:
                    return LocalSnippetMatchesAvrae(snippet_path, snippet)
                else:
                    return LocalSnippetDoesNotMatchAvrae(snippet_path, snippet)

    def find_snippets(base_path: os.PathLike) -> list[os.PathLike]:
        found_snippets = []
        for dirpath, _, filenames in os.walk(base_path):
            shared = os.path.commonprefix([dirpath, base_path])
            dirname = os.path.relpath(dirpath, shared)
            found_snippets += [os.path.join(dirname, filename)
                               for filename in filenames if filename.endswith('.snippet')]
        return found_snippets

    snippets_directory = (base_path / collection.name / 'snippets')
    snippet_paths = ((os.path.join(snippets_directory, snippet.name +
                     '.snippet'), snippet) for snippet in collection.snippets)
    snippets_map = {snippet_path: snippet for (
        snippet_path, snippet) in snippet_paths}
    comparision_results = [build_snippet_comparison(snippet_path, snippet) for (
        snippet_path, snippet) in snippets_map.items()]

    local_snippets = find_snippets(base_path=snippets_directory)
    full_local_snippets = (os.path.normpath(os.path.join(
        snippets_directory, local_snippet)) for local_snippet in local_snippets)
    missing_snippets = (
        snippet for snippet in full_local_snippets if not snippet in snippets_map)
    comparision_results += [LocalSnippetNotFoundInAvrae(
        snippet) for snippet in missing_snippets]

    return comparision_results


def _compare_gvars(
    gvars: list[Gvar],
    config: dict[str: os.PathLike],
    base_path: os.PathLike
) -> list[_GvarComparisonResult]:
    """
    Generate GvarComparisonResults for defined Gvars

    Returns results for any gvar defined in the gvars config file,
    does not report gvars found on avrae but not present in the repo as multiple repos may be used
    to update a single avrae account so we cannot assume that all visible gvars should be included.
    """
    def build_gvar_comparison(gvar_key: str, gvar_path: os.PathLike):
        gvar: Gvar | None = next(
            filter(lambda gvar: gvar.key == gvar_key, gvars), None)
        if not gvar:
            return LocalGvarNotFoundInAvrae(gvar_path)
        elif not os.path.exists(gvar_path):
            return LocalGvarMissing(gvar_path, gvar)
        else:
            with open(gvar_path, mode='r', encoding='utf-8') as gvar_file:
                local_code = gvar_file.read()
                if local_code == gvar.value:
                    return LocalGvarMatchesAvrae(gvar_path=gvar_path, gvar=gvar)
                else:
                    return LocalGvarDoesNotMatchAvrae(gvar_path=gvar_path, gvar=gvar)

    gvars_map = ((gvar_key, os.path.join(base_path, relative_path))
                 for (gvar_key, relative_path) in config.items())
    return [build_gvar_comparison(gvar_key, gvar_path) for (gvar_key, gvar_path) in gvars_map]


def compare_repository_collection_with_avrae(collection: Collection, base_path: os.PathLike):
    """
    Compare a single Collection with the source files in the repository.
    """
    return {
        'aliases': _compare_aliases(collection=collection, base_path=base_path),
        'snippets': _compare_snippets(collection=collection, base_path=base_path),
    }


def compare_repository_with_avrae(
    collections: list[Collection],
    gvars: list[Gvar],
    gvar_config: dict[str: os.PathLike],
    base_path: os.PathLike
):
    """
    Compare all Collections and Gvars with the local repository
    """
    collection_results = [compare_repository_collection_with_avrae(
        collection=collection, base_path=base_path) for collection in collections]
    return {
        'collections': collection_results,
        'gvars': _compare_gvars(gvars=gvars, config=gvar_config, base_path=base_path)
    }

    # for each alias/snippet
    # does a local copy exist?
    # is it modified?
    # if not modified is the code unchanged?
    # does it have docs?
    # are the docs modified or do they match the dashboard copy?
    # for each collection in collections.json
    # are there any misplaced snippets not at the top level?
    # do all snippets appear in the dashboard?
    # are their any aliases not in matching folders?
    # are their folders containing aliases which are not in the dashboard?
    # do they have doc files?
    # for each gvar in gvars.json
    # is there a local copy?
    # is it modified or does it match the dashboard?
    # for each .gvar file
    # is it misplaced?
    # is it in gvars.json?
