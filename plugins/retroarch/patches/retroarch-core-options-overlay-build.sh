#!/usr/bin/env bash
# Build-host only. Real option manager, native parser, filesystem and list code.
set -euo pipefail
source_root="$1"
probe="$2"
output="$3"
common="$source_root/libretro-common"
"${CC:-cc}" -std=gnu99 -O2 -Wall -Wextra -Werror -Wno-unused-parameter -Wno-implicit-fallthrough \
  -ffunction-sections -fdata-sections -I. -I"$source_root" -I"$common/include" \
  "$probe" core_option_manager.c "$source_root/msg_hash.c" "$source_root/intl/msg_hash_us.c" "$source_root/verbosity.c" \
  "$common/lists/string_list.c" "$common/lists/nested_list.c" \
  "$common/file/config_file.c" "$common/file/file_path.c" "$common/file/file_path_io.c" \
  "$common/streams/file_stream.c" "$common/streams/file_stream_transforms.c" \
  "$common/vfs/vfs_implementation.c" "$common/string/stdstring.c" \
  "$common/compat/compat_strl.c" "$common/compat/compat_posix_string.c" \
  "$common/encodings/encoding_utf.c" "$common/time/rtime.c" \
  -Wl,--gc-sections -o "$output"
