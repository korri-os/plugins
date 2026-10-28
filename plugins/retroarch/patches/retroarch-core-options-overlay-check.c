/* Build-host proof using the complete upstream option manager and parser,
 * plus extracted native runloop selection. Only runtime facts (paths and
 * loaded core identity) are provided here; selection is not reimplemented. */
#define _GNU_SOURCE
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <file/file_path.h>
#include <string/stdstring.h>
#include "core_option_manager.h"
#include "msg_hash.h"
#include "verbosity.h"

#define RUNLOOP_FLAG_GAME_OPTIONS_ACTIVE (1 << 10)
#define RUNLOOP_FLAG_FOLDER_OPTIONS_ACTIVE (1 << 11)
#define FILE_PATH_CORE_OPTIONS_CONFIG "retroarch-core-options.cfg"
enum { RARCH_PATH_BASENAME, RARCH_PATH_CONFIG, RARCH_PATH_CORE_OPTIONS };
enum { APPLICATION_SPECIAL_DIRECTORY_CONFIG };
/* The real selector only reads these runtime facts. */
typedef struct {
   struct { struct { const char *library_name; } info; } system;
   unsigned flags;
} runloop_state_t;
static runloop_state_t runloop_state;
static char paths[3][PATH_MAX_LENGTH];
static char config_directory[PATH_MAX_LENGTH];
static const char *path_get(unsigned id) { return paths[id]; }
static bool path_is_empty(unsigned id) { return !*paths[id]; }
static void path_set(unsigned id, const char *value)
{
   strlcpy(paths[id], value, sizeof(paths[id]));
}
static void fill_pathname_application_special(char *out, size_t size, unsigned id)
{
   assert(id == APPLICATION_SPECIAL_DIRECTORY_CONFIG);
   strlcpy(out, config_directory, size);
}
#include "core-options-selection.h"

static const struct retro_variable variables[] = {
   { "melonds_screen_layout", "Layout; Top/Bottom|Left/Right|Top Only|Bottom Only" },
   { "melonds_screen_gap", "Gap; 0|64" },
   { "melonds_threaded_renderer", "Threads; disabled|enabled" },
   { "melonds_touch_mode", "Touch mode; Mouse|Touch" },
   { NULL, NULL },
};
static struct retro_core_option_v2_definition definitions[] = {
   { .key = "melonds_screen_layout", .desc = "Layout", .values = {
      { "Top/Bottom", NULL }, { "Left/Right", NULL },
      { "Top Only", NULL }, { "Bottom Only", NULL }, { NULL, NULL },
   }, .default_value = "Top/Bottom" },
   { .key = "melonds_screen_gap", .desc = "Gap", .values = {
      { "0", NULL }, { "64", NULL }, { NULL, NULL },
   }, .default_value = "0" },
   { .key = "melonds_threaded_renderer", .desc = "Threads", .values = {
      { "disabled", NULL }, { "enabled", NULL }, { NULL, NULL },
   }, .default_value = "disabled" },
   { .key = "melonds_touch_mode", .desc = "Touch mode", .values = {
      { "Mouse", NULL }, { "Touch", NULL }, { NULL, NULL },
   }, .default_value = "Mouse" },
   { .key = NULL },
};
static const struct retro_core_options_v2 options = { NULL, definitions };

static void write_text(const char *path, const char *text)
{
   FILE *file = fopen(path, "wb");
   assert(file);
   assert(fputs(text, file) >= 0);
   assert(fclose(file) == 0);
}
static void expect_value(config_file_t *conf, const char *key, const char *expected)
{
   struct config_entry_list *entry = config_get_entry(conf, key);
   if (!expected) assert(!entry);
   else assert(entry && !strcmp(entry->value, expected));
}
static void verify_saved(const char *path, bool overlay, unsigned native_kind)
{
   config_file_t *conf = config_file_new_from_path_to_string(path);
   assert(conf);
   /* Native_kind also tests missing and invalid native values, which must
    * not become persisted defaults (or the launch's layout). */
   expect_value(conf, "melonds_screen_layout", overlay
         ? (native_kind == 1 ? NULL : native_kind == 2 ? "invalid-native" : "Bottom Only")
         : "Left/Right");
   expect_value(conf, "melonds_screen_gap", overlay
         ? (native_kind == 1 ? NULL : native_kind == 2 ? "invalid-native" : "64")
         : "64");
   expect_value(conf, "melonds_threaded_renderer", "disabled");
   expect_value(conf, "melonds_touch_mode", overlay
         ? (native_kind == 1 ? NULL : native_kind == 2 ? "invalid-native" : "Mouse")
         : "Mouse");
   config_file_free(conf);
   /* Include exact saved bytes in the no-overlay differential proof. */
   FILE *file = fopen(path, "rb");
   int byte;
   assert(file);
   while ((byte = fgetc(file)) != EOF) putchar(byte);
   fclose(file);
}

static void scenario(unsigned route, bool legacy, bool overlay,
      unsigned native_kind, unsigned layout)
{
   char game[PATH_MAX_LENGTH], folder[PATH_MAX_LENGTH], per_core[PATH_MAX_LENGTH];
   char custom[PATH_MAX_LENGTH], global[PATH_MAX_LENGTH], overlay_path[PATH_MAX_LENGTH];
   const char *chosen;
   const char *native = native_kind == 1
         ? "melonds_threaded_renderer = \"enabled\"\n"
         : native_kind == 2
         ? "melonds_screen_layout = \"invalid-native\"\nmelonds_screen_gap = \"invalid-native\"\nmelonds_touch_mode = \"invalid-native\"\nmelonds_threaded_renderer = \"enabled\"\n"
         : "melonds_screen_layout = \"Bottom Only\"\nmelonds_screen_gap = \"64\"\nmelonds_touch_mode = \"Mouse\"\nmelonds_threaded_renderer = \"enabled\"\n";
   const char *lower = "melonds_screen_layout = \"Top Only\"\nmelonds_screen_gap = \"0\"\nmelonds_touch_mode = \"Touch\"\nmelonds_threaded_renderer = \"disabled\"\n";
   char text[512];
   core_option_manager_t *manager;
   config_file_t *menu;
   fill_pathname_join_special(game, config_directory, "melonDS/game.opt", sizeof(game));
   fill_pathname_join_special(folder, config_directory, "melonDS/folder.opt", sizeof(folder));
   fill_pathname_join_special(per_core, config_directory, "melonDS/melonDS.opt", sizeof(per_core));
   fill_pathname_resolve_relative(custom, paths[RARCH_PATH_CONFIG], "custom.opt", sizeof(custom));
   fill_pathname_resolve_relative(global, paths[RARCH_PATH_CONFIG], FILE_PATH_CORE_OPTIONS_CONFIG, sizeof(global));
   fill_pathname_resolve_relative(overlay_path, paths[RARCH_PATH_CONFIG], "launch.opt", sizeof(overlay_path));
   /* Removing fixture files, never shared data. */
   unlink(game); unlink(folder); unlink(per_core); unlink(custom); unlink(global);
   write_text(custom, lower);
   write_text(global, lower);
   if (route <= 2) write_text(per_core, lower);
   if (route <= 1) write_text(folder, lower);
   if (route == 0) write_text(game, lower);
   chosen = route == 0 ? game : route == 1 ? folder : route == 2 ? per_core
         : (route == 3 || route == 5) ? custom : global;
   write_text(chosen, native);
   snprintf(text, sizeof(text), "melonds_screen_layout = \"%s\"\nmelonds_screen_gap = \"0\"\nmelonds_touch_mode = \"Touch\"\n",
         definitions[0].values[layout].value);
   write_text(overlay_path, text);
   if (overlay) assert(setenv("KORRI_RETROARCH_CORE_OPTIONS_OVERLAY", overlay_path, 1) == 0);
   else assert(unsetenv("KORRI_RETROARCH_CORE_OPTIONS_OVERLAY") == 0);
   runloop_state.flags = 0;
   paths[RARCH_PATH_CORE_OPTIONS][0] = '\0';
   /* Routes 5/6 initialise a missing per-core file from custom/global.
    * The runloop helper takes !global_core_options as its second boolean. */
   bool per_core_enabled = route <= 2 || route >= 5;
   const char *configured = (route == 3 || route == 5) ? custom : "";
   manager = legacy
         ? runloop_init_core_variables(true, per_core_enabled, configured, variables)
         : runloop_init_core_options(false, true, per_core_enabled, configured, &options);
   assert(manager);
   assert(!strcmp(manager->conf_path, route >= 5 ? per_core : chosen));
   assert((runloop_state.flags & RUNLOOP_FLAG_GAME_OPTIONS_ACTIVE) == (route == 0 ? RUNLOOP_FLAG_GAME_OPTIONS_ACTIVE : 0));
   assert((runloop_state.flags & RUNLOOP_FLAG_FOLDER_OPTIONS_ACTIVE) == (route == 1 ? RUNLOOP_FLAG_FOLDER_OPTIONS_ACTIVE : 0));
   assert(!strcmp(core_option_manager_get_val(manager, 0), overlay
         ? definitions[0].values[layout].value : native_kind ? "Top/Bottom" : "Bottom Only"));
   assert(!strcmp(core_option_manager_get_val(manager, 1), overlay || native_kind ? "0" : "64"));
   assert(!strcmp(core_option_manager_get_val(manager, 2), "enabled"));
   assert(!strcmp(core_option_manager_get_val(manager, 3), overlay ? "Touch" : "Mouse"));
   /* Exercise menu edits, followed by both menu Save As and exit flush.
    * Overlay keys must retain their ORIGINAL values in every destination. */
   core_option_manager_set_val(manager, 0, 1, false);
   core_option_manager_set_val(manager, 1, 1, false);
   core_option_manager_set_val(manager, 2, 0, false);
   core_option_manager_set_val(manager, 3, 0, false);
   menu = config_file_new_alloc();
   assert(menu);
   core_option_manager_flush(manager, menu);
   assert(config_file_write(menu, "menu-save.opt", true));
   config_file_free(menu);
   printf("route=%u legacy=%u kind=%u layout=%u menu\n", route, legacy, native_kind, layout);
   verify_saved("menu-save.opt", overlay, native_kind);
   core_option_manager_flush(manager, manager->conf);
   assert(config_file_write(manager->conf, manager->conf_path, true));
   printf("exit\n");
   verify_saved(manager->conf_path, overlay, native_kind);
   /* Overlay file is read-only input. Neither save path may rewrite it. */
   config_file_t *overlay_conf = config_file_new_from_path_to_string(overlay_path);
   expect_value(overlay_conf, "melonds_screen_layout", definitions[0].values[layout].value);
   expect_value(overlay_conf, "melonds_screen_gap", "0");
   expect_value(overlay_conf, "melonds_touch_mode", "Touch");
   config_file_free(overlay_conf);
   core_option_manager_free(manager);
   assert(unsetenv("KORRI_RETROARCH_CORE_OPTIONS_OVERLAY") == 0);
   /* A later manager in the same process sees only the native values. */
   manager = core_option_manager_new(per_core_enabled && route >= 5 ? per_core : chosen, NULL, &options, false);
   assert(manager);
   if (overlay && native_kind == 0)
   {
      assert(!strcmp(core_option_manager_get_val(manager, 0), "Bottom Only"));
      assert(!strcmp(core_option_manager_get_val(manager, 3), "Mouse"));
   }
   core_option_manager_free(manager);
}

int main(int argc, char **argv)
{
   assert(argc == 2);
   bool overlay = !strcmp(argv[1], "overlay");
   assert(overlay || !strcmp(argv[1], "native"));
   char cwd[PATH_MAX_LENGTH];
   assert(getcwd(cwd, sizeof(cwd)));
   fill_pathname_join_special(config_directory, cwd, "config", sizeof(config_directory));
   fill_pathname_join_special(paths[RARCH_PATH_CONFIG], cwd, "retroarch.cfg", sizeof(paths[0]));
   fill_pathname_join_special(paths[RARCH_PATH_BASENAME], cwd, "roms/folder/game", sizeof(paths[0]));
   char core_directory[PATH_MAX_LENGTH];
   fill_pathname_join_special(core_directory, config_directory, "melonDS", sizeof(core_directory));
   assert(path_mkdir(core_directory));
   runloop_state.system.info.library_name = "melonDS";
   for (unsigned route = 0; route < 7; route++)
      for (unsigned legacy = 0; legacy < 2; legacy++)
         for (unsigned kind = 0; kind < 3; kind++)
            for (unsigned layout = 0; layout < 4; layout++)
               scenario(route, legacy, overlay, kind, layout);
   if (overlay)
   {
      /* Invalid or unreadable overlays fail explicitly, not silently. */
      assert(setenv("KORRI_RETROARCH_CORE_OPTIONS_OVERLAY", "missing.opt", 1) == 0);
      assert(!core_option_manager_new(FILE_PATH_CORE_OPTIONS_CONFIG, NULL, &options, false));
      write_text("invalid.opt", "melonds_screen_layout = \"invalid-layout\"\n");
      assert(setenv("KORRI_RETROARCH_CORE_OPTIONS_OVERLAY", "invalid.opt", 1) == 0);
      assert(!core_option_manager_new(FILE_PATH_CORE_OPTIONS_CONFIG, NULL, &options, false));
   }
   return 0;
}
