from pathlib import Path
import tempfile
import unittest
from scripts.update_services import Parser, generate


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / 'data'
        self.data.mkdir()

    def write(self, name, content):
        (self.data / name).write_text(content, encoding='utf-8')

    def test_filters_nested_includes_and_metadata(self):
        self.write('root', 'include:child @keep @-ads\nEXAMPLE.com # comment\nregexp:^test\nkeyword:test\n')
        self.write('child', 'include:leaf\nfull:exact.example @keep\ndrop.example @keep @ads\n')
        self.write('leaf', 'included.example @keep\n')
        config = {'services': [{'id': 'test', 'sourceList': 'root', 'verifiedAt': '2026-10-08', 'exclusions': ['private.example']}]}
        service = generate(config, self.data.parent, 'a' * 40)['services'][0]
        self.assertEqual(service['domains'], ['example.com', 'included.example'])
        self.assertEqual(service['exactDomains'], ['exact.example'])
        self.assertEqual(service['omittedRules'], 2)
        self.assertEqual(service['exclusions'], ['private.example'])
        self.assertEqual(service['verifiedAt'], '2026-10-08')

    def test_cycles_missing_lists_and_paths(self):
        self.write('a', 'include:b')
        self.write('b', 'include:a')
        for name in ['a', 'missing', '../outside']:
            with self.subTest(name=name), self.assertRaises((ValueError, FileNotFoundError)):
                Parser(self.data).read(name)

    def test_unknown_rule(self):
        self.write('bad', 'newtype:example.com')
        with self.assertRaises(ValueError):
            Parser(self.data).read('bad')

    def test_affiliations(self):
        self.write('origin', 'full:EXACT.example @keep &target\n')
        self.write('root', 'include:target @keep\n')
        self.assertEqual(Parser(self.data).read('root'), frozenset({('full', 'exact.example', frozenset({'keep'}))}))
