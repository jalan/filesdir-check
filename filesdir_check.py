"""Look for unused FILESDIR files."""


import io
import optparse
import os
import re
import sys

import portage


DESCRIPTION = (
    "filesdir-check helps locate unused FILESDIR files in Gentoo portage "
    "trees. The idea is to look for references to each file in the relevant "
    "ebuilds and report any files that appear to be unreferenced. Note that "
    "this is a heuristic check, and that both false positives and false "
    "negatives can occur. By default, the main tree is checked. Pass "
    "arguments to only check specific packages."
)


class OptionParser(optparse.OptionParser):
    """OptionParser with different help output."""

    def error(self, message):
        """Print error output."""
        sys.exit("{}: error: {}".format(self.get_prog_name(), message))

    def format_help(self, formatter=None):
        """Format help output."""
        if formatter is None:
            formatter = self.formatter
        result = []
        result.append(self.get_usage() + "\n")
        result.append(self.format_description(formatter) + "\n")
        result.append(
            "Arguments:\n"
            "  Each of the following is a valid argument:\n"
            "    category\n"
            "    package\n"
            "    category/package\n\n")
        result.append(self.format_option_help(formatter))
        return "".join(result)


def check_category(base_directory, category):
    """Check the given category.

    Check each package in 'base_directory' belonging to 'category' for unused
    FILESDIR files. Return a list of possibly unused files.
    """
    category_packages = portage.portdb.cp_all([category], [base_directory])
    offending_files = []
    for category_package in category_packages:
        offending_files.extend(
            check_category_package(base_directory, category_package))
    return offending_files


def check_category_package(base_directory, category_package):
    """Check the given category/package.

    Check 'category_package' in 'base_directory' for unused FILESDIR files.
    Return a list of possibly unused files.
    """
    filesdir = os.path.join(base_directory, category_package, "files")
    if not os.path.isdir(filesdir):
        return []
    file_list = list_files(filesdir)
    ebuild_contents = []
    for ebuild in list_ebuilds(base_directory, category_package):
        ebuild_contents.append(process_ebuild(
            base_directory, category_package, ebuild,
        ))
    offending_files = []
    for file_name in file_list:
        referenced = any(file_name in content for content in ebuild_contents)
        if not referenced:
            offending_files.append(os.path.join(
                base_directory, category_package, "files", file_name,
            ))
    return offending_files


def list_ebuilds(base_directory, category_package):
    """List ebuilds in 'base_directory' belonging to 'category_package'."""
    dir_list = os.listdir(os.path.join(base_directory, category_package))
    return [entry for entry in dir_list if entry.endswith(".ebuild")]


def list_files(filesdir):
    """Return a list of files in 'filesdir'.

    The returned list specifies each file's path relative to 'filesdir'.
    """
    file_list = []
    for item in os.listdir(filesdir):
        item_path = os.path.join(filesdir, item)
        if os.path.isdir(item_path):
            for deeper_item in list_files(item_path):
                file_list.append(os.path.join(item, deeper_item))
        else:
            file_list.append(item)
    return file_list


def parse_command_line():
    """Parse command-line using optparse and do error checks."""
    processed_arguments = []
    parser = OptionParser(
        usage="%prog [options] [arguments]", description=DESCRIPTION)
    parser.disable_interspersed_args()
    parser.add_option(
        "-d", "--directory", dest="directory", action="store", type="string",
        help="just check the tree at DIR", metavar="DIR",
    )
    parser.add_option(
        "-o", "--overlays", action="store_true", dest="overlays",
        help="check all overlays instead of the main tree", default=False,
    )
    options, arguments = parser.parse_args()
    if options.directory is not None and options.overlays:
        parser.error("conflicting options: --directory and --overlays")
    if options.directory is not None and not os.path.isdir(options.directory):
        parser.error("'{}' is not a valid directory".format(options.directory))
    if arguments:
        all_categories = portage.settings.categories
        all_category_packages = portage.portdb.cp_all()
        all_packages = [cp.partition("/")[2] for cp in all_category_packages]
        # Valid argument forms: category, category/package, package
        for argument in arguments:
            if argument in all_categories:
                processed_arguments.append(argument)
            elif argument in all_category_packages:
                processed_arguments.append(argument)
            elif argument in all_packages:
                # Make sure we get all duplicates
                for index, package in enumerate(all_packages):
                    if package == argument:
                        processed_arguments.append(
                            all_category_packages[index])
            else:
                parser.error(
                    "'{}' is not a valid category or package".format(argument)
                )
    return options, processed_arguments


def process_ebuild(base_directory, category_package, ebuild):
    """Prepare ebuild text for searching.

    Read the given ebuild, strip quotes, fill in some standard variables, and
    return the resulting text.
    """
    pn = os.path.basename(category_package)
    pf = re.sub("\.ebuild$", "", ebuild)
    pvr = re.sub("^" + re.escape(pn) + "-", "", pf)
    pv = re.sub("-r[0-9]+$", "", pvr)
    p = pn + "-" + pv

    # ebuilds are in utf-8
    ebuild_file = io.open(
        os.path.join(base_directory, category_package, ebuild),
        "r", encoding="utf-8",
    )
    ebuild_text = ebuild_file.read()
    ebuild_file.close()

    # Remove double quotes
    ebuild_text = ebuild_text.replace('"', "")

    # Fill in standard variables
    ebuild_text = ebuild_text.replace("${PN}", pn)
    ebuild_text = ebuild_text.replace("$PN", pn)
    ebuild_text = ebuild_text.replace("${PF}", pf)
    ebuild_text = ebuild_text.replace("$PF", pf)
    ebuild_text = ebuild_text.replace("${PVR}", pvr)
    ebuild_text = ebuild_text.replace("$PVR", pvr)
    ebuild_text = ebuild_text.replace("${PV}", pv)
    ebuild_text = ebuild_text.replace("$PV", pv)
    ebuild_text = ebuild_text.replace("${P}", p)
    ebuild_text = ebuild_text.replace("$P", p)

    return ebuild_text


def main():
    """Run as a script, printing out the unused files."""
    all_categories = portage.settings.categories

    options, processed_arguments = parse_command_line()

    if options.overlays:
        portdir_overlay = portage.settings["PORTDIR_OVERLAY"]
        target_directories = portdir_overlay.split(" ")
    elif options.directory:
        target_directories = [options.directory]
    else:
        target_directories = [portage.settings["PORTDIR"]]

    unused_files = []
    for target_directory in target_directories:
        if processed_arguments:
            for argument in processed_arguments:
                if argument in all_categories:
                    unused_files.extend(
                        check_category(target_directory, argument))
                else:
                    unused_files.extend(
                        check_category_package(target_directory, argument))
        else:
            for category in all_categories:
                unused_files.extend(check_category(target_directory, category))

    if unused_files:
        print("\n".join(unused_files))


if __name__ == "__main__":
    main()
