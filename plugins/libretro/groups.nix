# A core contributes a group when it runs at least two of the group's members.
# Keep the full member set: the registry ignores members no enabled plugin declares.
{
  gameboy = {
    id = "gameboy";
    title = "Game Boy";
    systems = [
      "gb"
      "gbc"
    ];
  };
  sega-8bit = {
    id = "sega-8bit";
    title = "Sega 8-bit";
    systems = [
      "sms"
      "gg"
      "sg1000"
    ];
  };
  nintendo-8bit = {
    id = "nintendo-8bit";
    title = "Nintendo 8-bit";
    systems = [
      "nes"
      "fds"
    ];
  };
  mega-drive = {
    id = "mega-drive";
    title = "Mega Drive";
    systems = [
      "md"
      "sega32x"
    ];
  };
}
