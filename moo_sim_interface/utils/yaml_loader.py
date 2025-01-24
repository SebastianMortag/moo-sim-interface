import re

from yaml.composer import Composer
from yaml.constructor import SafeConstructor
from yaml.parser import Parser
from yaml.reader import Reader
from yaml.resolver import BaseResolver
from yaml.scanner import Scanner


class CustomResolver(BaseResolver):
    pass


CustomResolver.add_implicit_resolver(
    'tag:yaml.org,2002:bool',
    re.compile(r'''^(?:yes|Yes|YES|no|No|NO
                    |true|True|TRUE|false|False|FALSE
                    |on|On|ON|off|Off|OFF)$''', re.X),
    list('yYnNtTfFoO'))

CustomResolver.add_implicit_resolver(
    'tag:yaml.org,2002:float',
    re.compile(r'''^(?:[-+]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+][0-9]+)?
                    |\.[0-9][0-9_]*(?:[eE][-+][0-9]+)?
                    |[-+]?\.(?:inf|Inf|INF)
                    |\.(?:nan|NaN|NAN))$''', re.X),
    list('-+0123456789.'))

CustomResolver.add_implicit_resolver(
    'tag:yaml.org,2002:int',
    re.compile(r'''^(?:[-+]?0b[0-1_]+
                    |[-+]?0[0-7_]+
                    |[-+]?(?:0|[1-9][0-9_]*)
                    |[-+]?0x[0-9a-fA-F_]+)$''', re.X),
    list('-+0123456789'))

CustomResolver.add_implicit_resolver(
    'tag:yaml.org,2002:merge',
    re.compile(r'^(?:<<)$'),
    ['<'])

CustomResolver.add_implicit_resolver(
    'tag:yaml.org,2002:null',
    re.compile(r'''^(?: ~
                    |null|Null|NULL
                    | )$''', re.X),
    ['~', 'n', 'N', ''])

CustomResolver.add_implicit_resolver(
    'tag:yaml.org,2002:timestamp',
    re.compile(r'''^(?:[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]
                    |[0-9][0-9][0-9][0-9] -[0-9][0-9]? -[0-9][0-9]?
                     (?:[Tt]|[ \t]+)[0-9][0-9]?
                     :[0-9][0-9] :[0-9][0-9] (?:\.[0-9]*)?
                     (?:[ \t]*(?:Z|[-+][0-9][0-9]?(?::[0-9][0-9])?))?)$''', re.X),
    list('0123456789'))

CustomResolver.add_implicit_resolver(
    'tag:yaml.org,2002:value',
    re.compile(r'^(?:=)$'),
    ['='])

# The following resolver is only for documentation purposes. It cannot work
# because plain scalars cannot start with '!', '&', or '*'.
CustomResolver.add_implicit_resolver(
    'tag:yaml.org,2002:yaml',
    re.compile(r'^(?:!|&|\*)$'),
    list('!&*'))


class CustomSafeLoader(Reader, Scanner, Parser, Composer, SafeConstructor, CustomResolver):
    def __init__(self, stream):
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        SafeConstructor.__init__(self)
        CustomResolver.__init__(self)
