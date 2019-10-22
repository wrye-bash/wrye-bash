#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# GPL License and Copyright Notice ============================================
#  This file is part of Wrye Bash.
#
#  Wrye Bash is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  Wrye Bash is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Wrye Bash; if not, write to the Free Software Foundation,
#  Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
#  Wrye Bash copyright (C) 2005-2009 Wrye, 2010-2019 Wrye Bash Team
#  https://github.com/wrye-bash
#
# =============================================================================

"""
Deploy nightly and production builds.

To deploy to dropbox you need a Dropbox account and access to the wrye bash
shared folder in your dropbox. Optionally, you can override the regular oauth
process with your own API access token via '--access-token'. Deploying test
builds to a subfolder is also supported with '--branch'.

To deploy to nexus you need to have Google Chrome/Chromium installed and be
logged in to nexus in a browser [Supported: Chrome, Firefox, Safari]. The
appropriate selenium driver and the needed auth cookies are automatically
retrieved. If there are issues with this process, you can override the
chromedriver version with '--driver-version' and the auth cookie values with
'--member-id', '--pass-hash' and '--sid'.

Unless '--no-config' is supplied, all values are saved to a
configuration file at './deploy_config.json'. Values are
stored as a dictionary with the format (keys in lowercase):
    '%ARGUMENT%': '%VALUE%'
"""

import argparse

import deploy_dropbox
import deploy_nexus
import utils

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    utils.setup_deploy_parser(parser)
    parser.add_argument(
        "--no-dropbox",
        action="store_false",
        dest="dropbox",
        help="Do not deploy to dropbox.",
    )
    parser.add_argument(
        "--no-nexus",
        action="store_false",
        dest="nexus",
        help="Do not deploy to nexusmods.",
    )
    parser.add_argument(
        "--production-release",
        action="store_true",
        dest="prod_rel",
        help="Deploy a production release only.",
    )
    dropbox_parser = parser.add_argument_group("dropbox arguments")
    deploy_dropbox.setup_parser(dropbox_parser)
    nexus_parser = parser.add_argument_group("nexus arguments")
    deploy_nexus.setup_parser(nexus_parser)
    args = parser.parse_args()
    open(args.logfile, "w").close()
    if args.dropbox and not args.prod_rel:
        deploy_dropbox.main(args)
        print
    if args.nexus or args.prod_rel:
        args.release = "production"
        deploy_nexus.main(args)
