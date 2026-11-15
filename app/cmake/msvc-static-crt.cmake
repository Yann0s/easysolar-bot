# llama.cpp active CMP0091 : sans cette ligne, CMake impose /MD et ignore le /MT passé par le crate cmake.
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded")
