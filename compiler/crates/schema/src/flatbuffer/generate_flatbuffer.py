#! /usr/bin/env python3
# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# Unfortunately, `flatc` doesn't output Rust 2018 conformant code which poses a
# problem when we want to embed it within a crate that requires it.
# The script here runs `flatc`, the flatbuffer compiler and then patches a bunch
# of code.
# Not proud of this...

import subprocess
import re

flatc_version = subprocess.check_output(["flatc", "--version"], text=True).strip()

subprocess.run(["flatc", "--rust", "graphqlschema.fbs"], check=True)

with open("graphqlschema_generated.rs") as f:
    content = f.read()

# add header
content = (
    """/*
 * This file is generated, do not modify directly.
 *
 * Generated by:
 *   ./generate_flatbuffer.py
 *
 * Using:
 *   {}
 *
 * NOTE: The script requires `flatc` in the path which can be installed
 *       using `brew install flatbuffers` or similar.
 *
 * \x40generated
 */

#![allow(unused_imports, dead_code)]
""".format(
        flatc_version
    )
    + content
)
content = content.replace(
    "// automatically generated by the FlatBuffers compiler, do not modify\n", ""
)

# add explicit unnamed lifetimes required by Rust 2018
type_names = [
    "FBType",
    "FBTypeMap",
    "FBDirectiveMap",
    "FBDirective",
    "FBTypeReference",
    "FBConstValue",
    "FBObjectValue",
    "FBListValue",
]
for type_name in type_names:
    content = content.replace(type_name + ">", type_name + "<'_>>")
    content = content.replace(type_name + ")", type_name + "<'_>)")
content = content.replace(
    "flatbuffers::Vector<flatbuffers", "flatbuffers::Vector<'_, flatbuffers"
)

# fixup unused imports and deprecated `extern crate`
content = content.replace("use self::flatbuffers::EndianScalar;\n", "")
content = content.replace("extern crate flatbuffers;", "use flatbuffers;")

# fixup lifetime warning that this lifetime can be inferred
content = content.replace("<'a: 'b, 'b>", "<'a, 'b>")

# add Clone to type, I think this was a manual add at some point
content = content.replace(
    "pub struct FBTypeArgs {", "#[derive(Copy, Clone)]\n    pub struct FBTypeArgs {"
)

# drop excessive empty lines
content = re.sub("\n{3,}", "\n\n", content)

with open("graphqlschema_generated.rs", "w") as f:
    f.write(content)
