add_library(Libuuid::Libuuid UNKNOWN IMPORTED)
set_target_properties(Libuuid::Libuuid PROPERTIES
  IMPORTED_LOCATION "@uuidLib@/lib/libuuid.so"
  INTERFACE_INCLUDE_DIRECTORIES "@uuidDev@/include"
)
set(Libuuid_FOUND TRUE)
