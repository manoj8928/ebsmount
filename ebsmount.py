# Copyright (c) 2010 Alon Swartz <alon@turnkeylinux.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of 
# the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
from os.path import *

import pwd

import udevdb
from executil import system
from utils import config, log, is_mounted, mount

def _run_hooks(dir, mountpath, logfile):
    for file in os.listdir(dir):
        fpath = join(dir, file)
        if not os.access(fpath, os.X_OK):
            log("* skipping '%s', not executable" % fpath)
            continue

        if not os.stat(fpath).st_uid == 0 and not os.stat(fpath).st_gid == 0:
            log("* skipping '%s', not owned root:root" % fpath)
            continue

        log("* executing: %s" % fpath)

        os.environ['HOME'] = pwd.getpwuid(os.getuid()).pw_dir
        os.environ['MOUNTPOINT'] = mountpath
        system("/bin/bash --login -c '%s' 2>&1 | tee -a %s" % (fpath, logfile))

def ebsmount_add(devname, mountdir):
    """ebs device attached"""

    matching_devices = []
    for device in udevdb.query():
        if device.name.startswith(basename(devname)):
            matching_devices.append(device)

    for device in matching_devices:
        devpath = join('/dev', device.name)
        mountpath = join(mountdir, device.env.get('ID_FS_UUID', devpath[-1])[:6])
        mountoptions = ",".join(config.mountoptions.split())
        hookspath = join(mountpath, ".ebsmount")

        filesystem = device.env.get('ID_FS_TYPE', None)
        if not filesystem:
            log(devname, "could not identify filesystem: %s" % devpath)
            continue

        if not filesystem in config.filesystems.split():
            log(devname, "filesystem (%s) not supported: %s" % (filesystem,devpath))
            continue

        if is_mounted(devpath):
            log(devname, "already mounted: %s" % devpath)
            continue

        mount(devpath, mountpath, mountoptions)
        log(devname, "mounted %s %s (%s)" % (devpath, mountpath, mountoptions))

        if config.runhooks and exists(hookspath):
            _run_hooks(hookspath, mountpath, config.logfile)

def ebsmount_remove(devname, mountdir):
    """ebs device detached"""

    mounted = False
    for d in os.listdir(mountdir):
        path = join(mountdir, d)
        if is_mounted(path):
            mounted = True
            continue

        os.rmdir(path)

    if not mounted:
        os.rmdir(mountdir)

