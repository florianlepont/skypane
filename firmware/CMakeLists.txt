# SPDX-FileCopyrightText: 2026 YODE PTE LTD
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
# Modified from FlightPortrait (github.com/flightportrait/frame) for
# SkyPane; the changes are listed in firmware/VENDOR.md.
cmake_minimum_required(VERSION 3.16)
# PROJECT_VER, reported to the server as X-Fw-Version via the app
# descriptor, is normally passed in by build.sh as -DPROJECT_VER=<git
# describe>: the container has no .git to run git describe itself (only
# firmware/ is mounted), so the host resolves it and hands it in.
if(NOT DEFINED PROJECT_VER)
    set(PROJECT_VER "0.0.0-nogit")
endif()
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(skypane)
