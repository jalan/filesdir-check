version_string = "filesdir-check 1.0"

import optparse
import os
import portage
import re
import string
import sys

def check_category(base_directory, category, verbose=False):
	"""
	Check each package in 'base_directory' (e.g. PORTDIR) belonging to 'category' (e.g. app-misc) for unused FILESDIR files.
	Return a list of possibly unused files.
	When this script is being used stand-alone, print them out.
	If 'verbose', print out more details about what is going on.
	"""
	if verbose: print "Checking category '{}'...".format(category)
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
	if verbose: print "\tChecking '{}'...".format(category_package)
	filesdir = os.path.join(base_directory, category_package, "files")
	if not os.path.isdir(filesdir):
		if verbose: print "\t\tIt has no 'files' directory."
		return []
	file_list = _list_files(filesdir)
	ebuilds = dict.fromkeys(_list_ebuilds(base_directory, category_package))
	for ebuild in dict.iterkeys(ebuilds):
		ebuilds[ebuild] = _process_ebuild(base_directory, category_package, ebuild)
	offending_files = []
	for file in file_list:
		if verbose: print "\t\tChecking file '{}'...".format(file),
		referencers = []
		for ebuild in dict.iterkeys(ebuilds):
			if _grep(re.escape(file), [ebuilds[ebuild]]):
				referencers.append(ebuild)
		if not referencers:
			if verbose: print "no reference found!"
			elif __name__ == "__main__": print os.path.join(base_directory, category_package, "files", file)
			offending_files.append(os.path.join(base_directory, category_package, "files", file))
		else:
			if verbose: print "referenced by '{}'.".format("', '".join(referencers))
	return offending_files

def _grep(pattern, string_list):
	"""
	Search for 'pattern' in the elements of 'string_list'; return a list of matching elements.
	'pattern' is a string describing a regular expression to be re.compiled.
	"""
	expression = re.compile(pattern)
	return filter(expression.search, string_list)

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

def _parse_options():
	"""
	Parse command-line options using optparse.
	Do various error checks.
	Return the options object.
	"""
	parser = optparse.OptionParser(usage="")
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
	(options, arguments) = parser.parse_args()
	if arguments:
		print "filesdir-check: error: this program accepts no arguments (yet)"
		sys.exit(1)
	if options.directory is not None and options.overlays:
		for arg in sys.argv:
			if arg == "-d" or arg == "--directory":
				directory_option = arg
			if arg == "-o" or arg == "--overlays":
				overlays_option = arg
		print "filesdir-check: error: conflicting options: {}, {}".format(directory_option, overlays_option)
		sys.exit(1)
	if options.directory is not None and not os.path.isdir(options.directory):
		print "filesdir-check: error: '{}' is not a valid directory".format(options.directory)
		sys.exit(1)
	if options.show_version:
		print version_string
		sys.exit(0)
	return options

def _process_ebuild(base_directory, category_package, ebuild):
	"""
	Read the given ebuild, strip quotes, fill in some standard variables, and return the resulting text
	"""
	pn = os.path.basename(category_package)
	pf = re.sub("\.ebuild$", "", ebuild)
	pvr = re.sub("^" + re.escape(pn) + "-", "", pf)
	pv = re.sub("-r[0-9]+$", "", pvr)
	p = pn + "-" + pv

	ebuild_file = open(os.path.join(base_directory, category_package, ebuild))
	ebuild_text = unicode(ebuild_file.read(), "utf-8") # ebuilds are in unicode
	ebuild_file.close();

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

	# Remove comments on a line by themselves
	ebuild_text = re.sub(re.compile("^\s*#.*?$", re.MULTILINE), "", ebuild_text)

	return ebuild_text

def _main():
	options = _parse_options()
	categories = portage.settings.categories

	if options.overlays:
		portdir_overlay = portage.settings["PORTDIR_OVERLAY"]
		overlays = portdir_overlay.split(" ")
		for overlay in overlays:
			if options.verbose: print "CHECKING OVERLAY '{}'...".format(overlay)
			for category in categories:
				check_category(overlay, category, options.verbose)
	elif options.directory:
		if options.verbose: print "CHECKING DIRECTORY '{}'...".format(options.directory)
		for category in categories:
			check_category(options.directory, category, options.verbose)
	else:
		portdir = portage.settings["PORTDIR"]
		for category in categories:
			check_category(portdir, category, options.verbose)

if __name__ == "__main__":
	_main()
