-- Gain on the raw DMIC node, which the public mic loopback records from.
-- The volume slider stays on the public node, so this does not add a device.
-- 17.78 is +25 dB. Hardware Dmic0 is already at 0 dB.

log = Log.open_topic("s-mic-boost")

local GAIN = 17.78

local function apply_gain(node)
  local volumes = { GAIN, GAIN, GAIN, GAIN }
  table.insert(volumes, 1, "Spa:Float")
  local param = Pod.Object {
    "Spa:Pod:Object:Param:Props", "Props",
    channelVolumes = Pod.Array(volumes),
  }
  node:set_param("Props", param)
  log:info(node, "internal mic gain +25 dB")
end

sources = ObjectManager {
  Interest {
    type = "node",
    Constraint { "node.name", "equals", "alsa_input.hw_sofrt5682_99" },
  },
}

sources:connect("object-added", function(_, node)
  -- After route restore, so a saved slider value cannot replace the gain.
  Core.timeout_add(200, function()
    apply_gain(node)
    return false
  end)
end)

sources:activate()
