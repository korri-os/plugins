// Lantern Hollow private authoring command (NOT part of any published build).
// Included at the end of src/zq/commands.cpp.
//   zeditor -headless -lh-build <base.qst> <recipe.json> <out.qst>
// Loads a base quest, blanks every stock name/media table, applies the recipe,
// and saves through the engine's own save_quest().
#include <nlohmann/json.hpp>
#include "tiles.h"
#include "items.h"
#include "sprite_data.h"
#include "zcsfx.h"
#include "advanced_music.h"
#include "subscr.h"
#include "new_subscr.h"
#include "zinfo.h"
#include "hero_tiles.h"
#include "core/combo.h"
#include "core/mapscr.h"
#include "core/msgstr.h"
#include "core/initdata.h"
#include "core/misctypes.h"
#include "core/cpool.h"
#include "zq/zq_misc.h"

namespace lh {
using json = nlohmann::json;

static void die(std::string const& m) { printf("lh-build: %s\n", m.c_str()); zq_exit(1); }

static void scrub()
{
	clear_tiles(newtilebuf);
	for (auto& c : combobuf) c.clear();
	for (auto& s : TheMaps) s = mapscr();
	for (auto& mi : map_infos) mi = map_info();
	for (auto& a : combo_aliases) a = combo_alias();
	for (auto& f : favorite_combos) f = -1;
	memset(colordata, 0, psTOTAL255);
	memset(palnames, 0, sizeof(palnames));
	for (int i = 0; i < MAXITEMS; ++i)
	{
		itemdata& it = itemsbuf[i];
		it.name.clear();
		it.display_name.clear();
		it.tile = 0;
	}
	for (int i = 0; i < MAXGUYS; ++i)
	{
		if (guy_string[i]) memset(guy_string[i], 0, 64);
		guysbuf[i].tile = guysbuf[i].s_tile = guysbuf[i].e_tile = 0;
	}
	for (int i = 0; i < MAXSPRITES; ++i)
	{
		sprite_data_buf[i].name.clear();
		sprite_data_buf[i].tile = 0;
	}
	ZI.clear();
	for (int i = 0; i < msg_count; ++i)
	{
		MsgStrings[i].clear();
	}
	msg_count = 1;
	for (int i = 0; i < MAXDMAPS; ++i) DMaps[i].clear();
	for (auto& d : DoorComboSets) d = DoorComboSet();
	for (auto& s : item_drop_sets) memset(&s, 0, sizeof(s));
	for (auto& s : QMisc.shop) memset(&s, 0, sizeof(s));
	for (auto& s : QMisc.info) memset(&s, 0, sizeof(s));
	for (auto& s : QMisc.bottle_types) s.clear();
	for (auto& s : QMisc.bottle_shop_types) s.clear();
	for (auto& s : quest_sounds) s.clear();
	for (int i = 0; i < MAXCUSTOMMIDIS; ++i) customtunes[i].reset();
	quest_music.clear();
	// Interface colours are palette indices into our cset 0 (15 white, 14 gold).
	{
		zcolors& z = QMisc.colors;
		z.text = 15; z.caption = 14; z.msgtext = 15;
		z.overw_bg = 0; z.dngn_bg = 0; z.dngn_fg = 7; z.cave_fg = 7;
		z.bs_dk = 4; z.bs_goal = 14; z.compass_lt = 15; z.compass_dk = 4;
		z.subscr_bg = 0; z.subscr_shadow = 0; z.triframe_color = 7;
		z.bmap_bg = 0; z.bmap_fg = 7; z.hero_dot = 14;
		z.triforce_cset = z.triframe_cset = z.overworld_map_cset = 0;
		z.dungeon_map_cset = z.blueframe_cset = z.HCpieces_cset = 0;
		z.triforce_tile = z.triframe_tile = z.overworld_map_tile = 0;
		z.dungeon_map_tile = z.blueframe_tile = z.HCpieces_tile = 0;
	}
	memset(header.title, 0, sizeof(header.title));
	memset(header.author, 0, sizeof(header.author));
	// Subscreens: keep only functional widgets; drop all text and artwork.
	auto prune = [](std::vector<ZCSubscreen>& v, char const* nm) {
		for (auto& sub : v)
		{
			sub.name = nm;
			for (auto& pg : sub.pages)
			{
				for (int w = int(pg.contents.size()) - 1; w >= 0; --w)
				{
					byte ty = pg.contents[w]->getType();
					bool keep = ty == widgLMETER || ty == widgCOUNTER || ty == widgBTNITM
						|| ty == widgITEMSLOT || ty == widgSELECTOR || ty == widgBGCOLOR
						|| ty == widgBTNCOUNTER || ty == widgLGAUGE;
					printf("lh-subscr %s widget %d type %d at %d,%d %s\n", nm, w, ty,
						pg.contents[w]->x, pg.contents[w]->y, keep ? "keep" : "drop");
					if (!keep) pg.delete_widg(w);
				}
			}
		}
	};
	prune(subscreens_active, "Inventory");
	prune(subscreens_passive, "Status");
	prune(subscreens_overlay, "Overlay");
	prune(subscreens_map, "Map");
}

static const byte ALLPOS = sspUP | sspDOWN | sspSCROLLING;

static SW_Text* make_text(int x, int y, std::string const& s, int font, int align)
{
	auto* t = new SW_Text();
	t->x = x; t->y = y; t->text = s; t->fontid = font; t->align = align;
	t->posflags = ALLPOS;
	return t;
}

// Original HUD: hearts, a key counter, and a pause screen with our own text.
static void build_subscreens(json const& h)
{
	subscreens_active.clear();
	subscreens_passive.clear();
	subscreens_overlay.clear();
	subscreens_map.clear();

	auto& pas = subscreens_passive.emplace_back();
	pas.name = "Status";
	pas.sub_type = sstPASSIVE;
	pas.add_page(0);
	{
		auto& pg = pas.pages[0];
		auto* life = new SW_LifeMeter();
		life->x = h["life"][0]; life->y = h["life"][1];
		life->posflags = ALLPOS;
		life->rows = 3;
		pg.push_back(life);
		auto* key = new SW_MiniTile();
		key->x = h["key_icon"][0]; key->y = h["key_icon"][1];
		key->tile = h["key_icon"][2]; key->crn = 1; key->flip = 0;
		key->cs.type = ssctMISC; key->cs.color = 0; key->cs.set_int_cset(h["key_icon"][3].get<int>());
		key->posflags = ALLPOS;
		pg.push_back(key);
		auto* ctr = new SW_Counter();
		ctr->x = h["keys"][0]; ctr->y = h["keys"][1];
		ctr->ctrs[0] = crKEYS; ctr->fontid = 0; ctr->mindigits = 1; ctr->maxdigits = 2;
		ctr->flags |= SUBSCR_COUNTER_SHOW0;
		ctr->posflags = ALLPOS;
		pg.push_back(ctr);
		for (auto& t : h["passive_text"])
			pg.push_back(make_text(t[0], t[1], t[2], 0, t[3]));
	}
	auto& act = subscreens_active.emplace_back();
	act.name = "Pause";
	act.sub_type = sstACTIVE;
	act.add_page(0);
	for (auto& t : h["active_text"])
		act.pages[0].push_back(make_text(t[0], t[1], t[2], 0, t[3]));
}

static void put_tile(int idx, json const& px)
{
	if (px.size() != 256) die("tile pixels must be 256");
	reset_tile(newtilebuf, idx, tf4Bit);
	for (int i = 0; i < 256; ++i) newtilebuf[idx].data[i] = byte(px[i].get<int>() & 15);
}

template<size_t N>
static void copy_str(char (&dst)[N], std::string const& s)
{
	memset(dst, 0, N);
	strncpy(dst, s.c_str(), N - 1);
}

static void set_spr(int32_t (*arr)[3], json const& dirs)
{
	for (int d = 0; d < 4; ++d)
	{
		arr[d][0] = dirs[d][0].get<int>();
		arr[d][1] = dirs[d][1].get<int>();
		arr[d][2] = dirs[d][2].get<int>();
	}
}

static void apply(json const& r)
{
	if (r.contains("header"))
	{
		copy_str(header.title, r["header"]["title"].get<std::string>());
		copy_str(header.author, r["header"]["author"].get<std::string>());
	}
	for (auto& [k, cols] : r["palette"].items())
	{
		int ds = std::stoi(k);
		for (int c = 0; c < 16; ++c)
			for (int ch = 0; ch < 3; ++ch)
				colordata[ds * 48 + c * 3 + ch] = byte(cols[c][ch].get<int>());
	}
	for (auto& [k, nm] : r["palnames"].items()) copy_str(palnames[std::stoi(k)], nm.get<std::string>());
	for (auto& t : r["tiles"]) put_tile(t["i"].get<int>(), t["px"]);
	for (auto& c : r["combos"])
	{
		newcombo& cb = combobuf[c["id"].get<int>()];
		cb.clear();
		cb.tile = cb.o_tile = c["tile"].get<int>();
		cb.flip = c.value("flip", 0);
		cb.walk = byte(0xF0 | (c.value("solid", 0) & 15));
		cb.type = c.value("type", 0);
		cb.csets = c.value("csets", 0);
		cb.flag = c.value("flag", 0);
		cb.frames = c.value("frames", 0);
		cb.speed = c.value("speed", 0);
		cb.label = c.value("label", "");
	}
	if (r.contains("map_count"))
	{
		map_count = r["map_count"].get<int>();
		TheMaps.resize(size_t(map_count) * MAPSCRS);
		map_infos.resize(map_count);
	}
	for (auto& s : r["screens"])
	{
		int m = s["map"].get<int>(), sc = s["screen"].get<int>();
		mapscr& ms = TheMaps[size_t(m) * MAPSCRS + sc];
		ms = mapscr();
		ms.map = m; ms.screen = sc;
		ms.valid = mVALID | mVERSION;
		for (int i = 0; i < 176; ++i)
		{
			ms.data[i] = s["data"][i].get<int>();
			ms.cset[i] = s["cset"][i].get<int>();
			ms.sflag[i] = s["sflag"][i].get<int>();
		}
		ms.color = s.value("color", 0);
		ms.flags = s.value("flags", 0);
		ms.flags2 = s.value("flags2", 0);
		ms.flags3 = s.value("flags3", 0);
		ms.roomflags = s.value("roomflags", 0);
		ms.room = s.value("room", 0);
		ms.guy = s.value("guy", 0);
		ms.str = s.value("str", 0);
		ms.pattern = s.value("pattern", 0);
		ms.item = s.value("item", 0);
		ms.hasitem = s.value("hasitem", 0);
		ms.itemx = s.value("itemx", 0);
		ms.itemy = s.value("itemy", 0);
		ms.undercombo = s.value("undercombo", 0);
		ms.undercset = s.value("undercset", 0);
		ms.secretsfx = s.value("secretsfx", 27);
		if (s.contains("enemy"))
			for (int i = 0; i < 10 && i < int(s["enemy"].size()); ++i) ms.enemy[i] = s["enemy"][i].get<int>();
		if (s.contains("tilewarp"))
		{
			auto& w = s["tilewarp"];
			ms.tilewarptype[0] = w["type"].get<int>();
			ms.tilewarpdmap[0] = w["dmap"].get<int>();
			ms.tilewarpscr[0] = w["scr"].get<int>();
		}
		if (s.contains("sidewarp"))
		{
			auto& w = s["sidewarp"];
			ms.sidewarptype[0] = w["type"].get<int>();
			ms.sidewarpdmap[0] = w["dmap"].get<int>();
			ms.sidewarpscr[0] = w["scr"].get<int>();
		}
		if (s.contains("warpreturn"))
		{
			for (int i = 0; i < 4; ++i)
			{
				ms.warpreturnx[i] = s["warpreturn"][0].get<int>();
				ms.warpreturny[i] = s["warpreturn"][1].get<int>();
			}
		}
		if (s.contains("warpreturns"))
		{
			for (int i = 0; i < 4 && i < int(s["warpreturns"].size()); ++i)
			{
				ms.warpreturnx[i] = s["warpreturns"][i][0].get<int>();
				ms.warpreturny[i] = s["warpreturns"][i][1].get<int>();
			}
		}
		if (s.contains("stair")) { ms.stairx = s["stair"][0]; ms.stairy = s["stair"][1]; }
		if (s.contains("warparrival")) { ms.warparrivalx = s["warparrival"][0]; ms.warparrivaly = s["warparrival"][1]; }
		else if (s.contains("warpreturn")) { ms.warparrivalx = s["warpreturn"][0]; ms.warparrivaly = s["warpreturn"][1]; }
	}
	if (r.contains("hud")) build_subscreens(r["hud"]);
	// The sword is always on A; there is no item selection in this quest.
	set_qr(qr_SELECTAWPN, 0);
	set_qr(qr_MSGDISAPPEAR, 1);
	printf("lh-subscr counts: active %zu passive %zu overlay %zu map %zu\n",
		subscreens_active.size(), subscreens_passive.size(), subscreens_overlay.size(), subscreens_map.size());
	for (auto& d : r["dmaps"])
	{
		dmap& dm = DMaps[d["i"].get<int>()];
		dm.clear();
		dm.map = d["map"].get<int>();
		dm.level = d.value("level", 0);
		dm.xoff = d.value("xoff", 0);
		dm.type = d.value("type", 0);
		dm.cont = d.value("cont", 0);
		dm.color = d.value("color", 0);
		dm.flags = d.value("flags", 0);
		for (int i = 0; i < 8; ++i) dm.grid[i] = d["grid"][i].get<int>();
		copy_str(dm.name, d.value("name", ""));
		dm.title = d.value("title", "");
		dm.music = d.value("music", 0);
		dm.active_subscreen = d.value("active_subscreen", 0);
		dm.passive_subscreen = d.value("passive_subscreen", 0);
	}
	for (auto& it : r["items"])
	{
		itemdata& id = itemsbuf[it["id"].get<int>()];
		id.name = it.value("name", "");
		id.display_name = id.name;
		id.tile = it["tile"].get<int>();
		id.csets = it.value("csets", 0);
		if (it.contains("power")) id.power = it["power"].get<int>();
		if (it.contains("wpn_tile"))
		{
			sprite_data& sd = sprite_data_buf[id.wpn_sprites[0]];
			sd.tile = it["wpn_tile"].get<int>();
			sd.csets = it.value("wpn_csets", 0);
		}
	}
	for (auto& sp : r["sprites"])
	{
		sprite_data& sd = sprite_data_buf[sp["id"].get<int>()];
		sd.tile = sp["tile"].get<int>();
		sd.csets = sp.value("csets", 0);
		sd.frames = sp.value("frames", 0);
		sd.speed = sp.value("speed", 0);
		sd.name = sp.value("name", "");
	}
	for (auto& g : r["guys"])
	{
		int i = g["id"].get<int>();
		guydata& gd = guysbuf[i];
		gd.tile = gd.s_tile = gd.e_tile = g["tile"].get<int>();
		gd.width = gd.height = gd.s_width = gd.s_height = gd.e_width = gd.e_height = 0;
		gd.cset = g.value("cset", 0);
		gd.anim = gd.e_anim = g.value("anim", 0);
		if (g.contains("hp")) gd.hp = g["hp"].get<int>();
		if (g.contains("dp")) gd.dp = g["dp"].get<int>();
		if (g.contains("step")) gd.step = g["step"].get<int>();
		if (g.contains("item_set")) gd.item_set = g["item_set"].get<int>();
		if (g.contains("frate")) gd.frate = gd.e_frate = g["frate"].get<int>();
		std::string nm = g.value("name", "");
		memset(guy_string[i], 0, 64);
		strncpy(guy_string[i], nm.c_str(), 63);
	}
	for (auto& ds : r["dropsets"])
	{
		item_drop_object& o = item_drop_sets[ds["i"].get<int>()];
		memset(&o, 0, sizeof(o));
		copy_str(o.name, ds.value("name", ""));
		o.chance[0] = ds["none"].get<int>();
		for (int q = 0; q < int(ds["items"].size()) && q < 10; ++q)
		{
			o.item[q] = ds["items"][q][0].get<int>();
			o.chance[q + 1] = ds["items"][q][1].get<int>();
		}
	}
	if (r.contains("hero"))
	{
		json const& h = r["hero"];
		for (auto arr : {walkspr, stabspr, slashspr, revslashspr, floatspr, swimspr, divespr,
			poundspr, jumpspr, chargespr, frozenspr, frozen_waterspr, onfirespr, onfire_waterspr,
			diggingspr, usingrodspr, usingcanespr, pushingspr, liftingwalkspr, stunnedspr,
			stunned_waterspr, drowningspr, sidedrowningspr, drowning_lavaspr})
			set_spr(arr, h["dirs"]);
		for (int d = 0; d < 4; ++d)
		{
			liftingspr[d][0] = h["dirs"][d][0]; liftingspr[d][1] = h["dirs"][d][1];
			liftingspr[d][2] = h["dirs"][d][2]; liftingspr[d][3] = 0;
		}
		for (int a = 0; a < 2; ++a) for (int b = 0; b < 3; ++b)
		{
			holdspr[a][b][0] = h["hold"][0]; holdspr[a][b][1] = 0; holdspr[a][b][2] = 0;
		}
		castingspr[0] = h["hold"][0]; castingspr[1] = 0; castingspr[2] = 0;
		sideswimcastingspr[0] = h["hold"][0]; sideswimcastingspr[1] = 0; sideswimcastingspr[2] = 0;
	}
	if (r.contains("strings"))
	{
		auto& st = r["strings"];
		msg_count = int(st.size()) + 1;
		for (int i = 0; i < int(st.size()); ++i)
		{
			MsgStr& m = MsgStrings[i + 1];
			m.clear();
			m.setFromAsciiEncoding(st[i]["text"].get<std::string>());
			m.x = 24; m.y = 24; m.w = 208; m.h = 72;
			m.font = 0; m.sfx = 18; m.trans = 0; m.tile = st[i].value("box", 0); m.cset = 0;
			m.vspace = 2; m.hspace = 0;
			m.margins[0] = 8; m.margins[1] = 8; m.margins[2] = 8; m.margins[3] = 8;
			m.listpos = i + 1;
			if (st[i].contains("next")) m.nextstring = st[i]["next"].get<int>();
		}
	}
	for (auto& s : r["sfx"])
	{
		int slot = s["slot"].get<int>();
		if (int(quest_sounds.size()) <= slot) quest_sounds.resize(slot + 1);
		// Headless mode disables the sound driver, so load the WAV with Allegro's
		// file loader and wrap the in-memory sample.
		SAMPLE* smp = load_wav(s["path"].get<std::string>().c_str());
		if (!smp) die("bad sfx " + s["path"].get<std::string>());
		quest_sounds[slot] = ZCSFX(*smp);
		destroy_sample(smp);
		if (quest_sounds[slot].is_invalid()) die("invalid sfx " + s["path"].get<std::string>());
		quest_sounds[slot].sfx_name = s["name"].get<std::string>();
	}
	for (auto& m : r["midis"])
	{
		int i = m["i"].get<int>();
		zctune& t = customtunes[i];
		t.reset();
		packfile_password("");
		t.data = load_midi(m["path"].get<std::string>().c_str());
		if (!t.data) die("bad midi " + m["path"].get<std::string>());
		t.song_title = m["title"].get<std::string>();
		t.loop = 1;
		int q = find_or_make_midi_music(i + 1);
		quest_music[q - 1].name = m["title"].get<std::string>();
	}
	if (r.contains("init"))
	{
		json const& in = r["init"];
		zinit.start_dmap = in.value("start_dmap", 0);
		for (int i = 0; i < MAXITEMS; ++i) zinit.set_item(i, false);
		for (auto& it : in["items"]) zinit.set_item(it.get<int>(), true);
		for (auto& [k, v] : in["counter"].items()) zinit.counter[std::stoi(k)] = v.get<int>();
		for (auto& [k, v] : in["mcounter"].items()) zinit.mcounter[std::stoi(k)] = v.get<int>();
		if (in.contains("cont_heart")) zinit.cont_heart = in["cont_heart"].get<int>();
		zinit.last_map = 0; zinit.last_screen = 0;
		zinit.msg_speed = 1;
	}
}

static void build(std::string const& base, std::string const& recipe, std::string const& out)
{
	set_headless_mode();
	if (int ret = load_quest(base.c_str(), false); ret != qe_OK)
		die(fmt::format("load base failed: {}", ret));
	std::ifstream in(recipe);
	if (!in) die("cannot open recipe");
	json r = json::parse(in);
	scrub();
	apply(r);
	header.data_flags[ZQ_TILES] = 1;
	printf("lh-debug sword item type %d level %d spr %d tile %d owned %d qrA %d\n",
		itemsbuf[5].type, itemsbuf[5].level, itemsbuf[5].wpn_sprites[0],
		sprite_data_buf[itemsbuf[5].wpn_sprites[0]].tile, (int)zinit.get_item(5), (int)get_qr(qr_SELECTAWPN));
	if (save_quest(out.c_str()) != 0) die("save failed");
	printf("lh-build: wrote %s\n", out.c_str());
	zq_exit(0);
}
} // namespace lh

void lh_handle_commands()
{
	int a = zapp_check_switch("-lh-build", {"base.qst", "recipe.json", "out.qst"});
	if (a > 0)
		lh::build(zapp_get_arg_string(a + 1), zapp_get_arg_string(a + 2), zapp_get_arg_string(a + 3));
}
