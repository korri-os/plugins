-- Exercise native save loading/writing without a retail quest or game assets.
-- Public API used by upstream's 1533_savegame_write_escape regression test.
function sol.main:on_started()
  local game = sol.game.load("save1.dat")
  local launches = game:get_value("launches") or 0
  game:set_value("launches", launches + 1)
  game:save()
  local reloaded = sol.game.load("save1.dat")
  assert(reloaded:get_value("launches") == launches + 1)
  print("KORRI_SOLARUS_SAVE=" .. reloaded:get_value("launches"))
  sol.timer.start(sol.main, 100, function()
    print("KORRI_SOLARUS_LOOP")
    sol.main.exit()
  end)
end
