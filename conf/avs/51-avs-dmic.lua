rule = {
  matches = {
    {
      { "node.nick", "equals", "Internal Microphone" },
    },
  },
  apply_properties = {
    ["audio.format"] = "S16LE",
  },
}

table.insert(alsa_monitor.rules, rule)
