export const name = "starter-pack"
export const title = "Starter pack"
export const description = "24 PICO-8 games, two Solarus quests and the original ZQuest Classic quest Lantern Hollow. Content and notices only; no automatic library registration. PICO-8 content is noncommercial."

// Declared games (ADR 0003): titles from CREDITS.md, hashes from SHA256SUMS.
// A paired folder holding these exact files gets these titles; installing the
// pack still adds no library entries. intoruins_main.p8.png is Into Ruins'
// companion cartridge, loaded by intoruins.p8.png, and is not a game.
export const games = {
  "celeste-classic-2-lanis-trek": {
    title: "Celeste Classic 2: Lani's Trek",
    releases: { original: { system: "pico8", hashes: ["sha256:15b1f2639c8dd237ddb1176b1d9f311bb960082b780668e14c0f1d0fd8f8d96d"] } },
  },
  "combo-pool": {
    title: "Combo Pool",
    releases: { original: { system: "pico8", hashes: ["sha256:87f30adb9936668423bcf42fca0470a9b3b1bc7f2268ecb9ddf0b617a7c05edb"] } },
  },
  "whiplash-taxi-co": {
    title: "Whiplash Taxi Co",
    releases: { original: { system: "pico8", hashes: ["sha256:f42ffd0cfb87cc24d9eb26f92bd4553d46b1b2bef5c6ee201e5b9665b23cac8f"] } },
  },
  "birds-with-guns": {
    title: "Birds With Guns",
    releases: { original: { system: "pico8", hashes: ["sha256:552157ac198761b084446ba9335ab44b99b1a09d870765ddb9215fdde1d802f5"] } },
  },
  "demon-castle": {
    title: "Demon Castle",
    releases: { original: { system: "pico8", hashes: ["sha256:9fb4bd26b8da636d5d289f8c6272bafe99557cae22c82145950c5472d7e217cc"] } },
  },
  "little-necromancer": {
    title: "Little Necromancer",
    releases: { original: { system: "pico8", hashes: ["sha256:e6d04a2d2e4be24fb6ab8082a6eb5ab789930f98fec1a5307b80c4f30b19b4ef"] } },
  },
  "ufo-swamp-odyssey": {
    title: "UFO Swamp Odyssey",
    releases: { original: { system: "pico8", hashes: ["sha256:47364d1982fed967b4c867a104fd9cade13606cfe505989525979186bb28b9eb"] } },
  },
  "solais": {
    title: "Solais",
    releases: { original: { system: "pico8", hashes: ["sha256:e10ffc1f3bc69267cc8b19e23ba1fca3c2bace9663fcbbb4bbb4722dd9865001"] } },
  },
  "pigments": {
    title: "pigments",
    releases: { original: { system: "pico8", hashes: ["sha256:6022f3e36884e02ea851f35663a6ebeef0bde51d2146a65ec1d541fc8d1b9f56"] } },
  },
  "high-stakes": {
    title: "High Stakes",
    releases: { original: { system: "pico8", hashes: ["sha256:a5cff876236fdc4a225684b43f5acf92cb8e9e06bc12de819dcac521233c3ab6"] } },
  },
  "into-ruins": {
    title: "Into Ruins",
    releases: { original: { system: "pico8", hashes: ["sha256:552d29bb795c2c28ccc743d59be2b47f0361a13d778cf608a205cdf04229c62b"] } },
  },
  "air-delivery": {
    title: "Air Delivery",
    releases: { original: { system: "pico8", hashes: ["sha256:683adaf19233595077a904465343c2bc4e38eebf17e4b57a111f001ff7b7a0a3"] } },
  },
  "marble-merger": {
    title: "Marble Merger",
    releases: { original: { system: "pico8", hashes: ["sha256:9d98592e889a7e8a6efaac2534f09f70b3770d96b521911c36adfefe346f0c07"] } },
  },
  "proserpinas-quest": {
    title: "Proserpina's Quest",
    releases: { original: { system: "pico8", hashes: ["sha256:264e426b4409aa847b190eca90f45508be02e8d7992b04249294b18388ea615f"] } },
  },
  "cherry-bomb": {
    title: "Cherry Bomb",
    releases: { original: { system: "pico8", hashes: ["sha256:e6b223cc8d91fded83605444cf9ef68366e88a987713e5c6bbbf4260163e51e3"] } },
  },
  "charge": {
    title: "Charge!",
    releases: { original: { system: "pico8", hashes: ["sha256:687649db4d80befb02962512c33540883b31b07456312aada6bf3dfc424d7f80"] } },
  },
  "witchbeat": {
    title: "Witchbeat",
    releases: { original: { system: "pico8", hashes: ["sha256:5623b468d7099b531513787ef70690a37b2d2a17e1b9151086bc88e1a8f64b1d"] } },
  },
  "mai-chans-sweet-buns": {
    title: "Mai-Chan's Sweet Buns",
    releases: { original: { system: "pico8", hashes: ["sha256:ba3250ad0f3e73844d7003139ec0f46efe708d4764bac7d55075f851ddbfe1de"] } },
  },
  "spaceman-8": {
    title: "Spaceman 8",
    releases: { original: { system: "pico8", hashes: ["sha256:07c1155f63a0a13e6300ef9aef8a26b0df650f15eb24a9ed73bb68394f079c0a"] } },
  },
  "worm-nom-nom": {
    title: "Worm Nom Nom",
    releases: { original: { system: "pico8", hashes: ["sha256:310a57c27b0c2a49a6cfe68f0a9fddf5ebcb4b35be6f385c1695da5b32beffcd"] } },
  },
  "picoracer-2048": {
    title: "PICORACER-2048",
    releases: { original: { system: "pico8", hashes: ["sha256:a88221fbd390c819d91db8438575325002cd4e85de4274690108958aa0aa3e65"] } },
  },
  "defacto": {
    title: "DeFacto",
    releases: { original: { system: "pico8", hashes: ["sha256:9e2c7759826af559697e0c69a331c8a14db2ddd5b1108bc91ea9fbe1570706d1"] } },
  },
  "vitreous": {
    title: "Vitreous",
    releases: { original: { system: "pico8", hashes: ["sha256:cacfc19bd8aaa6e7f19aea36e5c8c726e43a895e45a8a208912ecb18699862fe"] } },
  },
  "dungeon-solitaire": {
    title: "Dungeon Solitaire",
    releases: { original: { system: "pico8", hashes: ["sha256:07ab38817c51bddf4ecdd9e0418a3f7d5aa6e3f0f31ba28a5a67605de728fbf3"] } },
  },
  "perlshaws-problems": {
    title: "Perlshaw's Problems",
    releases: { original: { system: "solarus", hashes: ["sha256:ad7b54f73d4a3bca39135d30ac92d895a7c2f4a20924dc43e9ad7a4564bd5a8a"] } },
  },
  "vegan-on-a-desert-island": {
    title: "Vegan on a Desert Island",
    releases: { original: { system: "solarus", hashes: ["sha256:292809bffc860326bab70f676d1c5e9c15b86b915fcaf122123766d8b49f6d34"] } },
  },
  "lantern-hollow": {
    title: "Lantern Hollow",
    releases: { original: { system: "zelda-classic", hashes: ["sha256:5bba59ec2e265c2cc6619be10bb403e4fa33136b3cbdfc181316c836bb9a749c"] } },
  },
}
