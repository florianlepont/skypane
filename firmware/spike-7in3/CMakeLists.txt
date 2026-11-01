# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
# Trial 7.3" driver project. It builds on its own, is not part of the
# production firmware, and is never flashed.
cmake_minimum_required(VERSION 3.16)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(skypane_spike_7in3)
