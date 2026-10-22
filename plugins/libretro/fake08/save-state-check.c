/* Exercise the real libretro ABI, including RetroArch's pre-first-run restore.
 * Use PR #288's Lua-only n counter, observed via its poke into serialized RAM.
 * No display, audio device, input device or private VM symbols are needed.
 */
#include "libretro.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void require(bool condition, const char *message) {
  if (!condition) {
    fprintf(stderr, "harness error: %s\n", message);
    exit(2);
  }
}

static bool environment(unsigned command, void *data) {
  switch (command) {
  case RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY:
  case RETRO_ENVIRONMENT_GET_SAVE_DIRECTORY:
    *(const char **)data = ".";
    return true;
  case RETRO_ENVIRONMENT_SET_PIXEL_FORMAT:
    return *(enum retro_pixel_format *)data == RETRO_PIXEL_FORMAT_RGB565;
  case RETRO_ENVIRONMENT_GET_CAN_DUPE:
    *(bool *)data = false;
    return true;
  default:
    return false;
  }
}

static void video(const void *data, unsigned width, unsigned height,
                  size_t pitch) {
  require(data && width == 128 && height == 128 && pitch == 256,
          "invalid video frame");
}

static void audio(int16_t left, int16_t right) {
  (void)left;
  (void)right;
}
static size_t audio_batch(const int16_t *data, size_t frames) {
  (void)data;
  return frames;
}
static void poll(void) {}
static int16_t input(unsigned port, unsigned device, unsigned index,
                     unsigned id) {
  (void)port;
  (void)device;
  (void)index;
  (void)id;
  return 0;
}

static unsigned char *read_file(const char *path, size_t *size) {
  FILE *file = fopen(path, "rb");
  require(file != NULL, "open input");
  require(fseek(file, 0, SEEK_END) == 0, "seek input");
  long length = ftell(file);
  require(length > 0, "empty input");
  *size = (size_t)length;
  rewind(file);
  unsigned char *data = malloc(*size);
  require(data != NULL, "allocate input");
  require(fread(data, 1, *size, file) == *size, "read input");
  require(fclose(file) == 0, "close input");
  return data;
}

static void run_frames(unsigned count) {
  for (unsigned i = 0; i < count; ++i)
    retro_run();
}

/* The pinned core exposes no memory through retro_get_memory_data. Its f8\0\1
 * state stores native size_t lengths, then Lua, then PicoRam. Read only after
 * validating the lengths. This also works on the aarch64 CI runner.
 */
static unsigned counter(const unsigned char *state, size_t size) {
  size_t lua_size, ram_size;
  require(size >= 4 + sizeof(size_t), "short state header");
  require(memcmp(state, "f8\0\1", 4) == 0, "state version");
  memcpy(&lua_size, state + 4, sizeof(lua_size));
  size_t offset = 4 + sizeof(size_t);
  require(lua_size <= size - offset, "Lua state bounds");
  offset += lua_size;
  require(sizeof(size_t) <= size - offset, "short RAM header");
  memcpy(&ram_size, state + offset, sizeof(ram_size));
  offset += sizeof(size_t);
  require(ram_size <= size - offset && ram_size > 0x4300, "RAM state bounds");
  return state[offset + 0x4300];
}

int main(int argc, char **argv) {
  require(argc == 5,
          "usage: harness CART save|running|autoload|reload STATE memory|path");
  const char *mode = argv[2];
  require(strcmp(mode, "save") == 0 || strcmp(mode, "running") == 0 ||
              strcmp(mode, "autoload") == 0 || strcmp(mode, "reload") == 0,
          "unknown mode");
  bool memory = strcmp(argv[4], "memory") == 0;
  require(memory || strcmp(argv[4], "path") == 0, "unknown loading mode");
  size_t cart_size;
  unsigned char *cart = read_file(argv[1], &cart_size);
  struct retro_game_info game = {argv[1], memory ? cart : NULL,
                                 memory ? cart_size : 0, NULL};
  retro_set_environment(environment);
  retro_set_video_refresh(video);
  retro_set_audio_sample(audio);
  retro_set_audio_sample_batch(audio_batch);
  retro_set_input_poll(poll);
  retro_set_input_state(input);
  retro_init();
  require(retro_load_game(&game), "load cart");

  size_t size = retro_serialize_size();
  unsigned char *state;
  if (strcmp(mode, "autoload") == 0) {
    size_t file_size;
    state = read_file(argv[3], &file_size);
    require(file_size == size, "state size differs between runs");
    /* No retro_run here: this is RetroArch's savestate_auto_load order. */
  } else {
    run_frames(62);
    state = calloc(1, size);
    require(state != NULL, "allocate state");
    require(retro_serialize(state, size), "serialize");
  }
  unsigned saved = counter(state, size);
  require(saved > 10 && saved < 100, "cart counter did not advance");
  size_t lua_size;
  memcpy(&lua_size, state + 4, sizeof(lua_size));
  printf("%s/%s: saved counter=%u, Lua bytes=%zu\n", mode, argv[4], saved,
         lua_size);

  int result = 0;
  if (strcmp(mode, "save") == 0) {
    FILE *file = fopen(argv[3], "wb");
    require(file != NULL, "open saved state");
    require(fwrite(state, 1, size, file) == size, "write saved state");
    require(fclose(file) == 0, "close saved state");
  } else {
    if (strcmp(mode, "running") == 0)
      run_frames(60);
    if (strcmp(mode, "reload") == 0) {
      retro_unload_game();
      require(retro_load_game(&game), "reload cart");
    }
    require(retro_unserialize(state, size), "unserialize");
    unsigned char *observed = calloc(1, size);
    require(observed != NULL, "allocate observed state");
    for (unsigned step = 1; step <= 3; ++step) {
      /* The fixture runs at 30fps; the libretro frontend runs at 60fps. */
      run_frames(2);
      require(retro_serialize(observed, size), "serialize resumed state");
      unsigned actual = counter(observed, size);
      printf("%s/%s: resumed counter=%u, expected=%u\n", mode, argv[4], actual,
             saved + step);
      if (actual != saved + step) {
        fprintf(stderr,
                "FAIL: Lua counter did not continue from saved value\n");
        result = 1;
        break;
      }
    }
    free(observed);
  }
  retro_unload_game();
  retro_deinit();
  free(state);
  free(cart);
  return result;
}
