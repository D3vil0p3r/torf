import torf
from torf import _utils as utils
from torf import _errors as errors

import pytest
import os
from collections import OrderedDict
from pathlib import Path
from unittest import mock


ALPHABET = 'abcdefghijklmnopqrstuvwxyz'

def test_read_chunks__unreadable_file():
    with pytest.raises(torf.ReadError) as excinfo:
        tuple(utils.read_chunks('no/such/file', 10))
    assert excinfo.match(r'^no/such/file: No such file or directory$')

def test_read_chunks__readable_file(create_file):
    filepath = create_file('some_file', ALPHABET[:16])
    assert tuple(utils.read_chunks(filepath, 4)) == (b'abcd', b'efgh', b'ijkl', b'mnop')
    assert tuple(utils.read_chunks(filepath, 5)) == (b'abcde', b'fghij', b'klmno', b'p')
    assert tuple(utils.read_chunks(filepath, 5)) == (b'abcde', b'fghij', b'klmno', b'p')

def test_read_chunks__normal_read(create_file):
    filepath = create_file('some_file', ALPHABET[:5])
    assert tuple(utils.read_chunks(filepath, 1)) == (b'a', b'b', b'c', b'd', b'e')
    assert tuple(utils.read_chunks(filepath, 2)) == (b'ab', b'cd', b'e')
    assert tuple(utils.read_chunks(filepath, 3)) == (b'abc', b'de')
    assert tuple(utils.read_chunks(filepath, 4)) == (b'abcd', b'e')
    assert tuple(utils.read_chunks(filepath, 5)) == (b'abcde',)
    assert tuple(utils.read_chunks(filepath, 6)) == (b'abcde',)

def test_read_chunks__prepend_bytes_to_file(create_file):
    filepath = create_file('some_file', ALPHABET[:10])

    assert tuple(utils.read_chunks(filepath, 2, prepend=b'1')) == (b'1a', b'bc', b'de', b'fg', b'hi', b'j')
    assert tuple(utils.read_chunks(filepath, 2, prepend=b'12')) == (b'12', b'ab', b'cd', b'ef', b'gh', b'ij')
    assert tuple(utils.read_chunks(filepath, 2, prepend=b'123')) == (b'12', b'3a', b'bc', b'de', b'fg', b'hi', b'j')
    assert tuple(utils.read_chunks(filepath, 2, prepend=b'1234')) == (b'12', b'34', b'ab', b'cd', b'ef', b'gh', b'ij')

    assert tuple(utils.read_chunks(filepath, 3, prepend=b'1')) == (b'1ab', b'cde', b'fgh', b'ij')
    assert tuple(utils.read_chunks(filepath, 3, prepend=b'12')) == (b'12a', b'bcd', b'efg', b'hij')
    assert tuple(utils.read_chunks(filepath, 3, prepend=b'123')) == (b'123', b'abc', b'def', b'ghi', b'j')
    assert tuple(utils.read_chunks(filepath, 3, prepend=b'1234')) == (b'123', b'4ab', b'cde', b'fgh', b'ij')
    assert tuple(utils.read_chunks(filepath, 3, prepend=b'12345')) == (b'123', b'45a', b'bcd', b'efg', b'hij')
    assert tuple(utils.read_chunks(filepath, 3, prepend=b'123456')) == (b'123', b'456', b'abc', b'def', b'ghi', b'j')


def test_is_power_of_2():
    assert utils.is_power_of_2(0) is False
    for n in range(1, 30):
        assert utils.is_power_of_2(2**n) is True
        assert utils.is_power_of_2(-2**n) is True
        assert utils.is_power_of_2(3**n) is False
        assert utils.is_power_of_2(-5**n) is False


def test_iterable_startswith():
    a = ['a', 'b', 'c', 'd']
    b = ['a', 'b', 'c']
    assert utils.iterable_startswith(a, b)
    assert not utils.iterable_startswith(b, a)
    a = ['a', 'b', 'c']
    b = ['a', 'b', 'c']
    assert utils.iterable_startswith(a, b)
    assert utils.iterable_startswith(b, a)
    a = ['a', 'b', 'c']
    b = []
    assert utils.iterable_startswith(a, b)
    assert not utils.iterable_startswith(b, a)
    a = []
    b = []
    assert utils.iterable_startswith(a, b)
    assert utils.iterable_startswith(b, a)


def test_URL__max_port_number():
    utils.URL(f'http://foohost:{2**16-1}')
    with pytest.raises(torf.URLError):
        utils.URL(f'http://foohost:{2**16}')

def test_URL__min_port_number():
    utils.URL('http://foohost:0')
    with pytest.raises(torf.URLError):
        utils.URL('http://foohost:-1')


def test_real_size_of_directory(tmp_path):
    dir = tmp_path / 'dir' ; dir.mkdir()
    subdir = dir / 'subdir' ; subdir.mkdir()
    (dir / 'file1').write_bytes(b'\x00' * 100)
    (dir / 'file2').write_bytes(b'\x00' * 200)
    (subdir / 'file3').write_bytes(b'\x00' * 300)
    (subdir / 'file4').write_bytes(b'\x00' * 400)
    assert utils.real_size(dir) == 1000

def test_real_size_of_directory_with_unreadable_file(tmp_path):
    dir = tmp_path / 'dir' ; dir.mkdir()
    subdir = dir / 'subdir' ; subdir.mkdir()
    (dir / 'file1').write_bytes(b'\x00' * 100)
    (subdir / 'file2').write_bytes(b'\x00' * 200)
    subdir_mode = os.stat(subdir).st_mode
    os.chmod(subdir, mode=0o222)
    try:
        with pytest.raises(errors.ReadError) as exc_info:
            utils.real_size(dir)
        assert str(exc_info.value) == f'{subdir}: Permission denied'
    finally:
        os.chmod(subdir, mode=subdir_mode)

def test_real_size_of_file(tmp_path):
    (tmp_path / 'file').write_bytes(b'\x00' * 123)
    assert utils.real_size(tmp_path / 'file') == 123

def test_real_size_of_nonexising_path():
    with pytest.raises(errors.ReadError) as exc_info:
        utils.real_size('path/doesnt/exist')
    assert str(exc_info.value) == 'path/doesnt/exist: No such file or directory'


@pytest.fixture
def testdir(tmp_path):
    base = tmp_path / 'base'
    base.mkdir()
    foo = base / 'foo'
    foo.mkdir()
    bar = base / '.bar'
    bar.mkdir()
    baz = bar / 'baz'
    baz.mkdir()
    for path in (foo, bar, baz):
        (path / 'empty').write_text('')
        (path / '.empty').write_text('')
        (path / 'not_empty').write_text('dummy content')
        (path / '.not_empty').write_text('more dummy content')
    return base

def test_filter_files_with_default_arguments(testdir):
    files = [filepath[len(os.path.dirname(str(testdir))):]
             for filepath in utils.filter_files(testdir)]
    exp = sorted(['/base/foo/.empty', '/base/foo/.not_empty', '/base/foo/empty', '/base/foo/not_empty',
                  '/base/.bar/.empty', '/base/.bar/.not_empty', '/base/.bar/empty', '/base/.bar/not_empty',
                  '/base/.bar/baz/.empty', '/base/.bar/baz/.not_empty', '/base/.bar/baz/empty', '/base/.bar/baz/not_empty'])
    assert files == exp

def test_filter_files_without_hidden_files(testdir):
    files = [filepath[len(os.path.dirname(str(testdir))):]
             for filepath in utils.filter_files(testdir, hidden=False)]
    exp = sorted(['/base/foo/empty', '/base/foo/not_empty'])
    assert files == exp

def test_filter_files_without_empty_files(testdir):
    files = [filepath[len(os.path.dirname(str(testdir))):]
             for filepath in utils.filter_files(testdir, empty=False)]
    exp = sorted(['/base/foo/.not_empty', '/base/foo/not_empty',
                  '/base/.bar/.not_empty', '/base/.bar/not_empty',
                  '/base/.bar/baz/.not_empty', '/base/.bar/baz/not_empty'])
    assert files == exp

def test_filter_files_with_exclude_argument(testdir):
    files = [filepath[len(os.path.dirname(str(testdir))):]
             for filepath in utils.filter_files(testdir, exclude=('.*',))]
    exp = sorted(['/base/foo/empty', '/base/foo/not_empty'])
    assert files == exp

    for pattern in ('foo', 'fo?', 'f*', '?oo', '*o', 'f?o'):
        files = [filepath[len(os.path.dirname(str(testdir))):]
                 for filepath in utils.filter_files(testdir, exclude=(pattern,))]
        exp = sorted(['/base/.bar/.empty', '/base/.bar/.not_empty', '/base/.bar/empty', '/base/.bar/not_empty',
                      '/base/.bar/baz/.empty', '/base/.bar/baz/.not_empty', '/base/.bar/baz/empty', '/base/.bar/baz/not_empty'])
        assert files == exp

    files = [filepath[len(os.path.dirname(str(testdir))):]
             for filepath in utils.filter_files(testdir, exclude=('*ba?',))]
    exp = sorted(['/base/foo/.empty', '/base/foo/.not_empty', '/base/foo/empty', '/base/foo/not_empty'])
    assert files == exp

    files = [filepath[len(os.path.dirname(str(testdir))):]
             for filepath in utils.filter_files(testdir, exclude=('not_*',))]
    exp = sorted(['/base/foo/.empty', '/base/foo/.not_empty', '/base/foo/empty',
                  '/base/.bar/.empty', '/base/.bar/.not_empty', '/base/.bar/empty',
                  '/base/.bar/baz/.empty', '/base/.bar/baz/.not_empty', '/base/.bar/baz/empty'])
    assert files == exp

    files = [filepath[len(os.path.dirname(str(testdir))):]
             for filepath in utils.filter_files(testdir, exclude=('*not_*',))]
    exp = sorted(['/base/foo/.empty', '/base/foo/empty',
                  '/base/.bar/.empty', '/base/.bar/empty',
                  '/base/.bar/baz/.empty', '/base/.bar/baz/empty'])
    assert files == exp



def test_decoding():
    encoded = {
        b'one': b'foo',
        b'two': 17,
        b'three': [1, b'twelve', [b'x', {b'boo': 800}]],
        b'something': {
            b'four': b'baz',
            b'five': [{b'a': [1, 2, 3], b'b': 4}],
        }
    }
    decoded = {
        'one': 'foo',
        'two': 17,
        'three': [1, 'twelve', ['x', {'boo': 800}]],
        'something': {
            'four': 'baz',
            'five': [{'a': [1, 2, 3], 'b': 4}],
        }
    }
    assert utils.decode_dict(encoded) == decoded


def test_encoding():
    class SillyStr(str):
        def __str__(self):
            return f'This is silly: {super().__str__()}'
        __repr__ = __str__

    decoded = {
        'one': SillyStr('foo'),
        'two': 17.3,
        'three': (1, 'twelve', ['x', OrderedDict([('boo', range(3))])]),
        'something': {
            'four': 'baz',
            'five': [{'a': (1, 2, 3), 'b': -4}],
        }
    }
    encoded = {
        b'one': b'This is silly: foo',
        b'two': 17,
        b'three': [1, b'twelve', [b'x', {b'boo': [0, 1, 2]}]],
        b'something': {
            b'four': b'baz',
            b'five': [{b'a': [1, 2, 3], b'b': -4}],
        }
    }
    assert utils.encode_dict(decoded) == encoded


def test_Filepaths_accepts_string_or_iterable():
    assert utils.Filepaths('path/to/foo.jpg') == [Path('path/to/foo.jpg')]
    assert utils.Filepaths(('path/to/foo.jpg',)) == [Path('path/to/foo.jpg')]
    assert utils.Filepaths(['path/to/foo.jpg']) == [Path('path/to/foo.jpg')]

def test_Filepaths_deduplicates_when_initializing():
    fps = utils.Filepaths(('path/to/foo.jpg', 'path/to/bar.jpg', 'path/to/foo.jpg'))
    assert fps == (Path('path/to/foo.jpg'), Path('path/to/bar.jpg'))

def test_Filepaths_deduplicates_when_setting():
    fps = utils.Filepaths(('path/to/foo.jpg', 'path/to/bar.jpg'))
    fps.append('path/to/foo.jpg')
    fps.extend(('path/to/bar.jpg',))
    assert fps == (Path('path/to/foo.jpg'), Path('path/to/bar.jpg'))

def test_Filepaths_deduplicates_when_inserting():
    fps = utils.Filepaths(('path/to/foo.jpg', 'path/to/bar.jpg'))
    fps.insert(0, 'path/to/bar.jpg')
    assert fps == (Path('path/to/foo.jpg'), Path('path/to/bar.jpg'))

def test_Filepaths_treats_relative_paths_as_equal_to_their_absolute_versions(tmp_path):
    cwd = tmp_path / 'cwd' ; cwd.mkdir()
    os.chdir(cwd)
    fps = utils.Filepaths((Path('foo'),))
    assert fps == ('foo',)

    fps.append(cwd / 'foo')
    assert fps == ('foo',)
    fps.append(cwd / 'bar')
    fps.append('bar')
    assert fps == ('foo', cwd / 'bar')

def test_Filepaths_handles_directories(tmp_path):
    # Create directory with 2 files
    content = tmp_path / 'content' ; content.mkdir()
    for f in ('a', 'b'): (content / f).write_text('<data>')
    fps = utils.Filepaths((content,))
    assert fps == (content / 'a', content / 'b')

    # Replace one file with multilevel subdirectory
    subdir = content / 'b' ; subdir.unlink() ; subdir.mkdir()
    for f in ('c', 'd'): (subdir / f).write_text('<subdata>')
    subsubdir = subdir / 'subsubdir' ; subsubdir.mkdir()
    for f in ('e', 'f'): (subsubdir / f).write_text('<subdata>')
    fps[1] = content / 'b'
    assert fps == (content / 'a', subdir / 'c', subdir / 'd', subsubdir / 'e', subsubdir / 'f')

    # Replace subdirectory with file again
    for f in (subdir / 'c', subdir / 'd', subsubdir / 'e', subsubdir / 'f'):
        f.unlink()
    subsubdir.rmdir()
    subdir.rmdir()
    (content / 'b').write_text('I AM BACK')
    fps[1] = content / 'b'
    assert fps == (content / 'a', content / 'b')

def test_Filepaths_calls_callback_after_appending():
    cb = mock.MagicMock()
    fps = utils.Filepaths(('path/to/foo.jpg',), callback=cb)
    fps.append('path/to/baz.jpg')
    cb.assert_called_once_with(fps)

def test_Filepaths_calls_callback_after_removing():
    cb = mock.MagicMock()
    fps = utils.Filepaths(('path/to/foo.jpg',), callback=cb)
    del fps[0]
    cb.assert_called_once_with(fps)

def test_Filepaths_calls_callback_after_inserting():
    cb = mock.MagicMock()
    fps = utils.Filepaths(('path/to/foo.jpg',), callback=cb)
    fps.insert(0, 'path/to/baz.jpg')
    cb.assert_called_once_with(fps)

def test_Filepaths_calls_callback_after_clearing():
    cb = mock.MagicMock()
    fps = utils.Filepaths(('path/to/foo.jpg',), callback=cb)
    fps.clear()
    cb.assert_called_once_with(fps)


def test_URLs_accepts_string_or_iterable():
    urls = utils.URLs('http://foo:123')
    assert urls == utils.URLs(('http://foo:123',))
    assert urls == utils.URLs(['http://foo:123'])

def test_URLs_deduplicates_when_initializing():
    urls = utils.URLs(('http://foo:123', 'http://bar:456', 'http://foo:123'))
    assert urls == ['http://foo:123', 'http://bar:456']

def test_URLs_deduplicates_when_setting():
    urls = utils.URLs(('http://foo:123', 'http://bar:456'))
    urls.append('http://foo:123')
    urls.append('http://bar:456')
    urls.extend(('http://foo:123', 'http://bar:456'))
    assert urls == ['http://foo:123', 'http://bar:456']

def test_URLs_deduplicates_when_inserting():
    urls = utils.URLs(('http://foo:123', 'http://bar:456'))
    urls.insert(1, 'http://foo:123')
    urls.insert(0, 'http://bar:456')
    urls.insert(0, 'http://foo:123')
    urls.insert(1, 'http://bar:456')
    assert urls == ['http://foo:123', 'http://bar:456']

def test_URLs_validates_initial_urls():
    with pytest.raises(errors.URLError) as e:
        utils.URLs(('http://foo:123', 'http://bar:456:789'))
    assert str(e.value) == 'http://bar:456:789: Invalid URL'

def test_URLs_validates_appended_urls():
    urls = utils.URLs('http://foo:123')
    with pytest.raises(errors.URLError) as e:
        urls.append('http://bar:456:789')
    assert str(e.value) == 'http://bar:456:789: Invalid URL'

def test_URLs_validates_changed_urls():
    urls = utils.URLs('http://foo:123')
    with pytest.raises(errors.URLError) as e:
        urls[0] = 'http://bar:456:789'
    assert str(e.value) == 'http://bar:456:789: Invalid URL'

def test_URLs_validates_inserted_urls():
    urls = utils.URLs(('http://foo:123', 'http://bar:456'))
    with pytest.raises(errors.URLError) as e:
        urls.insert(1, 'http://baz:789:abc')
    assert str(e.value) == 'http://baz:789:abc: Invalid URL'

def test_URLs_is_equal_to_URLs_instances():
    t1 = utils.URLs(('http://foo:123', 'http://bar:456'))
    t2 = utils.URLs(('http://foo:123', 'http://bar:456'))
    assert t1 == t2
    t2 = utils.URLs(('http://foo:123', 'http://baz:789'))
    assert t1 != t2

def test_URLs_is_equal_to_iterables():
    urls = utils.URLs(('http://foo:123', 'http://bar:456'))
    assert urls == ['http://foo:123', 'http://bar:456']
    assert urls == ('http://foo:123', 'http://bar:456')

def test_URLs_is_equal_to_any_combination_of_the_same_urls():
    urls = utils.URLs(('http://foo:123', 'http://bar:456', 'http://baz:789'))
    assert urls == ('http://foo:123', 'http://bar:456', 'http://baz:789')
    assert urls == ('http://bar:456', 'http://foo:123', 'http://baz:789')
    assert urls == ('http://bar:456', 'http://foo:123', 'http://baz:789')
    assert urls == ('http://foo:123', 'http://baz:789', 'http://bar:456')

def test_URLs_calls_callback_after_appending():
    cb = mock.MagicMock()
    urls = utils.URLs(('http://foo:123', 'http://bar:456'), callback=cb)
    urls.append('http://baz:789')
    cb.assert_called_once_with(urls)

def test_URLs_calls_callback_after_removing():
    cb = mock.MagicMock()
    urls = utils.URLs(('http://foo:123', 'http://bar:456'), callback=cb)
    urls.remove('http://bar:456')
    cb.assert_called_once_with(urls)

def test_URLs_calls_callback_after_inserting():
    cb = mock.MagicMock()
    urls = utils.URLs(('http://foo:123', 'http://bar:456'), callback=cb)
    urls.insert(0, 'http://baz:789')
    cb.assert_called_once_with(urls)

def test_URLs_calls_callback_after_clearing():
    cb = mock.MagicMock()
    urls = utils.URLs(('http://foo:123', 'http://bar:456'), callback=cb)
    urls.clear()
    cb.assert_called_once_with(urls)

def test_URLs_equality():
    urls = utils.URLs(('http://foo:123', 'http://bar:456'))
    assert urls == ('http://foo:123', 'http://bar:456')
    assert urls == ['http://foo:123', 'http://bar:456']
    assert urls != ['http://foo:124', 'http://bar:456']
    assert urls != 'http://bar:456'
    assert urls != 5
    assert urls != None

def test_URLs_can_be_added():
    urls1 = utils.URLs(('http://foo:123', 'http://bar:456'))
    urls2 = utils.URLs(('http://bar', 'http://baz'))
    assert urls1 + urls2 == ('http://foo:123', 'http://bar:456',
                             'http://bar', 'http://baz')
    assert urls1 + ('http://bar',) == ('http://foo:123', 'http://bar:456',
                                       'http://bar')
    assert urls1 + 'http://baz' == ('http://foo:123', 'http://bar:456',
                                    'http://baz')

def test_URLs_replace():
    cb = mock.MagicMock()
    urls = utils.URLs(('http://foo:123', 'http://bar:456'),
                      callback=cb)
    urls.replace(['http://asdf', 'http://quux'])
    assert urls == ['http://asdf', 'http://quux']
    assert cb.call_args_list == [mock.call(urls)]


def test_Trackers_ensures_tiers_when_initializing():
    for args in (('http://foo:123', 'http://bar:456'),
                 (['http://foo:123'], 'http://bar:456'),
                 ('http://foo:123', ['http://bar:456']),
                 (['http://foo:123'], ['http://bar:456'])):
        tiers = utils.Trackers(args)
        for tier in tiers:
            assert isinstance(tier, utils.URLs)
        assert tiers == [['http://foo:123'], ['http://bar:456']]

def test_Trackers_ensures_tiers_when_setting():
    for args in (('http://foo:123', 'http://bar:456'),
                 (['http://foo:123'], 'http://bar:456'),
                 ('http://foo:123', ['http://bar:456']),
                 (['http://foo:123'], ['http://bar:456'])):
        tiers = utils.Trackers('http://quux')
        tiers.extend(args)
        for tier in tiers:
            assert isinstance(tier, utils.URLs)
        assert tiers == [['http://quux'], ['http://foo:123'], ['http://bar:456']]

        tiers = utils.Trackers('http://quux')
        tiers.append(args)
        for tier in tiers:
            assert isinstance(tier, utils.URLs)
        assert tiers == [['http://quux'], ['http://foo:123', 'http://bar:456']]

def test_Trackers_ensures_tiers_when_inserting():
    for args in (('http://foo:123', 'http://bar:456'),
                 (['http://foo:123'], 'http://bar:456'),
                 ('http://foo:123', ['http://bar:456']),
                 (['http://foo:123'], ['http://bar:456'])):
        tiers = utils.Trackers('http://quux')
        tiers.insert(1, args)
        for tier in tiers:
            assert isinstance(tier, utils.URLs)
        assert tiers == [['http://quux'], ['http://foo:123', 'http://bar:456']]

def test_Trackers_equality():
    urls = utils.Trackers(('http://foo:123', 'http://bar:456'))
    assert urls == utils.Trackers(('http://foo:123', 'http://bar:456'))
    assert urls != utils.Trackers(('http://foo:123', 'http://bar:4567'))
    assert urls == utils.Trackers(('http://foo:123', 'http://bar:456'), callback=lambda _: None)
    assert urls == [['http://foo:123'], ('http://bar:456',)]
    assert urls != [['http://foo:123'], 'http://bar:456']
    assert urls == (('http://foo:123',), ['http://bar:456'])
    assert urls != (('http://foo:123',), [['http://bar:456']])
    urls_ = utils.Trackers('http://foo:123')
    assert urls != urls_
    urls_.append('http://bar:456')
    assert urls == urls_

def test_Trackers_can_be_added():
    urls1 = utils.Trackers((('http://foo', 'http://bar'), 'http://baz'))
    urls2 = utils.Trackers(('http://a', ('http://b', 'http://c'), 'http://d'))
    assert urls1 + urls2 == (('http://foo', 'http://bar', 'http://a'),
                             ('http://baz', 'http://b', 'http://c'),
                             ('http://d',))
    assert urls1 + ('http://x',) == (('http://foo', 'http://bar', 'http://x'),
                                     ('http://baz',))
    assert urls2 + ('http://x',) == (('http://a','http://x'),
                                     ('http://b', 'http://c'),
                                     ('http://d',))
    assert urls1 + (('http://x', 'http://y'),
                    'http://z') == (('http://foo', 'http://bar', 'http://x', 'http://y'),
                                    ('http://baz', 'http://z'))
    assert urls2 + (('http://x', 'http://y'),
                    'http://z') == (('http://a', 'http://x', 'http://y'),
                                    ('http://b', 'http://c', 'http://z'),
                                    ('http://d',))
    assert urls1 + (('http://x',),
                    'http://z',
                    ('http://123', 'http://456')) == (('http://foo', 'http://bar', 'http://x'),
                                                      ('http://baz', 'http://z'),
                                                      ('http://123', 'http://456'))

def test_Trackers_callback():
    cb = mock.MagicMock()
    def assert_type(arg):
        assert type(arg) is utils.Trackers
    cb.side_effect = assert_type
    tiers = utils.Trackers(('http://foo:123', 'http://bar:456'), callback=cb)
    assert cb.call_args_list == []
    tiers.append('http://baz:789')
    assert cb.call_args_list == [mock.call(tiers)]
    del tiers[0]
    assert cb.call_args_list == [mock.call(tiers)] * 2
    tiers.insert(0, ['http://quux'])
    assert cb.call_args_list == [mock.call(tiers)] * 3
    tiers[0].append('http://asdf')
    assert cb.call_args_list == [mock.call(tiers)] * 4
    tiers[2].remove('http://baz:789')
    assert cb.call_args_list == [mock.call(tiers)] * 5
    tiers.clear()
    assert cb.call_args_list == [mock.call(tiers)] * 6

def test_Trackers_removes_empty_tier_automatically():
    tiers = utils.Trackers(('http://foo:123', 'http://bar:456'))
    assert tiers == [['http://foo:123'], ['http://bar:456']]
    tiers[0].remove('http://foo:123')
    assert tiers == [['http://bar:456']]

def test_Trackers_deduplicates_urls_automatically_when_initializing():
    tiers = utils.Trackers((['http://foo:123', 'http://bar:456', 'http://baz:789'],
                            ['http://quux', 'http://foo:123', 'http://asdf'],
                            ['http://asdf', 'http://baz:789', 'http://flim']))
    assert tiers == [['http://foo:123', 'http://bar:456', 'http://baz:789'],
                     ['http://quux', 'http://asdf'],
                     ['http://flim']]

def test_Trackers_deduplicates_urls_automatically_when_setting():
    tiers = utils.Trackers((['http://foo:123', 'http://bar:456', 'http://baz:789'],))
    tiers.append(['http://quux', 'http://foo:123'])
    assert tiers == [['http://foo:123', 'http://bar:456', 'http://baz:789'],
                     ['http://quux']]
    tiers.append(['http://foo:123', 'http://bar:456', 'http://baz:789'])
    tiers.append('http://quux')
    assert tiers == [['http://foo:123', 'http://bar:456', 'http://baz:789'],
                     ['http://quux']]

def test_Trackers_deduplicates_urls_automatically_when_inserting():
    tiers = utils.Trackers((['http://foo:123', 'http://bar:456', 'http://baz:789'],))
    tiers.insert(0, ['http://asdf', 'http://baz:789', 'http://quux', 'http://foo:123'])
    assert tiers == [['http://asdf', 'http://quux'],
                     ['http://foo:123', 'http://bar:456', 'http://baz:789']]
    tiers = utils.Trackers((['http://foo:123', 'http://bar:456', 'http://baz:789'],))
    tiers.insert(1, ['http://asdf', 'http://baz:789', 'http://quux', 'http://foo:123'])
    assert tiers == [['http://foo:123', 'http://bar:456', 'http://baz:789'],
                     ['http://asdf', 'http://quux']]

def test_Trackers_flat_property():
    tiers = utils.Trackers((['http://foo:123'], ['http://bar:456']))
    assert tiers.flat == ('http://foo:123', 'http://bar:456')

def test_Trackers_replace():
    cb = mock.MagicMock()
    tiers = utils.Trackers((['http://foo:123'], ['http://bar:456']), callback=cb)
    cb.reset_mock()
    tiers.replace(('http://asdf', ('http://qux', 'http://quux'), 'http://qaax'))
    assert tiers == (['http://asdf'], ['http://qux', 'http://quux'], ['http://qaax'])
    assert cb.call_args_list == [mock.call(tiers)]
