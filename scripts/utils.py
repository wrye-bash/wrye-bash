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

import contextlib
import errno
import io
import json
import logging
import math
import os
import subprocess
import sys
import urllib2
import webbrowser

import browsercookie
import dropbox

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
DEPLOY_FOLDER = os.path.join(ROOT_PATH, "deploy")
DEPLOY_LOG = os.path.join(ROOT_PATH, "deploy.log")
DEPLOY_CONFIG = os.path.join(DEPLOY_FOLDER, "deploy_config.json")
DIST_PATH = os.path.join(ROOT_PATH, "dist")

# verbosity:
#  quiet (warnings and above)
#  regular (info and above)
#  verbose (all messages)
def setup_log(logger, verbosity=logging.INFO, logfile=None):
    logger.setLevel(logging.DEBUG)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_formatter = logging.Formatter("%(message)s")
    stdout_handler.setFormatter(stdout_formatter)
    stdout_handler.setLevel(verbosity)
    logger.addHandler(stdout_handler)
    if logfile is not None:
        file_handler = logging.FileHandler(logfile)
        file_formatter = logging.Formatter("[%(name)s]: %(message)s")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)


# sets up common parser options
def setup_common_parser(parser):
    verbose_group = parser.add_mutually_exclusive_group()
    verbose_group.add_argument(
        "-v",
        "--verbose",
        action="store_const",
        const=logging.DEBUG,
        dest="verbosity",
        help="Print all output to console.",
    )
    verbose_group.add_argument(
        "-q",
        "--quiet",
        action="store_const",
        const=logging.WARNING,
        dest="verbosity",
        help="Do not print any output to console.",
    )
    parser.set_defaults(verbosity=logging.INFO)


def setup_deploy_parser(parser):
    setup_common_parser(parser)
    parser.add_argument(
        "-l",
        "--logfile",
        default=DEPLOY_LOG,
        help="Where to store the deployment log [default: {}].".format(
            os.path.relpath(DEPLOY_LOG, os.getcwd())
        ),
    )
    parser.add_argument(
        "--no-config",
        action="store_false",
        dest="save_config",
        help="Do not save arguments to a config file.",
    )
    parser.add_argument(
        "-n", "--dry-run", action="store_true", help="Perform a dry run."
    )
    parser.add_argument(
        "-f",
        "--dist-folder",
        default=DIST_PATH,
        dest="dist_folder",
        help="Specifies the folder with the distributables to deploy "
        "[default: {}].".format(os.path.relpath(DIST_PATH, os.getcwd())),
    )


def parse_deploy_credentials(cli_args, required_creds, save_config=True):
    if os.path.isfile(DEPLOY_CONFIG):
        with open(DEPLOY_CONFIG, "r") as conf_file:
            file_dict = json.load(conf_file)
    else:
        file_dict = {}
    cli_dict = vars(cli_args)
    creds = {a: None for a in required_creds}
    creds.update(file_dict)
    creds.update({a: b for a, b in cli_dict.iteritems() if a in required_creds})

    # dropbox
    if "access_token" in required_creds and creds["access_token"] is None:
        if None in (creds.get("app_id"), creds.get("app_secret")):
            creds["app_id"] = raw_input(
                "Please enter the Wrye Bash Dropbox App ID:\n> "
            )
            creds["app_secret"] = raw_input(
                "Please enter the Wrye Bash Dropbox App Secret:\n> "
            )
        auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(
            creds["app_id"], creds["app_secret"]
        )
        authorize_url = auth_flow.start()
        webbrowser.open_new_tab(authorize_url)
        auth_code = raw_input("Enter the authorization code here:\n> ").strip()
        creds["access_token"] = auth_flow.finish(auth_code).access_token

    # nexus
    required = all(elem in ("member_id", "pass_hash", "sid") for elem in required_creds)
    missing = None in (creds.get("member_id"), creds.get("pass_hash"), creds.get("sid"))
    if required and missing:
        with silence():
            cookies = browsercookie.load()
        predicate = lambda x, name: x.domain == ".nexusmods.com" and x.name == name
        creds["member_id"] = next(
            (item.value for item in cookies if predicate(item, "member_id")), None
        )
        creds["pass_hash"] = next(
            (item.value for item in cookies if predicate(item, "pass_hash")), None
        )
        creds["sid"] = next(
            (item.value for item in cookies if predicate(item, "sid")), None
        )
        for key in ("member_id", "pass_hash", "sid"):
            if creds[key] is None:
                print "No {} cookie specified, please enter it now:".format(key)
                creds[key] = raw_input("> ")

    if save_config:
        mkdir(DEPLOY_FOLDER)
        with open(DEPLOY_CONFIG, "w") as conf_file:
            json.dump(creds, conf_file, indent=2, separators=(",", ": "))
    return creds


def convert_bytes(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "{}{}".format(s, size_name[i])


def download_file(url, fpath):
    file_name = os.path.basename(fpath)
    response = urllib2.urlopen(url)
    meta = response.info()
    file_size = int(meta.getheaders("Content-Length")[0])
    converted_size = convert_bytes(file_size)
    file_size_dl = 0
    block_sz = 8192
    with open(fpath, "wb") as dl_file:
        while True:
            buff = response.read(block_sz)
            if not buff:
                break
            file_size_dl += len(buff)
            dl_file.write(buff)
            percentage = file_size_dl * 100.0 / file_size
            status = "{0:>20}  -----  [{3:6.2f}%] {1:>10}/{2}".format(
                file_name, convert_bytes(file_size_dl), converted_size, percentage
            )
            status = status + chr(8) * (len(status) + 1)
            print status,
    print


def run_subprocess(command, logger, **kwargs):
    sp = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **kwargs
    )
    logger.debug("Running command: {}".format(" ".join(command)))
    stdout, _ = sp.communicate()
    if sp.returncode != 0:
        logger.error(stdout)
        raise subprocess.CalledProcessError(sp.returncode, " ".join(command))
    logger.debug("--- COMMAND OUTPUT START ---")
    logger.debug(stdout)
    logger.debug("---  COMMAND OUTPUT END  ---")


def relpath(path):
    return os.path.relpath(path, os.getcwd())


# https://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
def mkdir(path, exists_ok=True):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path) and exists_ok:
            pass
        else:
            raise


# https://stackoverflow.com/a/2829036
@contextlib.contextmanager
def silence():
    save_stdout = sys.stdout
    sys.stdout = io.BytesIO()
    yield
    sys.stdout = save_stdout
