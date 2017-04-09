import argparse
import html.parser
import subprocess
from fontTools.ttLib import TTFont
from os import remove, walk
from os.path import basename, isdir, isfile, join, lexists, splitext
from pprint import pprint
from shlex import quote
from shutil import get_terminal_size
from struct import unpack
from tempfile import NamedTemporaryFile


term_width = get_terminal_size()[0]


class HTMLParser(html.parser.HTMLParser):

    def __init__(self, used_chars, ignored_tags=[], ignored_ids=[],
                 ignored_classes=[], ignored_attrs=[]):
        super().__init__()
        self.ignored_tags = [tag.lower() for tag in ignored_tags]
        self.ignored_ids = ignored_ids
        self.ignored_classes = ignored_classes
        self.ignored_attrs = [attr.lower() for attr in ignored_attrs]
        self.tagstack = []
        self.used_chars = used_chars

    def close(self):
        _ = set(self.used_chars)
        _.discard("\t")
        _.discard("\n")
        _.discard("\r")
        if isinstance(self.used_chars, set):
            self.used_chars.clear()
            self.used_chars.update(_)
        elif isinstance(self.used_chars, list):
            self.used_chars[:] = list(_)
        self.tagstack[:] = []
        super().close()

    def handle_starttag(self, tag, attrs):
        _attrs = {}
        for attr in attrs[:]:
            if len(attr) > 1:
                _attrs[attr[0].lower()] = attr[1]
            else:
                _attrs[attr[0].lower()] = None
        self.tagstack.append({
            "tag": tag.lower(),
            "id": _attrs.get("id", ""),
            "class": _attrs.get("class", ""),
            "attrs": set(_attrs.keys()),
        })

    def handle_endtag(self, tag):
        self.tagstack.pop()

    def handle_data(self, data):
        if not self.tagstack:
            self.used_chars.update(*data)
        else:
            if (self.tagstack[-1]["tag"] not in self.ignored_tags and
                self.tagstack[-1]["id"] not in self.ignored_ids and
                self.tagstack[-1]["class"] not in self.ignored_classes and
                (len(self.tagstack[-1]["attrs"]) == 0 or not
                 self.tagstack[-1]["attrs"] <= set(self.ignored_attributes))):
                self.used_chars.update(*data)


def isttc(path):
    with open(path, "rb") as f:
        return f.read(4) == b"ttcf"


def expose_ttc(src, dest):
    with open(src, "rb") as f:
        f.seek(8)
        count = unpack(">L", f.read(4))
    for index in range(count):
        font = TTFont(src, fontNumber=index)
        if font.sfntVersion == "OTTO":
            ext = ".otf"
        elif font.sfntVersion == "\0\1\0\0":
            ext = ".ttf"
        elif font.sfntVersion == "wOFF":
            ext = ".woff"
        elif font.sfntVersion == "wOF2":
            ext = ".woff2"
        else:
            ext = ""
        name = font["name"].getDebugName(6) + ext  # 6: postscript name
        font.save(join(dest, name))


_ = argparse.ArgumentParser(add_help=False)
_r = _.add_argument_group("required arguments")
_i = _.add_argument_group("ignoring arguments")
_o = _.add_argument_group("optional arguments")

# "group"
# _ = [
#     (
#         [arg...],
#         "help",
#         dict(key=value),
#     ),
# ]

"required arguments"
r = [
    (
        ["-f", "--fonts"],
        "set fonts to make subsetted",
        dict(metavar="FONT", nargs="+", required=True),
    ),
    (
        ["files"],
        "files to get used characters",
        dict(metavar="FILE", nargs="+"),
    ),
]

"ignoring arguments"
i = [
    (
        ["-F", "--ignore-files"],
        "set files to be ignored",
        dict(metavar="FILE", nargs="+", default=[]),
    ),
    (
        ["-T", "--ignore-tags"],
        "set tags to be ignored",
        dict(metavar="TAG", nargs="+", default=[
             "html", "head", "style", "script", "title"]),
    ),
    (
        ["-I", "--ignore-ids"],
        "set ids to be ignored",
        dict(metavar="ID", nargs="+", default=[]),
    ),
    (
        ["-C", "--ignore-classes"],
        "set classes to be ignored",
        dict(metavar="CLASS", nargs="+", default=[]),
    ),
    (
        ["-A", "--ignore-attributes"],
        "set attributes to be ignored",
        dict(metavar="ATTRIBUTE", nargs="+", default=[]),
    ),
]

"optional arguments"
o = [
    (
        ["-e", "--extensions"],
        "set extensions of files to get used characters",
        dict(metavar="EXTENSION", nargs="+", default=[".html"]),
    ),
    (
        ["-i", "--include-characters"],
        "include characters in text",
        dict(metavar="TEXT", default=""),
    ),
    (
        ["-o", "--output-directory"],
        "set output directory",
        dict(metavar="DESTINATION", default="."),
    ),
    (
        ["-w", "--woff"],
        "output as woff (optionally required 'zopfli' module)",
        dict(action="store_true", default=False),
    ),
    (
        ["-W", "--woff2"],
        "output as woff2 (required 'brotli' module)",
        dict(action="store_true", default=False),
    ),
    (
        ["-v", "--verbose"],
        "print a lot of logs to reassure you",
        dict(action="store_true", default=False),
    ),
    (
        ["-h", "--help"],
        "print help message and exit",
        dict(action="help", default=argparse.SUPPRESS),
    ),
]

for item in r:
    _r.add_argument(*item[0], help=item[1], **item[2])
for item in i:
    _i.add_argument(*item[0], help=item[1], **item[2])
for item in o:
    _o.add_argument(*item[0], help=item[1], **item[2])

usage_space = " " * len(f"usage: {_.prog} ")
_usage = ["[-F FILE...] [-T TAG...] [-I ID...] [-C CLASS...] "
          "[-A ATTRIBUTE...] [-e EXTENSION...] [-i TEXT] "
          "[-o DESTINATION] [-w] [-W] [-v] [-h]"]
while len(_usage[-1]) > term_width - len(usage_space):
    index = _usage[-1].rindex("]", 0, term_width - len(usage_space)) + 1
    _usage.insert(len(_usage) - 1, _usage[-1][:index])
    _usage[-1] = _usage[-1][index + 1:]
_usage.append("-f FONT... -- FILE...")
for index in range(1, len(_usage)):
    _usage[index] = f"{usage_space}{_usage[index]}"
_.usage = "%s %s" % (_.prog, "\n".join(_usage))

_.epilog = "example: %(prog)s -f font.otf -- index.html"

args = _.parse_args()


files = args.files[:]
for item in files[:]:
    if isdir(item):
        files_to_add = []
        for _, _, files in walk(item):
            files_to_add(files)
        files.extend(files_to_add)
for item in files[:]:
    if splitext(item)[1] not in args.extensions:
        files.remove(item)
    elif item in args.ignore_files:
        files.remove(item)
files.sort()

used_chars = set()
used_chars.update(args.include_characters)
htmlparser = HTMLParser(used_chars, args.ignore_tags, args.ignore_ids,
                        args.ignore_classes, args.ignore_attributes)
for item in files:
    with open(item, "r") as f:
        htmlparser.feed(f.read())
    htmlparser.close()
    print(f"read {item}")

print(f"found {len(used_chars)} characters.")

with NamedTemporaryFile(delete=False) as f:
    _charfile = f.name
    f.write("".join(sorted(used_chars)).encode("utf-8"))
    if args.verbose:
        print(f"saved characters to {_charfile}")

woff, woff2 = args.woff, args.woff2
if not (woff or woff2):
    woff = True

if woff2:
    options = []
    if args.verbose:
        options.append("--verbose")
    try:
        import brotli
        options.append("--flavor=woff2")
    except:
        print("cannot found brotil module. trying woff")
        options.append("--flavor=woff")
    for font in args.fonts:
        dest = join(args.output_directory,
                    f"{splitext(basename(font))[0]}.woff2")
        n = None
        while lexists(dest):
            _ = splitext(dest)
            if n is None:
                n = 2
                dest = f"{_[0]}-{n}{_[1]}"
            else:
                n += 1
                dest = f"{_[0][:-len(str(n))]}{n}{_[1]}"
        _ = True
        try:
            subprocess.run(["pyftsubset", font,
                            f"--text-file={quote(_charfile)}",
                            f"--output-file={quote(dest)}",
                            *options], check=True)
        except:
            _ = False
            print(f"generation failed {font}")
        if _:
            print(f"generated subsetted font {dest}")
if woff:
    options = ["--flavor=woff"]
    if args.verbose:
        options.append("--verbose")
    try:
        import zopfli
        if args.verbose:
            print("found zopfil module. using --with-zopfil option")
        options.append("--with-zopfli")
    except:
        pass
    for font in args.fonts:
        dest = join(args.output_directory,
                    f"{splitext(basename(font))[0]}.woff")
        n = None
        while lexists(dest):
            _ = splitext(dest)
            if n is None:
                n = 2
                dest = f"{_[0]}-{n}{_[1]}"
            else:
                n += 1
                dest = f"{_[0][:-len(str(n))]}{n}{_[1]}"
        _ = True
        try:
            subprocess.run(["pyftsubset", font,
                            f"--text-file={quote(_charfile)}",
                            f"--output-file={quote(dest)}",
                            *options], check=True)
        except:
            _ = False
            print(f"generation failed {font}")
        if _:
            print(f"generated subsetted font {dest}")

remove(_charfile)
if args.verbose:
    print(f"removed {_charfile}")
