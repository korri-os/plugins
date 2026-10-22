#include "nv12.h"

#include <algorithm>
#include <cstdio>
#include <cstdlib>

static void require(bool ok) {
  if (!ok) {
    std::fprintf(stderr, "row-pair staging regression failed\n");
    std::exit(1);
  }
}

int main() {
  for (const auto dimensions : {std::pair<int, int> {64, 32}, {640, 480}, {18, 14}}) {
    int width = dimensions.first, height = dimensions.second;
    for (int padding : {0, 32}) {
      int pitch = width * 4 + padding, output_pitch = width + padding;
      std::vector<std::uint8_t> source(size_t(pitch) * height + 7);
      for (size_t i = 0; i < source.size(); ++i) {
        source[i] = (i * 17 + i / 13) % 251;
      }
      auto original = source;
      std::vector<std::uint8_t> staged(size_t(output_pitch) * height * 3 / 2, 0xa5);
      auto reference = staged;
      std::vector<std::uint8_t> scratch;
      require(kms::stage_nv12(source.data() + 7, pitch, width, height, staged.data(), output_pitch, staged.data() + size_t(output_pitch) * height, output_pitch, scratch) == 0);
      require(libyuv::ARGBToNV12(source.data() + 7, pitch, reference.data(), output_pitch, reference.data() + size_t(output_pitch) * height, output_pitch, width, height) == 0);
      require(staged == reference);
      require(source == original);
      require(scratch.size() == size_t(width) * 8);
      auto *allocation = scratch.data();
      require(kms::stage_nv12(source.data() + 7, pitch, width, height, staged.data(), output_pitch, staged.data() + size_t(output_pitch) * height, output_pitch, scratch) == 0);
      require(scratch.data() == allocation);
      require(staged == reference);
      require(kms::stage_nv12(nullptr, pitch, width, height, staged.data(), output_pitch, staged.data(), output_pitch, scratch) < 0);
      require(kms::stage_nv12(source.data(), pitch, width - 1, height, staged.data(), output_pitch, staged.data(), output_pitch, scratch) < 0);
      require(kms::stage_nv12(source.data(), pitch, width, height - 1, staged.data(), output_pitch, staged.data(), output_pitch, scratch) < 0);
      require(kms::stage_nv12(source.data(), width * 4 - 1, width, height, staged.data(), output_pitch, staged.data(), output_pitch, scratch) < 0);
      require(kms::stage_nv12(source.data(), pitch, width, height, staged.data(), width - 1, staged.data(), output_pitch, scratch) < 0);
    }
  }
  std::puts("PASS row-pair staging: exact libyuv pixels, padding, unaligned source, input unchanged, bounds, owned scratch");
}
