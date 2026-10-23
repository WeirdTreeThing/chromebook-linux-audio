-- Screebo. Hide the split parent and the raw hw PCM from apps. The public
-- mic is a loopback of that parent, and the loopback reads the raw node.
-- Disabling either one silences the mic; revoking client permission leaves
-- the links in place and drops the extra picker entries.

log = Log.open_topic("s-hide-dmic-parent")

clients_om = ObjectManager {
  Interest { type = "client" }
}

hidden = {}

local function hide(node)
  local bound = node["bound-id"]
  if not bound or hidden[bound] then
    return bound ~= nil
  end
  hidden[bound] = true
  for client in clients_om:iterate{ type = "client" } do
    if not client.properties["wireplumber.daemon"] then
      client:update_permissions{ [bound] = "-" }
    end
  end
  log:info(node, "hid extra DMIC node from clients")
  return true
end

local function hide_when_bound(node)
  if hide(node) then
    return
  end
  local tries = 0
  Core.timeout_add(50, function()
    tries = tries + 1
    if hide(node) or tries > 40 then
      return false
    end
    return true
  end)
end

watched = {}

local function watch(pattern)
  local om = ObjectManager {
    Interest {
      type = "node",
      Constraint { "node.name", "matches", pattern },
    },
  }
  om:connect("object-added", function(_, node)
    hide_when_bound(node)
  end)
  table.insert(watched, om)
  om:activate()
end

watch("*HiFi__Mic__source.split")
watch("alsa_input.hw_sofrt5682_99")

clients_om:connect("object-added", function(_, client)
  if client.properties["wireplumber.daemon"] then
    return
  end
  for bound, _ in pairs(hidden) do
    client:update_permissions{ [bound] = "-" }
  end
end)

clients_om:activate()
