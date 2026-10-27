/* An original, content-free deterministic core for frontend protocol checks. */
#include <libretro.h>
#include <stdint.h>
#include <string.h>

static retro_environment_t environment;
static retro_video_refresh_t video;
static retro_audio_sample_batch_t audio;
static retro_input_poll_t poll_input;
static retro_log_printf_t log_message;
static uint32_t frame;

void retro_set_environment(retro_environment_t cb) { environment = cb; }
void retro_set_video_refresh(retro_video_refresh_t cb) { video = cb; }
void retro_set_audio_sample(retro_audio_sample_t cb) { (void)cb; }
void retro_set_audio_sample_batch(retro_audio_sample_batch_t cb) { audio = cb; }
void retro_set_input_poll(retro_input_poll_t cb) { poll_input = cb; }
void retro_set_input_state(retro_input_state_t cb) { (void)cb; }
void retro_init(void) {
   struct retro_log_callback logging;
   if (environment(RETRO_ENVIRONMENT_GET_LOG_INTERFACE, &logging))
      log_message = logging.log;
}
void retro_deinit(void) {}
unsigned retro_api_version(void) { return RETRO_API_VERSION; }
void retro_get_system_info(struct retro_system_info *info) {
   memset(info, 0, sizeof(*info));
   info->library_name = "Korri netplay check";
   info->library_version = "1";
   info->valid_extensions = "bin";
}
void retro_get_system_av_info(struct retro_system_av_info *info) {
   memset(info, 0, sizeof(*info));
   info->geometry.base_width = info->geometry.max_width = 16;
   info->geometry.base_height = info->geometry.max_height = 16;
   info->geometry.aspect_ratio = 1.0f;
   info->timing.fps = 60.0;
   info->timing.sample_rate = 48000.0;
}
void retro_set_controller_port_device(unsigned port, unsigned device) {
   (void)port; (void)device;
}
void retro_reset(void) { frame = 0; }
void retro_run(void) {
   uint16_t pixels[16 * 16] = {0};
   int16_t samples[800 * 2] = {0};
   poll_input();
   frame++;
   pixels[0] = (uint16_t)frame;
   video(pixels, 16, 16, 16 * sizeof(uint16_t));
   audio(samples, 800);
   if (log_message && frame % 120 == 0)
      log_message(RETRO_LOG_INFO, "netplay-check frame=%u\n", frame);
}
size_t retro_serialize_size(void) { return sizeof(frame); }
bool retro_serialize(void *data, size_t size) {
   if (size != sizeof(frame)) return false;
   memcpy(data, &frame, size);
   return true;
}
bool retro_unserialize(const void *data, size_t size) {
   if (size != sizeof(frame)) return false;
   memcpy(&frame, data, size);
   if (log_message) log_message(RETRO_LOG_INFO, "netplay-check synced=%u\n", frame);
   return true;
}
void retro_cheat_reset(void) {}
void retro_cheat_set(unsigned index, bool enabled, const char *code) {
   (void)index; (void)enabled; (void)code;
}
bool retro_load_game(const struct retro_game_info *game) { (void)game; return true; }
bool retro_load_game_special(unsigned type, const struct retro_game_info *info, size_t n) {
   (void)type; (void)info; (void)n; return false;
}
void retro_unload_game(void) {}
unsigned retro_get_region(void) { return RETRO_REGION_NTSC; }
void *retro_get_memory_data(unsigned id) { (void)id; return NULL; }
size_t retro_get_memory_size(unsigned id) { (void)id; return 0; }
