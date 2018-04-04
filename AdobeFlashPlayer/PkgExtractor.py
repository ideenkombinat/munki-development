#!/usr/bin/env python
#
# Copyright 2013 Greg Neagle
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os
import FoundationPlist
import tempfile
import shutil
import subprocess

from autopkglib.DmgMounter import DmgMounter
from autopkglib import Processor, ProcessorError


__all__ = ["PkgExtractor"]


class PkgExtractor(DmgMounter):
    description = ("Extracts the contents of a bundle-style pkg (possibly on a diskimage) to pkgroot.")
    input_variables = {
        "pkg_path": {
            "required": True,
            "description": 
                "Path to a package.",
        },
        "extract_root": {
            "required": True,
            "description": 
                "Path to where the new package root will be created.",
        },
    }
    output_variables = {
    }
    description = __doc__

    def extract(self, pkg_path, extract_root):
        '''Extract package contents to extract_root, preserving intended
         directory structure'''
        info_plist = os.path.join(pkg_path, "Contents/Info.plist")
        archive_path = os.path.join(pkg_path, "Contents/Archive.pax.gz")
        if not os.path.exists(info_plist):
            raise ProcessorError("Info.plist not found in pkg")
        if not os.path.exists(archive_path):
            raise ProcessorError("Archive.pax.gz not found in pkg")
            
        if os.path.exists(extract_root):
            try:
                shutil.rmtree(extract_root)
            except (OSError, IOError), err:
                raise ProcessorError("Failed to remove extract_root: %s" % err)

        try:
            info = FoundationPlist.readPlist(info_plist)
        except FoundationPlist.FoundationPlistException, err:
            raise ProcessorError("Failed to read Info.plist: %s" % err)
            
        install_target = info.get("IFPkgFlagDefaultLocation", "/").lstrip("/")
        extract_path = os.path.join(extract_root, install_target)
        try:
            os.makedirs(extract_path, 0755)
        except (OSError, IOError), err:
            raise ProcessorError("Failed to create extract_path: %s" % err)
        
        # Unpack payload.
        try:
            p = subprocess.Popen(("/usr/bin/ditto",
                                  "-x",
                                  "-z",
                                  archive_path,
                                  extract_path),
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            (out, err) = p.communicate()
        except OSError as err:
            raise ProcessorError(
                "ditto execution failed with error code %d: %s" 
                % (err.errno, err.strerror))
        if p.returncode != 0:
            raise ProcessorError("Unpacking payload failed: %s" % err)

    def main(self):
        # Check if we're trying to read something inside a dmg.
        (dmg_path, dmg, dmg_source_path) = self.env[
            'pkg_path'].partition(".dmg/")
        dmg_path += ".dmg"
        try:
            if dmg:
                # Mount dmg and copy path inside.
                mount_point = self.mount(dmg_path)
                pkg_path = os.path.join(mount_point, dmg_source_path)
            else:
                # just use the given path
                pkg_path = self.env['pkg_path']
            self.extract(pkg_path, self.env["extract_root"])
            
        finally:
            if dmg:
                self.unmount(dmg_path)

if __name__ == '__main__':
    processor = PkgExtractor()
    processor.execute_shell()