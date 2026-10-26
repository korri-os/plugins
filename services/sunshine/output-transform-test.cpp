#include "kms_output_transform.h"

#include <array>
#include <cassert>
#include <cmath>
#include <iostream>
#include <string>

int main() {
  // wl_output.transform (wayland.xml): counter-clockwise in Cartesian
  // coordinates, with a vertical-axis flip BEFORE the rotation. GL texture
  // row zero is the bottom row; GetTextureSubImage preserves that row order.
  // Thus ABC/DEF below is labelled from the bottom, not a top-left diagram.
  constexpr int width = 3, height = 2;
  const std::string source = "ABCDEF";
  const std::array<std::string, 8> expected = {
      "ABCDEF", "DAEBFC", "FEDCBA", "CFBEAD",
      "CBAFED", "FCEBDA", "DEFABC", "ADBECF",
  };
  for (int value = 0; value < 8; ++value) {
    auto transform = platf::kms::output_transform(value);
    assert(transform);
    const auto &t = *transform;
    auto [out_width, out_height] = t.size(width, height);
    assert(out_width == (value % 2 ? height : width));
    assert(out_height == (value % 2 ? width : height));
    std::string image(source.size(), '?');
    for (int y = 0; y < out_height; ++y) {
      for (int x = 0; x < out_width; ++x) {
        // Evaluate the exact affine coefficients embedded in the fragment
        // shader, at pixel centres, with GL_NEAREST sampling.
        double u = (x + 0.5) / out_width, v = (y + 0.5) / out_height;
        int sx = int(std::floor((t.xx * u + t.xy * v + t.x0) * width));
        int sy = int(std::floor((t.yx * u + t.yy * v + t.y0) * height));
        assert(sx >= 0 && sx < width && sy >= 0 && sy < height);
        image[y * out_width + x] = source[sy * width + sx];
      }
    }
    assert(image == expected[value]);
    // Independent Wayland definition: flip first, then rotate CCW in Y-up
    // coordinates. Verify every labelled source pixel, not just the corners.
    for (int sy = 0; sy < height; ++sy) {
      for (int sx = 0; sx < width; ++sx) {
        int x = value >= 4 ? width - 1 - sx : sx, y = sy;
        int w = width, h = height;
        for (int turn = 0; turn < value % 4; ++turn) {
          int next_x = h - 1 - y;
          y = x;
          x = next_x;
          std::swap(w, h);
        }
        assert(image[y * out_width + x] == source[sy * width + sx]);
      }
    }
    // Cursor pixels use the production inverse sampler. Include clipped
    // cursor positions on every edge; clipping must agree with image bounds.
    for (int sy = -2; sy < height + 2; ++sy) {
      for (int sx = -2; sx < width + 2; ++sx) {
        auto [x, y] = t.pixel(sx, sy, width, height);
        bool visible = sx >= 0 && sx < width && sy >= 0 && sy < height;
        assert(visible ==
               (x >= 0 && x < out_width && y >= 0 && y < out_height));
        if (visible) {
          assert(image[y * out_width + x] == source[sy * width + sx]);
        }
      }
    }
    std::cout << value << ": " << image << " cursor agrees\n";
  }
  assert(!platf::kms::output_transform(-1));
  assert(!platf::kms::output_transform(8));
  std::cout << "All eight Wayland output transforms passed\n";
}
