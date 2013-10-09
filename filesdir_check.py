"""
Look for unused FILESDIR files.
"""

from __future__ import print_function

import codecs
import optparse
import os
import portage
import re
import sys

VERSION_STRING = "filesdir-check 1.1"
DESCRIPTION = ("filesdir-check helps locate unused FILESDIR files in Gentoo "
               "portage trees. The idea is to look for references to each "
               "file in the relevant ebuilds and report any files that "
               "appear to be unreferenced. Note that this is a heuristic "
               "check, and that both false positives and false negatives can "
               "occur.")

class MyOptionParser(optparse.OptionParser):
	"""
	Subclass OptionParser to change help output.
	"""
	def error(self, message):
		sys.exit("{0}: error: {1}".format(self.get_prog_name(), message))

	def format_help(self, formatter=None):
		if formatter is None:
			formatter = self.formatter
		result = []
		result.append(self.get_usage() + "\n")
		result.append(self.format_description(formatter) + "\n")
		result.append("Arguments:\n  Each of the following is a valid argument:\n    category\n    package\n    category/package\n\n")
		result.append(self.format_option_help(formatter))
		return "".join(result)

def check_category(base_directory, category, verbose=False):
	"""
	Check each package in 'base_directory' (e.g. PORTDIR) belonging to 'category' (e.g. app-misc) for unused FILESDIR files.
	Return a list of possibly unused files.
	When this script is being used stand-alone, print them out.
	If 'verbose', print out more details about what is going on.
	"""
	if verbose:
		print("Checking category '{}'...".format(category))
	category_packages = portage.portdb.cp_all([category], [base_directory])
	offending_files = []
	for category_package in category_packages:
		offending_files.extend(check_category_package(base_directory, category_package, verbose))
	return offending_files

def check_category_package(base_directory, category_package, verbose=False):
	"""
	Check 'category_package' (e.g. x11-libs/vte) in 'base_directory' (e.g. PORTDIR) for unused FILESDIR files.
	Return a list of possibly unused files.
	When this script is being used stand-alone, print them out.
	If 'verbose', print out more details about what is going on.
	"""
	if verbose:
		print("\tChecking '{}'...".format(category_package))
	filesdir = os.path.join(base_directory, category_package, "files")
	if not os.path.isdir(filesdir):
		if verbose:
			print("\t\tIt has no 'files' directory.")
		return []
	file_list = _list_files(filesdir)
	ebuilds = dict.fromkeys(_list_ebuilds(base_directory, category_package))
	for ebuild in dict.keys(ebuilds):
		ebuilds[ebuild] = _process_ebuild(base_directory, category_package, ebuild)
	offending_files = []
	for file in file_list:
		if verbose:
			print("\t\tChecking file '{}'...".format(file), end=' ')
		referencers = []
		for ebuild in dict.keys(ebuilds):
			if _grep(re.escape(file), [ebuilds[ebuild]]):
				referencers.append(ebuild)
		if not referencers:
			if verbose:
				print("no reference found!")
			elif __name__ == "__main__":
				print(os.path.join(base_directory, category_package, "files", file))
			offending_files.append(os.path.join(base_directory, category_package, "files", file))
		else:
			if verbose:
				print("referenced by '{}'.".format("', '".join(referencers)))
	return offending_files

def _grep(pattern, string_list):
	"""
	Search for 'pattern' in the elements of 'string_list'; return a list of matching elements.
	'pattern' is a string describing a regular expression to be re.compiled.
	"""
	expression = re.compile(pattern)
	return [i for i in string_list if expression.search(i)]

def _list_ebuilds(base_directory, category_package):
	"""
	Return a list of ebuilds in 'base_directory' (e.g. PORTDIR) belonging to 'category_package' (e.g. media-sound/lame).
	"""
	return _grep("\.ebuild$", os.listdir(os.path.join(base_directory, category_package)))

def _list_files(filesdir):
	"""
	Return a list of files in 'filesdir'. The returned list specifies each file's path relative to 'filesdir'.
	"""
	file_list = []
	for item in os.listdir(filesdir):
		item_path = os.path.join(filesdir, item)
		if os.path.isdir(item_path):
			for deeper_item in _list_files(item_path):
				file_list.append(os.path.join(item, deeper_item))
		else:
			file_list.append(item)
	return file_list

def _parse_command_line():
	"""
	Parse command-line using optparse.
	Do various error checks.
	Return the options object and a processed argument list.
	"""
	processed_arguments = []
	parser = MyOptionParser(usage="%prog [options] [arguments]", description=DESCRIPTION)
	parser.disable_interspersed_args()
	parser.add_option("-d", "--directory", dest="directory",
	                  action="store", type="string",
	                  help="just check the tree at DIR", metavar="DIR")
	parser.add_option("-o", "--overlays",
	                  action="store_true", dest="overlays", default=False,
	                  help="check all overlays instead of the main tree")
	parser.add_option("-v", "--verbose",
	                  action="store_true", dest="verbose", default=False,
	                  help="display more output, not just the offending files")
	parser.add_option("-V", "--version",
	                  action="store_true", dest="show_version", default=False,
	                  help="display version information")
	options, arguments = parser.parse_args()
	if options.directory is not None and options.overlays:
		sys.exit("filesdir-check: error: conflicting options: --directory and --overlays")
	if options.directory is not None and not os.path.isdir(options.directory):
		sys.exit("filesdir-check: error: '{}' is not a valid directory".format(options.directory))
	if arguments:
		all_categories = portage.settings.categories
		all_category_packages = portage.portdb.cp_all()
		# Valid argument forms: category, category/package, package
		for argument in arguments:
			if argument in all_categories:
				processed_arguments.append(argument)
			elif argument in all_category_packages:
				processed_arguments.append(argument)
			elif _grep("/" + argument, all_category_packages):
				processed_arguments.extend(_grep("/" + argument + '$', all_category_packages))
			else:
				sys.exit("filesdir-check: error: '{}' is not a valid category or package".format(argument))
	if options.show_version:
		print(VERSION_STRING)
		sys.exit(0)
	return options, processed_arguments

def _process_ebuild(base_directory, category_package, ebuild):
	"""
	Read the given ebuild, strip quotes, fill in some standard variables, and return the resulting text
	"""
	pn = os.path.basename(category_package)
	pf = re.sub("\.ebuild$", "", ebuild)
	pvr = re.sub("^" + re.escape(pn) + "-", "", pf)
	pv = re.sub("-r[0-9]+$", "", pvr)
	p = pn + "-" + pv

	# ebuilds are in utf-8
	ebuild_file = codecs.open(os.path.join(base_directory, category_package, ebuild), 'r', encoding='utf-8')
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

def _main():
	"""
	Run as a script.
	"""
	all_categories = portage.settings.categories

	options, processed_arguments = _parse_command_line()

	if options.overlays:
		portdir_overlay = portage.settings["PORTDIR_OVERLAY"]
		target_directories = portdir_overlay.split(" ")
	elif options.directory:
		target_directories = [options.directory]
	else:
		target_directories = [portage.settings["PORTDIR"]]

	for target_directory in target_directories:
		if options.verbose:
			print("CHECKING TREE AT '{}'...".format(target_directory))
		if processed_arguments:
			for argument in processed_arguments:
				if argument in all_categories:
					check_category(target_directory, argument, options.verbose)
				else:
					check_category_package(target_directory, argument, options.verbose)
		else:
			for category in all_categories:
				check_category(target_directory, category, options.verbose)

if __name__ == "__main__":
	_main()
