rule = {
    matches = {
      {
        { "node.name", "matches", "alsa_output.*" },
      },
    },
    apply_properties = {
      ["api.alsa.headroom"] = 4096,
    },
}

table.insert(alsa_monitor.rules,rule)
