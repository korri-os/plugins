//! save_export (ADR 0083): a game's Steam saves are exactly its Steam Cloud
//! set. That is the engine's `remote/` folder for the app and the files that the
//! app's AutoCloud rules (appinfo `ufs/savefiles`) resolve to. The host packs
//! them into one tar archive in the launch channel; korrid imports the archive
//! into its save history and never opens the Steam folder.
//!
//! Root names and their Proton prefix folders come from the spike's
//! `scripts/mini/cloud-rules.py`, which found the files on the device. A rule
//! whose root has no folder here is counted as unresolved and skipped. No
//! per-game rules.
use crate::appinfo::Value;
use std::{
    collections::BTreeMap,
    fs,
    io::Write,
    os::unix::fs::{OpenOptionsExt, PermissionsExt},
    path::{Component, Path, PathBuf},
};

/// A save set larger than this is not exported; a snapshot of that size is not
/// a save (korrid keeps snapshots on the device).
pub const MAX_BYTES: u64 = 512 << 20;
const MAX_FILES: usize = 20_000;

/// Where the folders of one app are.
pub struct Places<'a> {
    /// The Steam root (`steam/` of the person's engine folder).
    pub steam: &'a Path,
    /// HOME of the host and the game.
    pub home: &'a Path,
    pub appid: u32,
    pub steam_id: u64,
}
impl Places<'_> {
    fn account_id(&self) -> u32 {
        self.steam_id as u32
    }
    fn remote(&self) -> PathBuf {
        self.steam
            .join("userdata")
            .join(self.account_id().to_string())
            .join(self.appid.to_string())
            .join("remote")
    }
    fn prefix_user(&self) -> PathBuf {
        self.steam
            .join("steamapps/compatdata")
            .join(self.appid.to_string())
            .join("pfx/drive_c/users/steamuser")
    }
    /// The folder an AutoCloud root names, or None when the host has no folder for it.
    fn root(&self, root: &str, installdir: Option<&str>) -> Option<PathBuf> {
        let windows = |sub: &str| Some(self.prefix_user().join(sub));
        match root {
            "WinMyDocuments" => windows("Documents"),
            "WinAppDataRoaming" => windows("AppData/Roaming"),
            "WinAppDataLocal" => windows("AppData/Local"),
            "WinAppDataLocalLow" => windows("AppData/LocalLow"),
            "WinSavedGames" => windows("Saved Games"),
            "GameInstall" => {
                let dir = installdir.filter(|d| safe_relative(d))?;
                Some(self.steam.join("steamapps/common").join(dir))
            }
            "LinuxHome" => Some(self.home.to_path_buf()),
            "LinuxXdgDataHome" => Some(self.home.join(".local/share")),
            "LinuxXdgConfigHome" => Some(self.home.join(".config")),
            _ => None,
        }
    }
}

/// A relative path with no `..`, no root and no empty name.
fn safe_relative(path: &str) -> bool {
    !path.is_empty()
        && Path::new(path)
            .components()
            .all(|c| matches!(c, Component::Normal(_) | Component::CurDir))
}

/// `*` and `?` over one file name, as Steam's AutoCloud patterns use them.
pub fn pattern_matches(pattern: &str, name: &str) -> bool {
    fn go(p: &[u8], n: &[u8]) -> bool {
        match (p.first(), n.first()) {
            (None, None) => true,
            (Some(b'*'), _) => go(&p[1..], n) || (!n.is_empty() && go(p, &n[1..])),
            (Some(b'?'), Some(_)) => go(&p[1..], &n[1..]),
            (Some(a), Some(b)) if a.eq_ignore_ascii_case(b) => go(&p[1..], &n[1..]),
            _ => false,
        }
    }
    go(pattern.as_bytes(), name.as_bytes())
}

/// The app's Steam Cloud quota from appinfo (`ufs/quota`). An app without one
/// has no Steam Cloud, and so no snapshots.
pub fn has_cloud(app: Option<&Value>) -> bool {
    app.and_then(|a| a.path(&["ufs", "quota"]))
        .and_then(Value::int)
        .is_some_and(|q| q > 0)
}

#[derive(Debug, Default, PartialEq, Eq)]
pub struct Collected {
    /// Archive name -> file on disk.
    pub files: BTreeMap<String, PathBuf>,
    pub bytes: u64,
    /// Rules whose root the host has no folder for.
    pub unresolved: usize,
}

/// Every file of the app's Steam Cloud set that exists now.
pub fn collect(places: &Places, app: Option<&Value>) -> Result<Collected, String> {
    let mut out = Collected::default();
    walk(&places.remote(), "remote", None, true, &mut out)?;
    let installdir = app
        .and_then(|a| a.path(&["config", "installdir"]))
        .and_then(Value::text);
    let rules = app.and_then(|a| a.path(&["ufs", "savefiles"]));
    for (_, rule) in rules.into_iter().flat_map(Value::entries) {
        let field = |key| rule.get(key).and_then(Value::text).unwrap_or_default();
        let root_name = field("root");
        let Some(root) = places.root(&root_name, installdir.as_deref()) else {
            out.unresolved += 1;
            continue;
        };
        let path = field("path")
            .replace('\\', "/")
            .replace("{64BitSteamID}", &places.steam_id.to_string())
            .replace("{Steam3AccountID}", &places.account_id().to_string());
        let path = path.trim_matches('/');
        if !path.is_empty() && !safe_relative(path) {
            out.unresolved += 1;
            continue;
        }
        let pattern = Some(field("pattern")).filter(|p| !p.is_empty());
        let recursive = rule.get("recursive").and_then(Value::int).unwrap_or(0) != 0;
        let base = if path.is_empty() {
            root
        } else {
            root.join(path)
        };
        let prefix = if path.is_empty() {
            root_name.clone()
        } else {
            format!("{root_name}/{path}")
        };
        walk(
            &base,
            &prefix,
            Some(pattern.as_deref().unwrap_or("*")),
            recursive,
            &mut out,
        )?;
    }
    Ok(out)
}

/// Regular files below `dir` (symlinks are never followed), under `prefix`.
fn walk(
    dir: &Path,
    prefix: &str,
    pattern: Option<&str>,
    recursive: bool,
    out: &mut Collected,
) -> Result<(), String> {
    let Ok(entries) = fs::read_dir(dir) else {
        return Ok(());
    };
    let mut entries: Vec<_> = entries.flatten().collect();
    entries.sort_by_key(|e| e.file_name());
    for entry in entries {
        let Ok(kind) = entry.file_type() else {
            continue;
        };
        let Some(name) = entry.file_name().to_str().map(str::to_owned) else {
            continue;
        };
        let archived = format!("{prefix}/{name}");
        if kind.is_dir() && recursive {
            walk(&entry.path(), &archived, pattern, recursive, out)?;
        } else if kind.is_file() && pattern.is_none_or(|p| pattern_matches(p, &name)) {
            if out.files.contains_key(&archived) {
                continue;
            }
            let size = entry.metadata().map(|m| m.len()).unwrap_or(0);
            out.bytes += size;
            if out.bytes > MAX_BYTES || out.files.len() >= MAX_FILES {
                return Err("the save set is too large to export".into());
            }
            out.files.insert(archived, entry.path());
        }
    }
    Ok(())
}

/// Writes the files as a tar archive at `path` (mode 0644, by rename, so a
/// reader never sees half an archive).
pub fn write_archive(path: &Path, collected: &Collected) -> Result<(), String> {
    let fail = |what: &str| format!("save export: cannot {what}");
    let dir = path
        .parent()
        .ok_or_else(|| fail("find the archive folder"))?;
    fs::create_dir_all(dir).map_err(|_| fail("make the archive folder"))?;
    let temporary = dir.join(format!(
        ".{}.tmp",
        path.file_name().and_then(|n| n.to_str()).unwrap_or("save")
    ));
    let _ = fs::remove_file(&temporary);
    let file = fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o644)
        .open(&temporary)
        .map_err(|_| fail("create the archive"))?;
    let result = (|| {
        let mut builder = tar::Builder::new(file);
        builder.follow_symlinks(false);
        for (name, source) in &collected.files {
            let mut data = fs::File::open(source).map_err(|_| fail("read a save file"))?;
            let meta = data.metadata().map_err(|_| fail("read a save file"))?;
            let mut header = tar::Header::new_gnu();
            header.set_size(meta.len());
            header.set_mode(0o644);
            header.set_mtime(
                meta.modified()
                    .ok()
                    .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
                    .map_or(0, |d| d.as_secs()),
            );
            header.set_entry_type(tar::EntryType::Regular);
            builder
                .append_data(&mut header, name, &mut data)
                .map_err(|_| fail("write the archive"))?;
        }
        let mut file = builder
            .into_inner()
            .map_err(|_| fail("write the archive"))?;
        file.flush().map_err(|_| fail("write the archive"))?;
        file.sync_all().map_err(|_| fail("write the archive"))?;
        file.set_permissions(fs::Permissions::from_mode(0o644))
            .map_err(|_| fail("write the archive"))?;
        fs::rename(&temporary, path).map_err(|_| fail("write the archive"))
    })();
    if result.is_err() {
        let _ = fs::remove_file(&temporary);
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::appinfo::Value as V;

    fn object(entries: Vec<(&str, V)>) -> V {
        V::Object(entries.into_iter().map(|(k, v)| (k.into(), v)).collect())
    }
    fn s(v: &str) -> V {
        V::String(v.into())
    }

    #[test]
    fn patterns_match_like_autocloud() {
        assert!(pattern_matches("*", "a.sav"));
        assert!(pattern_matches("*.sav", "slot1.SAV"));
        assert!(pattern_matches("slot?.dat", "slot3.dat"));
        assert!(!pattern_matches("*.sav", "slot1.bak"));
        assert!(!pattern_matches("slot?.dat", "slot10.dat"));
    }

    #[test]
    fn collects_remote_and_autocloud_files_and_skips_unknown_roots() {
        let tmp = std::env::temp_dir().join(format!("korri-saves-{}", std::process::id()));
        let _ = fs::remove_dir_all(&tmp);
        let steam = tmp.join("steam");
        let home = tmp.join("home");
        let remote = steam.join("userdata/42/7/remote/sub");
        fs::create_dir_all(&remote).unwrap();
        fs::write(remote.join("a.bin"), b"remote").unwrap();
        let roaming = steam.join("steamapps/compatdata/7/pfx/drive_c/users/steamuser/AppData/Roaming/Game/76561197960265770");
        fs::create_dir_all(roaming.join("deep")).unwrap();
        fs::write(roaming.join("one.sav"), b"1").unwrap();
        fs::write(roaming.join("skip.log"), b"x").unwrap();
        fs::write(roaming.join("deep/two.sav"), b"2").unwrap();
        std::os::unix::fs::symlink("/etc/hostname", roaming.join("link.sav")).unwrap();
        let app = object(vec![(
            "ufs",
            object(vec![
                ("quota", V::Int(1000)),
                (
                    "savefiles",
                    object(vec![
                        (
                            "0",
                            object(vec![
                                ("root", s("WinAppDataRoaming")),
                                ("path", s("Game\\{64BitSteamID}")),
                                ("pattern", s("*.sav")),
                            ]),
                        ),
                        ("1", object(vec![("root", s("MacHome")), ("path", s("x"))])),
                        (
                            "2",
                            object(vec![
                                ("root", s("WinAppDataRoaming")),
                                ("path", s("../escape")),
                            ]),
                        ),
                    ]),
                ),
            ]),
        )]);
        let places = Places {
            steam: &steam,
            home: &home,
            appid: 7,
            steam_id: 76561197960265770,
        };
        assert!(has_cloud(Some(&app)));
        let got = collect(&places, Some(&app)).unwrap();
        let names: Vec<&str> = got.files.keys().map(String::as_str).collect();
        assert_eq!(
            names,
            vec![
                "WinAppDataRoaming/Game/76561197960265770/one.sav",
                "remote/sub/a.bin"
            ]
        );
        assert_eq!(got.unresolved, 2);
        let archive = tmp.join("out/7-1.tar");
        write_archive(&archive, &got).unwrap();
        let mut read = tar::Archive::new(fs::File::open(&archive).unwrap());
        let listed: Vec<String> = read
            .entries()
            .unwrap()
            .map(|e| e.unwrap().path().unwrap().to_string_lossy().into_owned())
            .collect();
        assert_eq!(listed, names);
        // A recursive rule reaches the nested file.
        let recursive = object(vec![(
            "ufs",
            object(vec![(
                "savefiles",
                object(vec![(
                    "0",
                    object(vec![
                        ("root", s("WinAppDataRoaming")),
                        ("path", s("Game")),
                        ("pattern", s("*.sav")),
                        ("recursive", V::Int(1)),
                    ]),
                )]),
            )]),
        )]);
        let got = collect(&places, Some(&recursive)).unwrap();
        assert!(got
            .files
            .contains_key("WinAppDataRoaming/Game/76561197960265770/deep/two.sav"));
        assert!(!has_cloud(Some(&recursive)));
        fs::remove_dir_all(&tmp).unwrap();
    }
}
