cmake_minimum_required(VERSION 3.16)
# Single source of the firmware version; reported to the server as
# X-Fw-Version via the app descriptor.
#
# Bump this for every image that leaves the bench. Phase 1 (this plan)
# has no server-side release tracking yet - that arrives with the real
# rendering server in Phase 2 - so for now this is just a human-readable
# marker of which phase produced the binary.
set(PROJECT_VER "0.1.0-p1")
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(inkframe)
