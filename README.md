# filesdir-check

```
$ filesdir-check --help
Usage: filesdir-check [options] [arguments]

filesdir-check helps locate unused FILESDIR files in Gentoo portage trees. The
idea is to look for references to each file in the relevant ebuilds and report
any files that appear to be unreferenced. Note that this is a heuristic check,
and that both false positives and false negatives can occur. By default, the
main tree is checked. Pass arguments to only check specific packages.

Arguments:
  Each of the following is a valid argument:
    category
    package
    category/package

Options:
  -h, --help            show this help message and exit
  -d DIR, --directory=DIR
                        just check the tree at DIR
  -o, --overlays        check all overlays instead of the main tree
```
