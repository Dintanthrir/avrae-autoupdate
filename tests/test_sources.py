"""
Tests for sources.py
"""

from autoupdate.avrae import Collection, Gvar
from autoupdate.sources import (LocalAliasDoesNotMatchAvrae,
                                LocalAliasDocsDoNotMatchAvrae,
                                LocalAliasMatchesAvrae,
                                LocalAliasDocsMatchAvrae,
                                LocalAliasMissing,
                                LocalAliasDocsMissing,
                                LocalAliasNotFoundInAvrae,
                                LocalGvarDoesNotMatchAvrae,
                                LocalGvarMatchesAvrae,
                                LocalGvarMissing,
                                LocalGvarNotFoundInAvrae,
                                LocalSnippetDoesNotMatchAvrae,
                                LocalSnippetDocsDoNotMatchAvrae,
                                LocalSnippetMatchesAvrae,
                                LocalSnippetDocsMatchAvrae,
                                LocalSnippetMissing,
                                LocalSnippetDocsMissing,
                                LocalSnippetNotFoundInAvrae,
                                _compare_aliases, _compare_gvars, _compare_snippets)


def test_compare_aliases(collection_fixtures: dict[str, Collection], tmp_path):
    collection_id = '5fa19a9814a62cb7e811c5c4'
    collection = collection_fixtures[collection_id]

    (tmp_path / 'API Collection Test').mkdir()

    (tmp_path / 'API Collection Test' / 'test-alias').mkdir()
    (tmp_path / 'API Collection Test' / 'test-alias' /
     'test-alias.alias').write_text(collection.aliases[0].code)
    (tmp_path / 'API Collection Test' / 'test-alias' /
     'test-alias.md').write_text(collection.aliases[0].docs)

    (tmp_path / 'API Collection Test' / 'test-alias' / 'test-subalias').mkdir()
    (tmp_path / 'API Collection Test' / 'test-alias' /
     'test-subalias' / 'test-subalias.alias').write_text('changed')
    (tmp_path / 'API Collection Test' / 'test-alias' /
     'test-subalias' / 'test-subalias.md').write_text('changed')

    (tmp_path / 'API Collection Test' / 'new-alias').mkdir()
    (tmp_path / 'API Collection Test' / 'new-alias' /
     'new-alias.alias').write_text('new addition')

    (tmp_path / 'Some other collection').mkdir()
    (tmp_path / 'Some other collection' / 'new-alias').mkdir()
    (tmp_path / 'Some other collection' / 'new-alias' /
     'new-alias.alias').write_text('should be ignored')

    (tmp_path / 'some-alias-file.alias').write_text('should be ignored')

    comparison = _compare_aliases(collection=collection, base_path=tmp_path)
    expected = [
        LocalAliasMatchesAvrae(
            (tmp_path / 'API Collection Test' /
             'test-alias' / 'test-alias.alias').as_posix(),
            collection.aliases[0]
        ),
        LocalAliasDocsMatchAvrae(
            (tmp_path / 'API Collection Test' /
             'test-alias' / 'test-alias.md').as_posix(),
            collection.aliases[0]
        ),
        LocalAliasDoesNotMatchAvrae(
            (tmp_path / 'API Collection Test' / 'test-alias' /
             'test-subalias' / 'test-subalias.alias').as_posix(),
            collection.aliases[0].subcommands[0]
        ),
        LocalAliasDocsDoNotMatchAvrae(
            (tmp_path / 'API Collection Test' / 'test-alias' /
             'test-subalias' / 'test-subalias.md').as_posix(),
            collection.aliases[0].subcommands[0]
        ),
        LocalAliasMissing(
            (tmp_path / 'API Collection Test' / 'test-alias' / 'test-subalias' /
             'test-subalias' / 'test-subalias.alias').as_posix(),
            collection.aliases[0].subcommands[0].subcommands[0]
        ),
        LocalAliasDocsMissing(
            (tmp_path / 'API Collection Test' / 'test-alias' / 'test-subalias' /
             'test-subalias' / 'test-subalias.md').as_posix(),
            collection.aliases[0].subcommands[0].subcommands[0]
        ),
        LocalAliasNotFoundInAvrae(
            (tmp_path / 'API Collection Test' /
             'new-alias' / 'new-alias.alias').as_posix()
        ),
    ]
    for result in expected:
        assert result in comparison, 'Expected ComparisonResult missing.'
    assert len(expected) == len(comparison)


def test_compare_snippets(collection_fixtures: dict[str, Collection], tmp_path):
    collection_id = '5fa19a9814a62cb7e811c5c4'
    collection = collection_fixtures[collection_id]
    (tmp_path / 'API Collection Test').mkdir()
    (tmp_path / 'API Collection Test' / 'snippets').mkdir()
    (tmp_path / 'API Collection Test' / 'snippets' /
     'test123.snippet').write_text(collection.snippets[0].code)
    (tmp_path / 'API Collection Test' / 'snippets' /
     'test123.md').write_text(collection.snippets[0].docs)

    # When local files match avrae
    assert _compare_snippets(collection=collection, base_path=tmp_path) == [
        LocalSnippetMatchesAvrae(
            (tmp_path / 'API Collection Test' / 'snippets' / 'test123.snippet').as_posix(),
            collection.snippets[0]
        ),
        LocalSnippetDocsMatchAvrae(
            (tmp_path / 'API Collection Test' / 'snippets' / 'test123.md').as_posix(),
            collection.snippets[0]
        ),
    ]

    # When local files differ from avrae
    (tmp_path / 'API Collection Test' / 'snippets' / 'test123.snippet').write_text('modified')
    (tmp_path / 'API Collection Test' / 'snippets' / 'test123.md').write_text('modified')
    assert _compare_snippets(collection=collection, base_path=tmp_path) == [
        LocalSnippetDoesNotMatchAvrae(
            (tmp_path / 'API Collection Test' / 'snippets' / 'test123.snippet').as_posix(),
            collection.snippets[0]
        ),
        LocalSnippetDocsDoNotMatchAvrae(
            (tmp_path / 'API Collection Test' / 'snippets' / 'test123.md').as_posix(),
            collection.snippets[0]
        ),
    ]

    # When local files do not exist in avrae and avrae files do not exist locally
    (tmp_path / 'API Collection Test' / 'snippets' / 'new.snippet').write_text('new addition')
    (tmp_path / 'API Collection Test' / 'snippets' / 'test123.snippet').unlink()
    (tmp_path / 'API Collection Test' / 'snippets' / 'test123.md').unlink()
    assert _compare_snippets(collection=collection, base_path=tmp_path) == [
        LocalSnippetMissing(
            (tmp_path / 'API Collection Test' / 'snippets' / 'test123.snippet').as_posix(),
            collection.snippets[0]
        ),
        LocalSnippetDocsMissing(
            (tmp_path / 'API Collection Test' / 'snippets' / 'test123.md').as_posix(),
            collection.snippets[0]
        ),
        LocalSnippetNotFoundInAvrae(
            (tmp_path / 'API Collection Test' / 'snippets' / 'new.snippet').as_posix()
        ),
    ]


def test_compare_gvars(tmp_path):
    (tmp_path / 'up-to-date.gvar').write_text('gvar content')
    (tmp_path / 'gvars').mkdir()
    (tmp_path / 'gvars' / 'modified-var.gvar').write_text('more gvar content')
    (tmp_path / 'gvars' / 'new-var.gvar').write_text('more gvar content')

    config = {
        "abc123": "up-to-date.gvar",
        "def456": "gvars/modified-var.gvar",
        "cba789": "gvars/new-var.gvar",
        "fed321": "gvars/not-found.gvar",
    }

    gvars = [
        Gvar(owner='999', key='abc123', owner_name='my name',
             value='gvar content', editors=[]),
        Gvar(owner='999', key='def456', owner_name='my name',
             value='current gvar content', editors=[]),
        Gvar(owner='999', key='fed321', owner_name='my name',
             value='current gvar content', editors=[]),
    ]

    comparison = _compare_gvars(gvars=gvars, config=config, base_path=tmp_path)
    assert comparison == [
        LocalGvarMatchesAvrae(
            (tmp_path / 'up-to-date.gvar').as_posix(), gvars[0]),
        LocalGvarDoesNotMatchAvrae(
            (tmp_path / 'gvars' / 'modified-var.gvar').as_posix(), gvars[1]),
        LocalGvarNotFoundInAvrae(
            (tmp_path / 'gvars' / 'new-var.gvar').as_posix()),
        LocalGvarMissing(
            (tmp_path / 'gvars' / 'not-found.gvar').as_posix(), gvars[2]),
    ]
